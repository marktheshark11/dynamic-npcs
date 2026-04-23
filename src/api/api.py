import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from db.config import Config
from db.repositories import ConstantRepo, FormRepo, PlayerRepo, PlayerTemperatureRepo, UserRepo
from llms.config import (
    DEFAULT_CHAT_MODEL,
    DEFAULT_CHAT_TEMPERATURE,
    PROMPT_GUARD_PROVIDER,
    get_required_chat_api_key,
    resolve_chat_provider,
)
from llms.prompt_guard import PromptGuardValidationError, validate_safe_player_profile
from pipelines import get_pipeline
from services.chat_service import ChatService
from services.door_service import DoorService
from services.locale_service import LocaleService
from services.player_analytics_service import PlayerAnalyticsService
from services.player_temperature_service import (
    PlayerTemperatureService,
    infer_temperature_override_from_player_name,
)
from services.scripted_npc_service import ScriptedNpcService

class ChatResponse(BaseModel):
    npc_id: str
    npc_name: str = ""
    conversation_id: str | None = None
    response: str
    used_claims: list[str] = Field(default_factory=list)
    important_claim_ids: list[str] = Field(default_factory=list)


class StaticNpcChatResponse(BaseModel):
    npc_id: str
    npc_name: str = ""
    conversation_id: str | None = None
    response: str
    game_completed: bool = False
    accused_correct_npc: bool | None = None
    accused_npc_id: str | None = None
    completed_at: str | None = None

class ChatRequest(BaseModel):
    npc_id: str
    message: str
    player_id: str | None = None
    conversation_id: str | None = None


def _print_chat_debug(result: dict) -> None:
    flat_prompt = result.get("flat_prompt") or "(ingen prompt tillganglig)"
    response_text = result.get("response") or ""
    used_claims = result.get("used_claims") or []
    important_claim_ids = result.get("important_claim_ids") or []
    temperature = result.get("temperature")
    selector_debug = result.get("selector_debug") or {}
    selected_claim_ids = selector_debug.get("selected_claim_ids") or []
    selection_notes = selector_debug.get("selection_notes") or []
    selected_claims = selector_debug.get("selected_claims") or []
    candidate_claims = selector_debug.get("candidate_claims") or []

    print("\n" + "=" * 24 + " PROMPT " + "=" * 24, file=sys.stderr)
    print(flat_prompt, file=sys.stderr)
    print("=" * 57, file=sys.stderr)
    if selector_debug:
        print("\n" + "=" * 20 + " SELECTOR " + "=" * 20, file=sys.stderr)
        print(
            f"candidate_claims: {', '.join(claim.get('claim_id') for claim in candidate_claims if claim.get('claim_id')) or '(inga)'}",
            file=sys.stderr,
        )
        print(
            f"selected_for_prompt: {', '.join(selected_claim_ids) if selected_claim_ids else '(inga)'}",
            file=sys.stderr,
        )
        if selected_claims:
            print("selected_claim_details:", file=sys.stderr)
            for claim in selected_claims:
                important_marker = " [VIKTIG]" if claim.get("important") else ""
                print(
                    f"  - {claim.get('claim_id')}{important_marker}: {claim.get('content', '')}",
                    file=sys.stderr,
                )
        if selection_notes:
            print("selection_notes:", file=sys.stderr)
            for note in selection_notes:
                print(f"  - {note}", file=sys.stderr)
        print("=" * 57, file=sys.stderr)
    print("\n" + "=" * 22 + " RESULTAT " + "=" * 21, file=sys.stderr)
    print(f"npc_id: {result.get('npc_id')}", file=sys.stderr)
    print(f"conversation_id: {result.get('conversation_id')}", file=sys.stderr)
    print(f"temperature: {temperature}", file=sys.stderr)
    print(
        f"used_claims: {', '.join(used_claims) if used_claims else '(inga)'}",
        file=sys.stderr,
    )
    print(
        f"important_claim_ids: {', '.join(important_claim_ids) if important_claim_ids else '(inga)'}",
        file=sys.stderr,
    )
    print(f"response: {response_text}", file=sys.stderr)
    print("=" * 57, file=sys.stderr)


class StaticNpcChatRequest(BaseModel):
    npc_id: str
    message: str = ""
    player_id: str | None = None
    conversation_id: str | None = None


class ConversationSummaryRequest(BaseModel):
    conversation_id: str


