from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from npc_chat import chat_with_npc, get_npc_context
from db_neo4j import ex_query

app = FastAPI(
    title="Dynamic NPC Chat API",
    description="API for chatting with AI-powered NPCs with persistent memories",
    version="1.0.0"
)

# Enable CORS for web frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    npc_name: str
    message: str


class ChatResponse(BaseModel):
    npc_name: str
    response: str


class NPCInfo(BaseModel):
    name: str
    age: Optional[int] = None
    role: Optional[str] = None


class NPCDetail(BaseModel):
    name: str
    age: Optional[int] = None
    role: Optional[str] = None
    personality_summary: Optional[str] = None
    traits: List[str] = []
    memory_count: int = 0


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Dynamic NPC Chat API",
        "version": "1.0.0",
        "endpoints": {
            "GET /npcs": "List all available NPCs",
            "GET /npcs/{npc_name}": "Get detailed info about an NPC",
            "POST /chat": "Send a message to an NPC and get a response"
        }
    }


@app.get("/npcs", response_model=List[NPCInfo])
async def list_npcs():
    """Get a list of all available NPCs"""
    try:
        query = """
        MATCH (npc:NPC)
        RETURN npc.name as name, npc.age as age, npc.role as role
        ORDER BY npc.name
        """
        records, _, _ = ex_query(query)
        
        npcs = [
            NPCInfo(
                name=record["name"],
                age=record.get("age"),
                role=record.get("role")
            )
            for record in records
        ]
        
        return npcs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/npcs/{npc_name}", response_model=NPCDetail)
async def get_npc_info(npc_name: str):
    """Get detailed information about a specific NPC"""
    try:
        context = get_npc_context(npc_name)
        
        if not context:
            raise HTTPException(status_code=404, detail=f"NPC '{npc_name}' not found")
        
        npc = context["npc"]
        personality = context.get("personality")
        
        return NPCDetail(
            name=npc["name"],
            age=npc.get("age"),
            role=npc.get("role"),
            personality_summary=personality.get("summary") if personality else None,
            traits=context.get("traits", []),
            memory_count=len(context.get("memories", []))
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to an NPC and get a response.
    
    - **npc_name**: Name of the NPC to chat with (e.g., "Elin von Dahlen")
    - **message**: Your message to the NPC
    """
    try:
        response = chat_with_npc(request.npc_name, request.message)
        
        return ChatResponse(
            npc_name=request.npc_name,
            response=response
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        ex_query("RETURN 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
