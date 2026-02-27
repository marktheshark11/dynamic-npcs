from .base import Command
from ..repositories import NPCRepo, GroupRepo, ClaimRepo, ConstantRepo, RelationRepo
from ..repositories.relation_repo import STRUCTURAL_RELATIONS
from ..models import NPC, Claim
from ..ui import InputHelpers


class CreateStructuralRelationCommand(Command):
    def __init__(self, npc_repo: NPCRepo, relation_repo: RelationRepo,
                 ui: InputHelpers) -> None:
        self._npc_repo = npc_repo
        self._relation_repo = relation_repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Skapa strukturell relation"

    def execute(self) -> None:
        npcs = self._npc_repo.list_all()

        print("\n--- Valj forsta NPC ---")
        npc_a = self._ui.select_from_list(npcs, NPC.short_str, "NPC A")
        if not npc_a:
            return

        print("\n--- Valj andra NPC ---")
        npc_b = self._ui.select_from_list(npcs, NPC.short_str, "NPC B")
        if not npc_b:
            return

        rel_types = list(STRUCTURAL_RELATIONS.keys())
        rel_type = self._ui.select_option(rel_types, "Relationstyp")
        if not rel_type:
            return

        secrecy = self._ui.prompt_float("secrecy", min_val=0.0, max_val=1.0)

        if self._relation_repo.create_structural(npc_a.name, npc_b.name, rel_type, secrecy):
            inverse = STRUCTURAL_RELATIONS[rel_type]
            self._ui.display.success(f"{npc_a.name} {rel_type} {npc_b.name}")
            self._ui.display.info(f"{npc_b.name} {inverse} {npc_a.name}")
            self._ui.display.info(f"secrecy: {secrecy}")
        else:
            self._ui.display.error("Ogiltig relationstyp")


class CreateReferenceCommand(Command):
    def __init__(self, npc_repo: NPCRepo, claim_repo: ClaimRepo,
                 constant_repo: ConstantRepo, relation_repo: RelationRepo,
                 ui: InputHelpers) -> None:
        self._npc_repo = npc_repo
        self._claim_repo = claim_repo
        self._constant_repo = constant_repo
        self._relation_repo = relation_repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Skapa REFERENCE fran CLAIM"

    def execute(self) -> None:
        # Select source claim
        claims = self._claim_repo.list_all()
        source = self._ui.select_from_list(claims, Claim.short_str, "Valj CLAIM (kalla)")
        if not source:
            return

        # Select target type
        target_type = self._ui.select_option(
            ["NPC", "CLAIM", "OBJECT", "PLACE"], "Maltyp"
        )
        if not target_type:
            return

        # Select target
        if target_type == "NPC":
            npcs = self._npc_repo.list_all()
            npc = self._ui.select_from_list(npcs, NPC.short_str, "Valj NPC")
            if not npc:
                return
            target_name = npc.name
        elif target_type == "CLAIM":
            target_claim = self._ui.select_from_list(claims, Claim.short_str, "Valj CLAIM (mal)")
            if not target_claim:
                return
            target_name = target_claim.claim_id
        elif target_type == "OBJECT":
            objects = self._constant_repo.list_objects()
            obj = self._ui.select_from_list(objects, lambda o: o.name, "Valj OBJECT")
            if not obj:
                return
            target_name = obj.name
        else:  # PLACE
            places = self._constant_repo.list_places()
            place = self._ui.select_from_list(places, lambda p: p.name, "Valj PLACE")
            if not place:
                return
            target_name = place.name

        if self._relation_repo.create_reference(source.claim_id, target_name, target_type):
            self._ui.display.success(
                f"REFERENCE: {source.claim_id} -> [{target_type}] {target_name}"
            )
        else:
            self._ui.display.error("Kunde inte skapa referens")


class CreateMembershipCommand(Command):
    def __init__(self, npc_repo: NPCRepo, group_repo: GroupRepo,
                 relation_repo: RelationRepo, ui: InputHelpers) -> None:
        self._npc_repo = npc_repo
        self._group_repo = group_repo
        self._relation_repo = relation_repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Lagg till NPC i grupp"

    def execute(self) -> None:
        npcs = self._npc_repo.list_all()
        npc = self._ui.select_from_list(npcs, NPC.short_str, "Valj NPC")
        if not npc:
            return

        from db.models import Group
        groups = self._group_repo.list_all()
        group = self._ui.select_from_list(groups, Group.display_str, "Valj grupp")
        if not group:
            return

        if self._relation_repo.create_membership(npc.id, group.name):
            self._ui.display.success(f"{npc.name} ar nu medlem i {group.name}")
        else:
            self._ui.display.error("Kunde inte skapa medlemskap")


class DeleteMembershipCommand(Command):
    def __init__(self, npc_repo: NPCRepo, group_repo: GroupRepo,
                 relation_repo: RelationRepo, ui: InputHelpers) -> None:
        self._npc_repo = npc_repo
        self._group_repo = group_repo
        self._relation_repo = relation_repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Ta bort NPC fran grupp"

    def execute(self) -> None:
        from db.models import Group
        groups = self._group_repo.list_all()
        group = self._ui.select_from_list(groups, Group.display_str, "Valj grupp")
        if not group:
            return

        member_ids = self._relation_repo.list_members(group.name)
        if not member_ids:
            self._ui.display.error("Inga medlemmar i gruppen")
            return

        member = self._ui.select_option(member_ids, "Valj NPC att ta bort")
        if not member:
            return

        if self._relation_repo.delete_membership(member, group.name):
            self._ui.display.success(f"{member} borttagen fran {group.name}")
        else:
            self._ui.display.error("Kunde inte ta bort medlemskap")