class ConversationSummaryResponse(BaseModel):
    conversation_id: str
    summary: str
    exchange_count: int


class CreatePlayerRequest(BaseModel):
    name: str
    appearance: str | None = None
    user_id: str | None = None


class CreatePlayerResponse(BaseModel):
    player_id: str
    name: str
    appearance: str | None = None
    temperature: float


class PlayerResponse(BaseModel):
    player_id: str
    name: str
    appearance: str | None = None
    temperature: float


class UpdatePlayerRequest(BaseModel):
    name: str | None = None
    appearance: str | None = None


class AnalyticsProfileResponse(BaseModel):
    name: str | None = None
    appearance: str | None = None
    temperature: float | None = None
    created_at: str | None = None
    completed_at: str | None = None


class AnalyticsUserResponse(BaseModel):
    user_id: str | None = None
    username: str | None = None
    locale: str | None = None
    created_at: str | None = None


class AnalyticsGameResponse(BaseModel):
    has_completed_game: bool
    accused_correct_npc: bool | None = None
    accused_npc_id: str | None = None


class AnalyticsProgressResponse(BaseModel):
    claims_known: int
    items_seen: int
    items_picked_up: int
    doors_seen: int
    doors_opened: int
    forms_answered: int
    conversation_count: int
    exchange_count: int
    unique_npcs_spoken_to: int


class AnalyticsConversationResponse(BaseModel):
    conversation_id: str | None = None
    npc_id: str | None = None
    player_id: str | None = None
    created_at: str | None = None
    ended_at: str | None = None
    summary: str | None = None
    summary_updated_at: str | None = None
    exchange_count: int


class AnalyticsNpcConversationCountResponse(BaseModel):
    npc_id: str
    conversation_count: int


class AnalyticsConversationMetricsResponse(BaseModel):
    by_npc: list[AnalyticsNpcConversationCountResponse] = Field(default_factory=list)
    conversations: list[AnalyticsConversationResponse] = Field(default_factory=list)


class AnalyticsFormAnswerResponse(BaseModel):
    question_id: str
    question: str | None = None
    value_type: str
    order: int
    raw_answer: str | None = None
    answer_text: str | None = None
    answer_int: int | None = None
    answer_bool: bool | None = None


class AnalyticsFormResponse(BaseModel):
    form_id: str
    name: str | None = None
    description: str | None = None
    answers: list[AnalyticsFormAnswerResponse] = Field(default_factory=list)


class PlayerAnalyticsSummaryResponse(BaseModel):
    player_id: str
    locale: str
    user: AnalyticsUserResponse | None = None
    profile: AnalyticsProfileResponse
    game: AnalyticsGameResponse
    progress: AnalyticsProgressResponse
    clues: "ClueResponse"
    forms: list[AnalyticsFormResponse] = Field(default_factory=list)
    conversation_metrics: AnalyticsConversationMetricsResponse


class AnalyticsTimelineEventResponse(BaseModel):
    type: str
    timestamp: str | None = None
    payload: dict = Field(default_factory=dict)


class PlayerAnalyticsTimelineResponse(BaseModel):
    player_id: str
    locale: str
    event_count: int
    events: list[AnalyticsTimelineEventResponse] = Field(default_factory=list)


class PlayerAnalyticsExportResponse(BaseModel):
    exported_at: str
    user: AnalyticsUserResponse | None = None
    player_id: str
    summary: PlayerAnalyticsSummaryResponse
    timeline: PlayerAnalyticsTimelineResponse


class PlayerAnalyticsExportItemResponse(BaseModel):
    player_id: str
    summary: PlayerAnalyticsSummaryResponse
    timeline: PlayerAnalyticsTimelineResponse


class UserAnalyticsExportGroupResponse(BaseModel):
    user: AnalyticsUserResponse | None = None
    player_count: int
    players: list[PlayerAnalyticsExportItemResponse] = Field(default_factory=list)


class PlayerAnalyticsBulkExportResponse(BaseModel):
    exported_at: str
    user_count: int
    users: list[UserAnalyticsExportGroupResponse] = Field(default_factory=list)


class DeletePlayerResponse(BaseModel):
    player_id: str
    deleted: bool


class FormQuestionResponse(BaseModel):
    question_id: str
    question: str
    value_type: str
    order: int
    required: bool = True
    scale_min: int | None = None
    scale_max: int | None = None
    min_label: str | None = None
    max_label: str | None = None


