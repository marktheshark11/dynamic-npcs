from .config import Config
from .services import EmbeddingService
from .repositories import (
    NPCRepo, GroupRepo, ClaimRepo, ConstantRepo, OpinionRepo, RelationRepo,
    MysteryRepo, ConversationRepo,
)
from .commands import (
    CreateNPCCommand, EditNPCCommand, DeleteNPCCommand, ListNPCsCommand,
    CreateGroupCommand, DeleteGroupCommand, ListGroupsCommand,
    CreateClaimCommand, EditClaimCommand, DeleteClaimCommand,
    ListClaimsCommand, ReindexClaimIdsCommand,
    CreateObjectCommand, CreatePlaceCommand, ListConstantsCommand,
    CreateOpinionCommand, EditOpinionCommand,
    DeleteOpinionCommand, ListOpinionsCommand,
    CreateStructuralRelationCommand,
    CreateReferenceCommand, CreateMembershipCommand, DeleteMembershipCommand,
    CreateMysteryCommand, DeleteMysteryCommand, ListMysteriesCommand,
    LinkClaimToMysteryCommand, UnlinkClaimFromMysteryCommand,
    ListClaimsByMysteryCommand,
    ListConversationsCommand, DeleteConversationCommand, DeleteAllConversationsCommand,
    SummarizeConversationCommand,
)
from .ui import InputHelpers, Menu, SubMenu
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
        self._opinion_repo = OpinionRepo(config.driver)
        self._relation_repo = RelationRepo(config.driver)
        self._mystery_repo = MysteryRepo(config.driver)
        self._conversation_repo = ConversationRepo(config.driver)
        self._chat_service = ChatService(config.driver, config.embed_model)

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
                    ui,
                ),
                EditClaimCommand(self._claim_repo, ui),
                DeleteClaimCommand(self._claim_repo, ui),
                ListClaimsCommand(self._claim_repo, ui),
                ReindexClaimIdsCommand(self._claim_repo, ui),
            ]),
            SubMenu("Konstanter (Objekt/Platser)", [
                CreateObjectCommand(self._constant_repo, ui),
                CreatePlaceCommand(self._constant_repo, ui),
                ListConstantsCommand(self._constant_repo, ui),
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
        ])

        main_menu.run()
