from .config import Config
from .services import EmbeddingService
from .repositories import (
    NPCRepo, GroupRepo, ClaimRepo, ConstantRepo, OpinionRepo, RelationRepo,
    MysteryRepo, ConversationRepo, PlayerRepo, FormRepo,
)
from .commands import (
    CreateNPCCommand, EditNPCCommand, DeleteNPCCommand, ListNPCsCommand,
    CreateGroupCommand, DeleteGroupCommand, ListGroupsCommand,
    CreateClaimCommand, EditClaimCommand, DeleteClaimCommand,
    ListClaimsCommand, RegenerateEmbeddingsCommand,
    CreateObjectCommand, CreatePlaceCommand, CreateItemCommand, CreateDoorCommand,
    DeleteObjectCommand, DeletePlaceCommand, DeleteItemCommand, DeleteDoorCommand,
    EditItemCommand, EditDoorCommand,
    ListConstantsCommand, ListItemsCommand, ListDoorsCommand,
    CreateFormCommand, ListFormsCommand, CreateFormQuestionCommand, EditFormQuestionCommand,
    ListFormQuestionsCommand,
    CreateOpinionCommand, EditOpinionCommand,
    DeleteOpinionCommand, ListOpinionsCommand,
    CreateStructuralRelationCommand,
    CreateReferenceCommand, CreateMembershipCommand, DeleteMembershipCommand,
    CreateMysteryCommand, DeleteMysteryCommand, ListMysteriesCommand,
    LinkClaimToMysteryCommand, UnlinkClaimFromMysteryCommand,
    ListClaimsByMysteryCommand,
    ListConversationsCommand, DeleteConversationCommand, DeleteAllConversationsCommand,
    SummarizeConversationCommand,
    CreatePlayerCommand, EditPlayerCommand, DeletePlayerCommand,
    InspectItemCommand, PickupItemCommand, ListPlayerInventoryCommand,
    ClearAwareOfCommand,
)
from .ui import InputHelpers, Menu, SubMenu
from pipelines import get_pipeline
from services.chat_service import ChatService