class FormResponse(BaseModel):
    form_id: str
    name: str
    description: str | None = None
    questions: list[FormQuestionResponse] = Field(default_factory=list)


class SaveFormAnswerItemRequest(BaseModel):
    question_id: str
    answer: str | bool | int


class SaveFormRequest(BaseModel):
    answers: list[SaveFormAnswerItemRequest] = Field(default_factory=list)


class SavedFormAnswerResponse(BaseModel):
    question_id: str
    value_type: str
    raw_answer: str
    answer_bool: bool | None = None


class SaveFormResponse(BaseModel):
    player_id: str
    form_id: str
    saved_answers: list[SavedFormAnswerResponse] = Field(default_factory=list)


class PlayerFormQuestionResponse(FormQuestionResponse):
    answer: str | None = None
    answer_bool: bool | None = None


class PlayerFormResponse(BaseModel):
    form_id: str
    name: str
    description: str | None = None
    questions: list[PlayerFormQuestionResponse] = Field(default_factory=list)


def _normalize_locale(locale: str | None) -> str:
    normalized = (locale or "sv").strip().lower()
    if normalized not in UserRepo.SUPPORTED_LOCALES:
        raise HTTPException(status_code=400, detail="locale must be 'sv' or 'en'")
    return normalized


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
    important: bool = False
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
    locale: str = "sv"


class RegisterResponse(BaseModel):
    user_id: str
    username: str
    locale: str
    created_at: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    user_id: str
    username: str
    locale: str
    created_at: str | None = None


class UpdateUserLocaleRequest(BaseModel):
    locale: str


class UserLocaleResponse(BaseModel):
    user_id: str
    locale: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    config = Config.from_env()
    api_key = os.getenv("API_KEY")
    chat_provider = resolve_chat_provider(model=DEFAULT_CHAT_MODEL)
    if not api_key:
        raise RuntimeError("Missing API_KEY in environment")
    get_required_chat_api_key(chat_provider)
    get_required_chat_api_key(PROMPT_GUARD_PROVIDER)

    app.state.config = config
    app.state.api_key = api_key
    app.state.chat_provider = chat_provider
    app.state.startup_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    pipeline = get_pipeline(
        pipeline_id=config.pipeline_id,
        driver=config.driver,
        embed_model=config.embed_model,
    )
    app.state.chat_service = ChatService(
        config.driver,
        config.embed_model,
        pipeline=pipeline,
    )
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


def _get_player_or_404(player_repo: PlayerRepo, player_id: str) -> dict:
    player_profile = player_repo.get_profile_by_id(player_id)
    if not player_profile:
        raise HTTPException(status_code=404, detail="Player not found")
    return player_profile


def _get_form_or_404(form_repo: FormRepo, form_id: str) -> dict:
    form = form_repo.get_form(form_id)
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    return form


def _localized_detail(locale: str, english_text: str, swedish_text: str) -> str:
    return english_text if locale == "en" else swedish_text


def _infer_temperature_from_player_name(name: str) -> float | None:
    return infer_temperature_override_from_player_name(name)


def _ensure_player_not_completed(player_profile: dict, locale: str = "sv") -> None:
    if player_profile.get("has_completed_game"):
        raise HTTPException(
            status_code=409,
            detail=(
                "The game is already completed for this player. Create a new player to continue."
                if locale == "en"
                else "Spelet är redan avslutat för den här spelaren. Skapa en ny spelare för att fortsätta."
            ),
        )

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
async def health_check(request: Request):
    return {
        "status": "ok",
        "startup_timestamp": request.app.state.startup_timestamp,
    }


