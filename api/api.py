import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from db.config import Config
from services.chat_service import ChatService

class ChatResponse(BaseModel):
    npc_id: str
    conversation_id: str | None = None
    response: str

class ChatRequest(BaseModel):
    npc_id: str
    message: str
    conversation_id: str | None = None
    new_conversation: bool = False


class ConversationSummaryRequest(BaseModel):
    conversation_id: str


class ConversationSummaryResponse(BaseModel):
    conversation_id: str
    summary: str
    exchange_count: int
    
@asynccontextmanager
async def lifespan(app: FastAPI):
    config = Config.from_env()
    api_key = os.getenv("API_KEY")
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Missing API_KEY in environment")
    if not groq_api_key:
        raise RuntimeError("Missing GROQ_API_KEY in environment")

    app.state.config = config
    app.state.api_key = api_key
    app.state.chat_service = ChatService(config.driver, config.embed_model)
    try:
        yield
    finally:
        config.close()

app = FastAPI(
    title="Dynamic NPC Chat API",
    description="API for chatting with AI-powered NPCs with persistent memories",
    version="1.0.0",
    lifespan=lifespan
)

def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service

# Enable CORS for web frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def check_api_key(request: Request, call_next: RequestResponseEndpoint) -> Response:
    if request.method == "OPTIONS":
        return await call_next(request)

    if request.url.path in {"/health", "/docs", "/openapi.json", "/redoc"}:
        return await call_next(request)

    if request.headers.get("x-api-key") != request.app.state.api_key:
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    return await call_next(request)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, chat_service: ChatService = Depends(get_chat_service)):
    try:
        result = chat_service.ask_npc(
            npc_id=payload.npc_id,
            question=payload.message,
            conversation_id=payload.conversation_id,
            new_conversation=payload.new_conversation,
        )
        if not result:
            return ChatResponse(npc_id=payload.npc_id, response="No response")
        return ChatResponse(
            npc_id=payload.npc_id,
            conversation_id=result.get("conversation_id"),
            response=result["response"],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/conversations/summarize", response_model=ConversationSummaryResponse)
async def summarize_conversation(
    payload: ConversationSummaryRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    try:
        result = chat_service.summarize_conversation(payload.conversation_id)
        if not result:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return ConversationSummaryResponse(
            conversation_id=result["conversation_id"],
            summary=result["summary"],
            exchange_count=result["exchange_count"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
