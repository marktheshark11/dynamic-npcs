import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from db.config import Config
from db.repositories import ConstantRepo, PlayerRepo, UserRepo
from services.chat_service import ChatService
from services.door_service import DoorService
from services.scripted_npc_service import ScriptedNpcService

class ChatResponse(BaseModel):
    npc_id: str
    conversation_id: str | None = None
    response: str
    used_claims: list[str] = Field(default_factory=list)


class StaticNpcChatResponse(BaseModel):
    npc_id: str
    response: str

class ChatRequest(BaseModel):
    npc_id: str
    message: str
    player_id: str | None = None
    conversation_id: str | None = None


class StaticNpcChatRequest(BaseModel):
    npc_id: str
    message: str = ""
    player_id: str | None = None


class ConversationSummaryRequest(BaseModel):
    conversation_id: str


class ConversationSummaryResponse(BaseModel):
    conversation_id: str
    summary: str
    exchange_count: int


class CreatePlayerRequest(BaseModel):
    name: str
    appearance: str
    user_id: str | None = None


class CreatePlayerResponse(BaseModel):
    player_id: str
    name: str
    appearance: str


class PlayerResponse(BaseModel):
    player_id: str
    name: str
    appearance: str


class DeletePlayerResponse(BaseModel):
    player_id: str
    deleted: bool


class ItemActionRequest(BaseModel):
    object_id: str


class DoorOpenRequest(BaseModel):
    object_id: str
    code: str | None = None


class InspectItemResponse(BaseModel):
    player_id: str
    object_id: str
    item_name: str
    inspect_text: str
    pickupable: bool
    seen: bool


class PickupItemResponse(BaseModel):
    player_id: str
    object_id: str
    item_name: str
    pickupable: bool
    picked_up: bool
    detail: str


class OpenDoorResponse(BaseModel):
    player_id: str
    object_id: str
    door_name: str
    opened: bool
    already_open: bool
    lock_type: str
    required_item_id: str | None = None
    detail: str


class AwareClaimResponse(BaseModel):
     claim_id: str
     content: str
     type: str | None = None
     created_at: str | None = None
     npc_ids: list[str] = Field(default_factory=list)


class ClueItemResponse(BaseModel):
    object_id: str
    name: str
    inspect_text: str
    pickupable: bool
    created_at: str | None = None
    seen: bool
    picked_up: bool


class ClueDoorResponse(BaseModel):
    object_id: str
    name: str
    inspect_text: str
    lock_type: str
    created_at: str | None = None
    seen: bool
    opened: bool


class ClueResponse(BaseModel):
    claims: list[AwareClaimResponse] = Field(default_factory=list)
    items: list[ClueItemResponse] = Field(default_factory=list)
    doors: list[ClueDoorResponse] = Field(default_factory=list)


class RegisterRequest(BaseModel):
    username: str
    password: str


class RegisterResponse(BaseModel):
    user_id: str
    username: str


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    user_id: str
    username: str
    

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
    app.state.scripted_npc_service = ScriptedNpcService(config.driver)
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


def get_scripted_npc_service(request: Request) -> ScriptedNpcService:
    return request.app.state.scripted_npc_service


def get_config(request: Request) -> Config:
    return request.app.state.config

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


@app.post("/users/register", response_model=RegisterResponse)
async def register(payload: RegisterRequest, config: Config = Depends(get_config)):
    username = payload.username.strip()
    password = payload.password.strip()
    
    if not username:
        raise HTTPException(status_code=400, detail="username cannot be empty")
    if not password:
        raise HTTPException(status_code=400, detail="password cannot be empty")
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="username must be at least 3 characters")
    if len(password) < 3:
        raise HTTPException(status_code=400, detail="password must be at least 3 characters")
    
    try:
        user_repo = UserRepo(config.driver)
        user = user_repo.register(username=username, password=password)
        
        if not user:
            raise HTTPException(status_code=409, detail="Username already exists")
        
        return RegisterResponse(user_id=user.user_id, username=user.username)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/users/login", response_model=LoginResponse)
