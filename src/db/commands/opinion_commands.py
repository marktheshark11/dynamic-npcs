from .base import Command
from ..repositories import NPCRepo, GroupRepo, ClaimRepo, OpinionRepo
from ..models import NPC, Group, Claim
from ..ui import InputHelpers


class CreateOpinionCommand(Command):
    def __init__(self, npc_repo: NPCRepo, group_repo: GroupRepo,
                 claim_repo: ClaimRepo, opinion_repo: OpinionRepo,
                 ui: InputHelpers) -> None:
        self._npc_repo = npc_repo
        self._group_repo = group_repo
        self._claim_repo = claim_repo
        self._opinion_repo = opinion_repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Koppla NPC/Grupp till CLAIM"

    def execute(self) -> None:
        # Choose entity type
        entity_type = self._ui.select_option(["NPC", "GROUP"], "Valj entitetstyp")
        if not entity_type:
            return

        # Select entity
        if entity_type == "NPC":
            npcs = self._npc_repo.list_all()
            selected = self._ui.select_from_list(npcs, NPC.short_str, "Valj NPC")
            if not selected:
                return
            entity_id = selected.id
        else:
            groups = self._group_repo.list_all()
            selected = self._ui.select_from_list(groups, Group.display_str, "Valj grupp")
            if not selected:
                return
            entity_id = selected.name

        # Select claim
        claims = self._claim_repo.list_all()
        claim = self._ui.select_from_list(claims, Claim.short_str, "Valj CLAIM")
        if not claim:
            return

        prefix = self._ui.prompt_optional("prefix")
        suffix = self._ui.prompt_optional("suffix")
        prefix_en = self._ui.prompt_optional("prefix_en")
        suffix_en = self._ui.prompt_optional("suffix_en")
        overwrite_suffix = self._ui.prompt_optional("overwrite_suffix (används när spelaren redan är aware_of, lämna tomt för default)")
        overwrite_suffix_en = self._ui.prompt_optional("overwrite_suffix_en")

        if self._opinion_repo.create(entity_id, entity_type, claim.claim_id,
                                     prefix, suffix, prefix_en, suffix_en, overwrite_suffix, overwrite_suffix_en):
            self._ui.display.success(
                f"HAS_OPINION: {entity_id} -> {claim.claim_id} "
                f"(prefix: {prefix or '-'}, suffix: {suffix or '-'}, prefix_en: {prefix_en or '-'}, suffix_en: {suffix_en or '-'}, overwrite_suffix: {overwrite_suffix or '-'}, overwrite_suffix_en: {overwrite_suffix_en or '-'})"
            )
        else:
            self._ui.display.error(
                f"Kunde inte skapa koppling. Kontrollera att entiteten och CLAIM finns."
            )


class EditOpinionCommand(Command):
    def __init__(self, npc_repo: NPCRepo, group_repo: GroupRepo,
                 opinion_repo: OpinionRepo, ui: InputHelpers) -> None:
        self._npc_repo = npc_repo
        self._group_repo = group_repo
        self._opinion_repo = opinion_repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Redigera en opinion-koppling"

    def execute(self) -> None:
        entity_type = self._ui.select_option(["NPC", "GROUP"], "Valj entitetstyp")
        if not entity_type:
            return

        if entity_type == "NPC":
            npcs = self._npc_repo.list_all()
            selected = self._ui.select_from_list(npcs, NPC.short_str, "Valj NPC")
            if not selected:
                return
            entity_id = selected.id
        else:
            groups = self._group_repo.list_all()
            selected = self._ui.select_from_list(groups, Group.display_str, "Valj grupp")
            if not selected:
                return
            entity_id = selected.name

        opinions = self._opinion_repo.list_for_entity(entity_id, entity_type)
        if not opinions:
            self._ui.display.error("Inga opinions hittades")
            return

        display_fn = lambda o: (
            f"{o.claim_id}: {o.claim_content[:40]}... "
            f"(prefix: {o.prefix or '-'}, suffix: {o.suffix or '-'}, prefix_en: {o.prefix_en or '-'}, suffix_en: {o.suffix_en or '-'}, overwrite_suffix: {o.overwrite_suffix or '-'}, overwrite_suffix_en: {o.overwrite_suffix_en or '-'})"
        )
        opinion = self._ui.select_from_list(opinions, display_fn, "Valj opinion")
        if not opinion:
            return

        self._ui.display.info(f"Nuvarande prefix: {opinion.prefix or '-'}")
        self._ui.display.info(f"Nuvarande suffix: {opinion.suffix or '-'}")
        self._ui.display.info(f"Nuvarande prefix_en: {opinion.prefix_en or '-'}")
        self._ui.display.info(f"Nuvarande suffix_en: {opinion.suffix_en or '-'}")
        self._ui.display.info(f"Nuvarande overwrite_suffix: {opinion.overwrite_suffix or '-'}")
        self._ui.display.info(f"Nuvarande overwrite_suffix_en: {opinion.overwrite_suffix_en or '-'}")

        prefix = self._ui.prompt_optional("ny prefix")
        suffix = self._ui.prompt_optional("ny suffix")
        prefix_en = self._ui.prompt_optional("ny prefix_en")
        suffix_en = self._ui.prompt_optional("ny suffix_en")
        overwrite_suffix = self._ui.prompt_optional("ny overwrite_suffix (används när spelaren redan är aware_of, lämna tomt för default)")
        overwrite_suffix_en = self._ui.prompt_optional("ny overwrite_suffix_en")

        if self._opinion_repo.update(
            entity_id,
            entity_type,
            opinion.claim_id,
            prefix,
            suffix,
            prefix_en,
            suffix_en,
            overwrite_suffix,
            overwrite_suffix_en,
        ):
            self._ui.display.success(
                f"Opinion uppdaterad for {opinion.claim_id} "
                f"(prefix: {prefix or '-'}, suffix: {suffix or '-'}, prefix_en: {prefix_en or '-'}, suffix_en: {suffix_en or '-'}, overwrite_suffix: {overwrite_suffix or '-'}, overwrite_suffix_en: {overwrite_suffix_en or '-'})"
            )
        else:
            self._ui.display.error("Kunde inte uppdatera opinion")