@app.post("/users/register", response_model=RegisterResponse)
async def register(payload: RegisterRequest, config: Config = Depends(get_config)):
    username = payload.username.strip()
    password = payload.password.strip()
    locale = payload.locale.strip().lower()
    
    if not username:
        raise HTTPException(status_code=400, detail="username cannot be empty")
    if not password:
        raise HTTPException(status_code=400, detail="password cannot be empty")
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="username must be at least 3 characters")
    if len(password) < 3:
        raise HTTPException(status_code=400, detail="password must be at least 3 characters")
    if locale not in UserRepo.SUPPORTED_LOCALES:
        raise HTTPException(status_code=400, detail="locale must be 'sv' or 'en'")
    
    try:
        user_repo = UserRepo(config.driver)
        user = user_repo.register(username=username, password=password, locale=locale)
        
        if not user:
            raise HTTPException(status_code=409, detail="Username already exists")
        
        return RegisterResponse(
            user_id=user.user_id,
            username=user.username,
            locale=user.locale,
            created_at=user.created_at,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
        
        return LoginResponse(
            user_id=user.user_id,
            username=user.username,
            locale=user.locale,
            created_at=user.created_at,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.patch("/users/{user_id}/locale", response_model=UserLocaleResponse)
async def update_user_locale(
    user_id: str,
    payload: UpdateUserLocaleRequest,
    config: Config = Depends(get_config),
):
    normalized_user_id = user_id.strip()
    locale = payload.locale.strip().lower()

    if not normalized_user_id:
        raise HTTPException(status_code=400, detail="user_id cannot be empty")
    if locale not in UserRepo.SUPPORTED_LOCALES:
        raise HTTPException(status_code=400, detail="locale must be 'sv' or 'en'")

    try:
        user_repo = UserRepo(config.driver)
        updated = user_repo.set_locale(normalized_user_id, locale)
        if not updated:
            raise HTTPException(status_code=404, detail="User not found")
        return UserLocaleResponse(user_id=normalized_user_id, locale=locale)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
            return ChatResponse(npc_id=payload.npc_id, npc_name="", response="No response")
        _print_chat_debug(result)
        return ChatResponse(
            npc_id=payload.npc_id,
            npc_name=result.get("npc_name") or "",
            conversation_id=result.get("conversation_id"),
            response=result["response"],
            used_claims=result.get("used_claims") or [],
            important_claim_ids=result.get("important_claim_ids") or [],
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
    config: Config = Depends(get_config),
    scripted_npc_service: ScriptedNpcService = Depends(get_scripted_npc_service),
):
    player_id = payload.player_id.strip() if payload.player_id else None

    try:
        if payload.player_id and not player_id:
            raise HTTPException(status_code=400, detail="player_id cannot be empty")

        if player_id:
            player_repo = PlayerRepo(config.driver)
            player_profile = _get_player_or_404(player_repo, player_id)
            locale = LocaleService(config.driver).get_player_locale(player_id)
            _ensure_player_not_completed(player_profile, locale=locale)

        result = scripted_npc_service.ask_npc(
            npc_id=payload.npc_id,
            question=payload.message,
            player_id=player_id,
            conversation_id=payload.conversation_id,
        )
        return StaticNpcChatResponse(
            npc_id=payload.npc_id,
            npc_name=result.get("npc_name") or "",
            conversation_id=result.get("conversation_id"),
            response=result["response"],
            game_completed=bool(result.get("game_completed")),
            accused_correct_npc=result.get("accused_correct_npc"),
            accused_npc_id=result.get("accused_npc_id"),
            completed_at=result.get("completed_at"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/players", response_model=CreatePlayerResponse)
async def create_player(payload: CreatePlayerRequest, config: Config = Depends(get_config)):
    name = payload.name.strip()
    appearance = payload.appearance.strip() if payload.appearance is not None else None
    user_id = payload.user_id.strip() if payload.user_id else None

    if not name:
        raise HTTPException(status_code=400, detail="name cannot be empty")
    if appearance == "":
        appearance = None

    try:
        validate_safe_player_profile(name=name, appearance=appearance)
    except PromptGuardValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        player_repo = PlayerRepo(config.driver)
        temperature_repo = PlayerTemperatureRepo(config.driver)
        temperature_service = PlayerTemperatureService(temperature_repo)
        temperature = temperature_service.resolve_for_new_player(name)
        player = player_repo.create(name=name, appearance=appearance, user_id=user_id, temperature=temperature)
        return CreatePlayerResponse(
            player_id=player.player_id,
            name=player.name,
            appearance=player.appearance,
            temperature=(
                player.temperature
                if player.temperature is not None
                else DEFAULT_CHAT_TEMPERATURE
            ),
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
                temperature=(
                    player.temperature
                    if player.temperature is not None
                    else DEFAULT_CHAT_TEMPERATURE
                ),
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


@app.patch("/players/{player_id}", response_model=PlayerResponse)
async def update_player(
    player_id: str,
    payload: UpdatePlayerRequest,
    config: Config = Depends(get_config),
):
    normalized_player_id = player_id.strip()
    if not normalized_player_id:
        raise HTTPException(status_code=400, detail="player_id cannot be empty")

    name = payload.name.strip() if payload.name is not None else None
    appearance = payload.appearance.strip() if payload.appearance is not None else None

    if name == "":
        raise HTTPException(status_code=400, detail="name cannot be empty")
    if appearance == "":
        appearance = None

    try:
        player_repo = PlayerRepo(config.driver)
        existing_player = _get_player_or_404(player_repo, normalized_player_id)
        validate_safe_player_profile(
            name=name or existing_player["name"],
            appearance=appearance if appearance is not None else existing_player.get("appearance"),
        )
        updated = player_repo.update(
            normalized_player_id,
            name=name,
            appearance=appearance,
        )
        if not updated:
            raise HTTPException(status_code=400, detail="No player fields to update")

        updated_player = _get_player_or_404(player_repo, normalized_player_id)
        return PlayerResponse(
            player_id=normalized_player_id,
            name=updated_player["name"],
            appearance=updated_player.get("appearance"),
            temperature=float(updated_player.get("temperature") or DEFAULT_CHAT_TEMPERATURE),
        )
    except HTTPException:
        raise
    except PromptGuardValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/players/{player_id}/analytics", response_model=PlayerAnalyticsSummaryResponse)
async def get_player_analytics_summary(player_id: str, config: Config = Depends(get_config)):
    player_id = player_id.strip()
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id cannot be empty")

    try:
        analytics_service = PlayerAnalyticsService(config.driver)
        summary = analytics_service.get_player_summary(player_id)
        if not summary:
            raise HTTPException(status_code=404, detail="Player not found")
        return PlayerAnalyticsSummaryResponse(**summary)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/players/{player_id}/analytics/timeline", response_model=PlayerAnalyticsTimelineResponse)
async def get_player_analytics_timeline(player_id: str, config: Config = Depends(get_config)):
    player_id = player_id.strip()
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id cannot be empty")

    try:
        analytics_service = PlayerAnalyticsService(config.driver)
        timeline = analytics_service.get_player_timeline(player_id)
        if not timeline:
            raise HTTPException(status_code=404, detail="Player not found")
        return PlayerAnalyticsTimelineResponse(**timeline)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/players/{player_id}/analytics/export", response_model=PlayerAnalyticsExportResponse)
async def export_player_analytics(player_id: str, config: Config = Depends(get_config)):
    player_id = player_id.strip()
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id cannot be empty")

    try:
        analytics_service = PlayerAnalyticsService(config.driver)
        export = analytics_service.export_player_analytics(player_id)
        if not export:
            raise HTTPException(status_code=404, detail="Player not found")
        return PlayerAnalyticsExportResponse(**export)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/analytics/export", response_model=PlayerAnalyticsBulkExportResponse)
async def export_all_player_analytics(user_id: str | None = None, config: Config = Depends(get_config)):
    try:
        analytics_service = PlayerAnalyticsService(config.driver)
        if user_id is not None:
            user_id = user_id.strip()
            if not user_id:
                raise HTTPException(status_code=400, detail="user_id cannot be empty")
            export = analytics_service.export_players_for_user(user_id)
        else:
            export = analytics_service.export_players()
        return PlayerAnalyticsBulkExportResponse(**export)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/users/{user_id}/analytics/export", response_model=PlayerAnalyticsBulkExportResponse)
async def export_user_player_analytics(user_id: str, config: Config = Depends(get_config)):
    normalized_user_id = user_id.strip()
    if not normalized_user_id:
        raise HTTPException(status_code=400, detail="user_id cannot be empty")

    try:
        analytics_service = PlayerAnalyticsService(config.driver)
        export = analytics_service.export_players_for_user(normalized_user_id)
        return PlayerAnalyticsBulkExportResponse(**export)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/forms/{form_id}", response_model=FormResponse)
async def get_form(form_id: str, locale: str = "sv", config: Config = Depends(get_config)):
    form_id = form_id.strip()
    if not form_id:
        raise HTTPException(status_code=400, detail="form_id cannot be empty")
    normalized_locale = _normalize_locale(locale)

    try:
        form_repo = FormRepo(config.driver)
        form = form_repo.get_form(form_id, locale=normalized_locale)
        if not form:
            raise HTTPException(status_code=404, detail="Form not found")
        return FormResponse(
            form_id=form["form_id"],
            name=form["name"],
            description=form.get("description"),
            questions=[FormQuestionResponse(**question) for question in form.get("questions", [])],
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/players/{player_id}/forms/{form_id}", response_model=SaveFormResponse)
async def save_player_form(
    player_id: str,
    form_id: str,
    payload: SaveFormRequest,
    config: Config = Depends(get_config),
):
    player_id = player_id.strip()
    form_id = form_id.strip()
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id cannot be empty")
    if not form_id:
        raise HTTPException(status_code=400, detail="form_id cannot be empty")

    try:
        player_repo = PlayerRepo(config.driver)
        form_repo = FormRepo(config.driver)
        _get_player_or_404(player_repo, player_id)
        _get_form_or_404(form_repo, form_id)

        answers = [
            {
                "question_id": item.question_id.strip(),
                "answer": str(item.answer).strip().lower() if isinstance(item.answer, bool) else str(item.answer).strip(),
            }
            for item in payload.answers
        ]
        saved_answers = form_repo.save_player_form_answers(player_id, form_id, answers)
        return SaveFormResponse(
            player_id=player_id,
            form_id=form_id,
            saved_answers=[SavedFormAnswerResponse(**item) for item in saved_answers],
        )
    except ValueError as exc:
        detail = str(exc)
        if detail in {"Player not found", "Form not found"}:
            raise HTTPException(status_code=404, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/players/{player_id}/forms/{form_id}", response_model=PlayerFormResponse)
async def get_player_form(player_id: str, form_id: str, config: Config = Depends(get_config)):
    player_id = player_id.strip()
    form_id = form_id.strip()
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id cannot be empty")
    if not form_id:
        raise HTTPException(status_code=400, detail="form_id cannot be empty")

    try:
        player_repo = PlayerRepo(config.driver)
        form_repo = FormRepo(config.driver)
        _get_player_or_404(player_repo, player_id)
        _get_form_or_404(form_repo, form_id)
        locale = LocaleService(config.driver).get_player_locale(player_id)

        player_form = form_repo.get_player_form_answers(player_id, form_id, locale=locale)
        if not player_form:
            raise HTTPException(status_code=404, detail="Form not found")

        return PlayerFormResponse(
            form_id=player_form["form_id"],
            name=player_form["name"],
            description=player_form.get("description"),
            questions=[PlayerFormQuestionResponse(**question) for question in player_form.get("questions", [])],
        )
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

        _get_player_or_404(player_repo, player_id)

        locale = LocaleService(config.driver).get_player_locale(player_id)
        claims = player_repo.get_aware_claims(player_id, locale=locale)
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

        _get_player_or_404(player_repo, player_id)

        locale = LocaleService(config.driver).get_player_locale(player_id)
        clues = player_repo.get_clues(player_id, locale=locale)
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

        _get_player_or_404(player_repo, player_id)
        locale = LocaleService(config.driver).get_player_locale(player_id)

        item = constant_repo.get_item(object_id, locale=locale)
        if not item:
            raise HTTPException(status_code=404, detail=_localized_detail(locale, "Item not found", "Item hittades inte"))

        seen = player_repo.mark_seen_object(player_id, item.object_id)
        if not seen:
            raise HTTPException(status_code=500, detail=_localized_detail(locale, "Could not mark item as seen", "Kunde inte markera item som sett"))

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

        _get_player_or_404(player_repo, player_id)
        locale = LocaleService(config.driver).get_player_locale(player_id)

        item = constant_repo.get_item(object_id, locale=locale)
        if not item:
            raise HTTPException(status_code=404, detail=_localized_detail(locale, "Item not found", "Item hittades inte"))

        locale = LocaleService(config.driver).get_player_locale(player_id)
        picked_up, detail = player_repo.pickup_item(player_id, item.object_id, locale=locale)
        if not picked_up and detail in {"Item eller player hittades inte", "Item or player not found"}:
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

        _get_player_or_404(player_repo, player_id)
        locale = LocaleService(config.driver).get_player_locale(player_id)

        result = door_service.open_door(player_id, object_id, code=payload.code, locale=locale)
        if result["detail"] in {"Door not found", "Dörr hittades inte"}:
            raise HTTPException(status_code=404, detail=result["detail"])
        return OpenDoorResponse(**result)
    except ValueError as exc:
        if str(exc) in {"Door not found", "Dörr hittades inte"}:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