class App:
    """Main application. Wires dependencies and builds the menu tree."""

    def __init__(self, config: Config) -> None:
        # Services
        embedding = EmbeddingService(config.embed_model)

        # Repositories
        self._npc_repo = NPCRepo(config.driver)
        self._group_repo = GroupRepo(config.driver)
        self._claim_repo = ClaimRepo(config.driver, embedding)
        self._constant_repo = ConstantRepo(config.driver)
        self._form_repo = FormRepo(config.driver)
        self._opinion_repo = OpinionRepo(config.driver)
        self._relation_repo = RelationRepo(config.driver)
        self._mystery_repo = MysteryRepo(config.driver)
        self._conversation_repo = ConversationRepo(config.driver)
        self._player_repo = PlayerRepo(config.driver)
        pipeline = get_pipeline(
            pipeline_id=config.pipeline_id,
            driver=config.driver,
            embed_model=config.embed_model,
        )
        self._chat_service = ChatService(
            config.driver,
            config.embed_model,
            pipeline=pipeline,
        )

        # UI
        self._ui = InputHelpers()

    def run(self) -> None:
        ui = self._ui

        main_menu = Menu("Huvudmeny", [
            SubMenu("NPC", [
                CreateNPCCommand(self._npc_repo, ui),
                EditNPCCommand(self._npc_repo, ui),
                DeleteNPCCommand(self._npc_repo, ui),
                ListNPCsCommand(self._npc_repo, ui),
            ]),
            SubMenu("Grupper", [
                CreateGroupCommand(self._group_repo, ui),
                DeleteGroupCommand(self._group_repo, ui),
                ListGroupsCommand(self._group_repo, ui),
            ]),
            SubMenu("Claims", [
                CreateClaimCommand(
                    self._claim_repo,
                    self._npc_repo,
                    self._group_repo,
                    self._constant_repo,
                    self._opinion_repo,
                    self._relation_repo,
                    self._mystery_repo,
                    ui,
                ),
                EditClaimCommand(self._claim_repo, ui),
                DeleteClaimCommand(self._claim_repo, ui),
                ListClaimsCommand(self._claim_repo, ui),
                RegenerateEmbeddingsCommand(self._claim_repo, ui),
            ]),
            SubMenu("Konstanter (Objekt/Platser)", [
                CreateObjectCommand(self._constant_repo, ui),
                DeleteObjectCommand(self._constant_repo, ui),
                CreatePlaceCommand(self._constant_repo, ui),
                DeletePlaceCommand(self._constant_repo, ui),
                CreateItemCommand(self._constant_repo, ui),
                EditItemCommand(self._constant_repo, ui),
                DeleteItemCommand(self._constant_repo, ui),
                CreateDoorCommand(self._constant_repo, ui),
                EditDoorCommand(self._constant_repo, ui),
                DeleteDoorCommand(self._constant_repo, ui),
                ListConstantsCommand(self._constant_repo, ui),
                ListItemsCommand(self._constant_repo, ui),
                ListDoorsCommand(self._constant_repo, ui),
            ]),
            SubMenu("Formulär", [
                CreateFormCommand(self._form_repo, ui),
                ListFormsCommand(self._form_repo, ui),
                CreateFormQuestionCommand(self._form_repo, ui),
                EditFormQuestionCommand(self._form_repo, ui),
                ListFormQuestionsCommand(self._form_repo, ui),
            ]),
            SubMenu("Opinions (kopplingar)", [
                CreateOpinionCommand(
                    self._npc_repo, self._group_repo,
                    self._claim_repo, self._opinion_repo, ui,
                ),
                EditOpinionCommand(
                    self._npc_repo, self._group_repo,
                    self._opinion_repo, ui,
                ),
                DeleteOpinionCommand(
                    self._npc_repo, self._group_repo,
                    self._opinion_repo, ui,
                ),
                ListOpinionsCommand(
                    self._npc_repo, self._group_repo,
                    self._opinion_repo, ui,
                ),
            ]),
            SubMenu("Relationer", [
                CreateStructuralRelationCommand(
                    self._npc_repo, self._relation_repo, ui,
                ),
                CreateReferenceCommand(
                    self._npc_repo, self._claim_repo,
                    self._constant_repo, self._relation_repo, ui,
                ),
                CreateMembershipCommand(
                    self._npc_repo, self._group_repo,
                    self._relation_repo, ui,
                ),
                DeleteMembershipCommand(
                    self._npc_repo, self._group_repo,
                    self._relation_repo, ui,
                ),
            ]),
            SubMenu("Mysterier", [
                CreateMysteryCommand(self._mystery_repo, ui),
                DeleteMysteryCommand(self._mystery_repo, ui),
                ListMysteriesCommand(self._mystery_repo, ui),
                LinkClaimToMysteryCommand(
                    self._mystery_repo, self._claim_repo, ui,
                ),
                UnlinkClaimFromMysteryCommand(
                    self._mystery_repo, self._claim_repo, ui,
                ),
                ListClaimsByMysteryCommand(self._mystery_repo, ui),
            ]),
            SubMenu("Konversationer", [
                ListConversationsCommand(self._conversation_repo, ui),
                SummarizeConversationCommand(self._conversation_repo, self._chat_service, ui),
                DeleteConversationCommand(self._conversation_repo, ui),
                DeleteAllConversationsCommand(self._conversation_repo, ui),
            ]),
            SubMenu("Player", [
                CreatePlayerCommand(self._player_repo, ui),
                EditPlayerCommand(self._player_repo, ui),
                DeletePlayerCommand(self._player_repo, ui),
                InspectItemCommand(self._player_repo, self._constant_repo, ui),
                PickupItemCommand(self._player_repo, self._constant_repo, ui),
                ListPlayerInventoryCommand(self._player_repo, ui),
                ClearAwareOfCommand(self._player_repo, ui),
            ]),
        ])

        main_menu.run()