class DeleteOpinionCommand(Command):
    def __init__(self, npc_repo: NPCRepo, group_repo: GroupRepo,
                 opinion_repo: OpinionRepo, ui: InputHelpers) -> None:
        self._npc_repo = npc_repo
        self._group_repo = group_repo
        self._opinion_repo = opinion_repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Ta bort en opinion-koppling"

    def execute(self) -> None:
        entity_type = self._ui.select_option(["NPC", "GROUP"], "Valj entitetstyp")
        if not entity_type:
            return

        if entity_type == "NPC":
            npcs = self._npc_repo.list_all()
            selected = self._ui.select_from_list(npcs, NPC.short_str, "Valj NPC")
            if not selected:
                return
            entity_id = selected.id
        else:
            groups = self._group_repo.list_all()
            selected = self._ui.select_from_list(groups, Group.display_str, "Valj grupp")
            if not selected:
                return
            entity_id = selected.name

        opinions = self._opinion_repo.list_for_entity(entity_id, entity_type)
        if not opinions:
            self._ui.display.error("Inga opinions hittades")
            return

        display_fn = lambda o: (
            f"{o.claim_id}: {o.claim_content[:40]}... "
            f"(prefix: {o.prefix or '-'}, suffix: {o.suffix or '-'}, prefix_en: {o.prefix_en or '-'}, suffix_en: {o.suffix_en or '-'}, overwrite_suffix: {o.overwrite_suffix or '-'}, overwrite_suffix_en: {o.overwrite_suffix_en or '-'})"
        )
        opinion = self._ui.select_from_list(opinions, display_fn, "Valj opinion")
        if not opinion:
            return

        if self._ui.confirm(f"Ta bort opinion for {opinion.claim_id}?"):
            if self._opinion_repo.delete(entity_id, entity_type, opinion.claim_id):
                self._ui.display.success("Opinion borttagen")
            else:
                self._ui.display.error("Kunde inte ta bort opinion")


class ListOpinionsCommand(Command):
    def __init__(self, npc_repo: NPCRepo, group_repo: GroupRepo,
                 opinion_repo: OpinionRepo, ui: InputHelpers) -> None:
        self._npc_repo = npc_repo
        self._group_repo = group_repo
        self._opinion_repo = opinion_repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Visa opinions for en entitet"

    def execute(self) -> None:
        entity_type = self._ui.select_option(["NPC", "GROUP"], "Valj entitetstyp")
        if not entity_type:
            return

        if entity_type == "NPC":
            npcs = self._npc_repo.list_all()
            selected = self._ui.select_from_list(npcs, NPC.short_str, "Valj NPC")
            if not selected:
                return
            entity_id = selected.id
        else:
            groups = self._group_repo.list_all()
            selected = self._ui.select_from_list(groups, Group.display_str, "Valj grupp")
            if not selected:
                return
            entity_id = selected.name

        opinions = self._opinion_repo.list_for_entity(entity_id, entity_type)
        if not opinions:
            self._ui.display.error("Inga opinions hittades")
            return

        self._ui.display.header(f"Opinions for {entity_id}")
        for o in opinions:
            content_preview = o.claim_content[:50] + "..." if len(o.claim_content) > 50 else o.claim_content
            print(f"  {o.claim_id}: {content_preview}")
            print(f"    prefix: {o.prefix or '-'}, suffix: {o.suffix or '-'}, prefix_en: {o.prefix_en or '-'}, suffix_en: {o.suffix_en or '-'}, overwrite_suffix: {o.overwrite_suffix or '-'}, overwrite_suffix_en: {o.overwrite_suffix_en or '-'}")