async def login(payload: LoginRequest, config: Config = Depends(get_config)):
    username = payload.username.strip()
    password = payload.password.strip()
    
    if not username:
        raise HTTPException(status_code=400, detail="username cannot be empty")
    if not password:
        raise HTTPException(status_code=400, detail="password cannot be empty")
    
    try:
        user_repo = UserRepo(config.driver)
        user = user_repo.login(username=username, password=password)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        return LoginResponse(user_id=user.user_id, username=user.username)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, chat_service: ChatService = Depends(get_chat_service)):
    try:
        result = chat_service.ask_npc(
            npc_id=payload.npc_id,
            question=payload.message,
            player_id=payload.player_id,
            conversation_id=payload.conversation_id,
        )
        if not result:
            return ChatResponse(npc_id=payload.npc_id, response="No response")
        return ChatResponse(
            npc_id=payload.npc_id,
            conversation_id=result.get("conversation_id"),
            response=result["response"],
            used_claims=result.get("used_claims") or [],
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


@app.post("/chat_static_npc", response_model=StaticNpcChatResponse)
async def chat_static_npc(
    payload: StaticNpcChatRequest,
    scripted_npc_service: ScriptedNpcService = Depends(get_scripted_npc_service),
):
    try:
        result = scripted_npc_service.ask_npc(
            npc_id=payload.npc_id,
            question=payload.message,
            player_id=payload.player_id,
        )
        return StaticNpcChatResponse(
            npc_id=payload.npc_id,
            response=result["response"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/players", response_model=CreatePlayerResponse)
async def create_player(payload: CreatePlayerRequest, config: Config = Depends(get_config)):
    name = payload.name.strip()
    appearance = payload.appearance.strip()
    user_id = payload.user_id.strip() if payload.user_id else None
    
    if not name:
        raise HTTPException(status_code=400, detail="name cannot be empty")
    if not appearance:
        raise HTTPException(status_code=400, detail="appearance cannot be empty")

    try:
        player_repo = PlayerRepo(config.driver)
        player = player_repo.create(name=name, appearance=appearance, user_id=user_id)
        return CreatePlayerResponse(
            player_id=player.player_id,
            name=player.name,
            appearance=player.appearance,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/players", response_model=list[PlayerResponse])
async def list_players(user_id: str | None = None, config: Config = Depends(get_config)):
    try:
        player_repo = PlayerRepo(config.driver)
        
        if user_id:
            # If user_id is provided, only return players for that user
            user_id = user_id.strip()
            if not user_id:
                raise HTTPException(status_code=400, detail="user_id cannot be empty")
            players = player_repo.list_by_user(user_id)
        else:
            # If no user_id, return all players
            players = player_repo.list_all()
        
        return [
            PlayerResponse(
                player_id=player.player_id,
                name=player.name,
                appearance=player.appearance,
            )
            for player in players
        ]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.delete("/players/{player_id}", response_model=DeletePlayerResponse)
async def delete_player(player_id: str, config: Config = Depends(get_config)):
    player_id = player_id.strip()
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id cannot be empty")

    try:
        player_repo = PlayerRepo(config.driver)
        deleted = player_repo.delete(player_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Player not found")
        return DeletePlayerResponse(player_id=player_id, deleted=True)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/players/{player_id}/claims", response_model=list[AwareClaimResponse])
async def list_aware_claims(player_id: str, config: Config = Depends(get_config)):
    player_id = player_id.strip()
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id cannot be empty")

    try:
        player_repo = PlayerRepo(config.driver)

        if not player_repo.get_profile_by_id(player_id):
            raise HTTPException(status_code=404, detail="Player not found")

        claims = player_repo.get_aware_claims(player_id)
        return [AwareClaimResponse(**c) for c in claims]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/players/{player_id}/clues", response_model=ClueResponse)
async def list_player_clues(player_id: str, config: Config = Depends(get_config)):
    player_id = player_id.strip()
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id cannot be empty")

    try:
        player_repo = PlayerRepo(config.driver)

        if not player_repo.get_profile_by_id(player_id):
            raise HTTPException(status_code=404, detail="Player not found")

        clues = player_repo.get_clues(player_id)
        return ClueResponse(
            claims=[AwareClaimResponse(**claim) for claim in clues.get("claims", [])],
            items=[ClueItemResponse(**item) for item in clues.get("items", [])],
            doors=[ClueDoorResponse(**door) for door in clues.get("doors", [])],
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/players/{player_id}/items/inspect", response_model=InspectItemResponse)
async def inspect_item(
    player_id: str,
    payload: ItemActionRequest,
    config: Config = Depends(get_config),
):
    player_id = player_id.strip()
    object_id = payload.object_id.strip()
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id cannot be empty")
    if not object_id:
        raise HTTPException(status_code=400, detail="object_id cannot be empty")

    try:
        player_repo = PlayerRepo(config.driver)
        constant_repo = ConstantRepo(config.driver)

        if not player_repo.get_profile_by_id(player_id):
            raise HTTPException(status_code=404, detail="Player not found")

        item = constant_repo.get_item(object_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        seen = player_repo.mark_seen_object(player_id, item.object_id)
        if not seen:
            raise HTTPException(status_code=500, detail="Could not mark item as seen")

        return InspectItemResponse(
            player_id=player_id,
            object_id=item.object_id,
            item_name=item.name,
            inspect_text=item.inspect_text,
            pickupable=item.pickupable,
            seen=True,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/players/{player_id}/items/pickup", response_model=PickupItemResponse)
async def pickup_item(
    player_id: str,
    payload: ItemActionRequest,
    config: Config = Depends(get_config),
):
    player_id = player_id.strip()
    object_id = payload.object_id.strip()
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id cannot be empty")
    if not object_id:
        raise HTTPException(status_code=400, detail="object_id cannot be empty")

    try:
        player_repo = PlayerRepo(config.driver)
        constant_repo = ConstantRepo(config.driver)

        if not player_repo.get_profile_by_id(player_id):
            raise HTTPException(status_code=404, detail="Player not found")

        item = constant_repo.get_item(object_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        picked_up, detail = player_repo.pickup_item(player_id, item.object_id)
        if not picked_up and detail == "Item eller player hittades inte":
            raise HTTPException(status_code=404, detail=detail)

        return PickupItemResponse(
            player_id=player_id,
            object_id=item.object_id,
            item_name=item.name,
            pickupable=item.pickupable,
            picked_up=picked_up,
            detail=detail,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/players/{player_id}/doors/open", response_model=OpenDoorResponse)
async def open_door(
    player_id: str,
    payload: DoorOpenRequest,
    config: Config = Depends(get_config),
):
    player_id = player_id.strip()
    object_id = payload.object_id.strip()
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id cannot be empty")
    if not object_id:
        raise HTTPException(status_code=400, detail="object_id cannot be empty")

    try:
        player_repo = PlayerRepo(config.driver)
        door_service = DoorService(config.driver)

        if not player_repo.get_profile_by_id(player_id):
            raise HTTPException(status_code=404, detail="Player not found")

        result = door_service.open_door(player_id, object_id, code=payload.code)
        if result["detail"] == "Door not found":
            raise HTTPException(status_code=404, detail=result["detail"])
        return OpenDoorResponse(**result)
    except ValueError as exc:
        if str(exc) == "Door not found":
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
