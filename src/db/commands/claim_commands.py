from .base import Command
from ..repositories import (
    ClaimRepo, NPCRepo, GroupRepo, ConstantRepo, OpinionRepo, RelationRepo,
)
from ..repositories.mystery_repo import MysteryRepo
from ..models import NPC, Group, Claim
from ..models.mystery import Mystery
from ..ui import InputHelpers


class CreateClaimCommand(Command):
    def __init__(self, claim_repo: ClaimRepo, npc_repo: NPCRepo,
                 group_repo: GroupRepo, constant_repo: ConstantRepo,
                 opinion_repo: OpinionRepo, relation_repo: RelationRepo,
                 mystery_repo: MysteryRepo,
                 ui: InputHelpers) -> None:
        self._claim_repo = claim_repo
        self._npc_repo = npc_repo
        self._group_repo = group_repo
        self._constant_repo = constant_repo
        self._opinion_repo = opinion_repo
        self._relation_repo = relation_repo
        self._mystery_repo = mystery_repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Skapa en ny CLAIM"

    def execute(self) -> None:
        content = self._ui.prompt("content")
        is_relation = self._ui.confirm("Ar detta en relations-claim?")
        claim_type = "relation" if is_relation else None

        claim = self._claim_repo.create(content, claim_type=claim_type)
        self._ui.display.success(f"CLAIM {claim.claim_id} skapad: '{content}'")

        self._link_to_mystery(claim)
        self._add_opinions_to_claim(claim)
        self._add_references_from_claim(claim)

    def _link_to_mystery(self, claim: Claim) -> None:
        while self._ui.confirm("Vill du koppla denna CLAIM till ett mysterium?"):
            mysteries = self._mystery_repo.list_all()
            if not mysteries:
                self._ui.display.error("Inga mysterier finns. Skapa ett mysterium först.")
                break

            mystery = self._ui.select_from_list(
                mysteries, Mystery.display_str, "Välj mysterium"
            )
            if not mystery:
                continue

            if self._mystery_repo.link_claim(claim.claim_id, mystery.name):
                self._ui.display.success(
                    f"CLAIM {claim.claim_id} kopplad till '{mystery.name}'"
                )
            else:
                self._ui.display.error("Kunde inte koppla claim till mysteriet")

    def _add_opinions_to_claim(self, claim: Claim) -> None:
        while self._ui.confirm("Vill du lagga till en opinion till denna CLAIM?"):
            entity_type = self._ui.select_option(["NPC", "GROUP"], "Valj entitetstyp")
            if not entity_type:
                self._ui.display.error("Ingen opinion skapad")
                continue

            if entity_type == "NPC":
                npcs = self._npc_repo.list_all()
                entity = self._ui.select_from_list(npcs, NPC.short_str, "Valj NPC")
                if not entity:
                    self._ui.display.error("Ingen opinion skapad")
                    continue
                entity_id = entity.id
            else:
                groups = self._group_repo.list_all()
                entity = self._ui.select_from_list(groups, Group.display_str, "Valj grupp")
                if not entity:
                    self._ui.display.error("Ingen opinion skapad")
                    continue
                entity_id = entity.name

            prefix = self._ui.prompt_optional("prefix")
            suffix = self._ui.prompt_optional("suffix")

            if self._opinion_repo.create(entity_id, entity_type, claim.claim_id,
                                         prefix, suffix):
                self._ui.display.success(
                    f"HAS_OPINION: {entity_id} -> {claim.claim_id} "
                    f"(prefix: {prefix or '-'}, suffix: {suffix or '-'})"
                )
            else:
                self._ui.display.error(
                    "Kunde inte skapa opinion. Kontrollera att entiteten finns."
                )

    def _add_references_from_claim(self, claim: Claim) -> None:
        while self._ui.confirm("Vill du lagga till en reference fran denna CLAIM?"):
            target_type = self._ui.select_option(
                ["NPC", "CLAIM", "OBJECT", "PLACE"], "Maltyp"
            )
            if not target_type:
                self._ui.display.error("Ingen reference skapad")
                continue

            if target_type == "NPC":
                npcs = self._npc_repo.list_all()
                npc = self._ui.select_from_list(npcs, NPC.short_str, "Valj NPC")
                if not npc:
                    self._ui.display.error("Ingen reference skapad")
                    continue
                target_name = npc.name
            elif target_type == "CLAIM":
                claims = [
                    c for c in self._claim_repo.list_all()
                    if c.claim_id != claim.claim_id
                ]
                target_claim = self._ui.select_from_list(
                    claims, Claim.short_str, "Valj CLAIM (mal)"
                )
                if not target_claim:
                    self._ui.display.error("Ingen reference skapad")
                    continue
                target_name = target_claim.claim_id
            elif target_type == "OBJECT":
                objects = self._constant_repo.list_objects()
                obj = self._ui.select_from_list(objects, lambda o: o.name, "Valj OBJECT")
                if not obj:
                    self._ui.display.error("Ingen reference skapad")
                    continue
                target_name = obj.name
            else:
                places = self._constant_repo.list_places()
                place = self._ui.select_from_list(places, lambda p: p.name, "Valj PLACE")
                if not place:
                    self._ui.display.error("Ingen reference skapad")
                    continue
                target_name = place.name

            if self._relation_repo.create_reference(claim.claim_id, target_name, target_type):
                self._ui.display.success(
                    f"REFERENCE: {claim.claim_id} -> [{target_type}] {target_name}"
                )
            else:
                self._ui.display.error("Kunde inte skapa referens")


class EditClaimCommand(Command):
    def __init__(self, repo: ClaimRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Redigera en CLAIM"

    def execute(self) -> None:
        claims = self._repo.list_all()
        selected = self._ui.select_from_list(claims, Claim.display_str, "Alla CLAIMs")
        if not selected:
            return

        self._ui.display.info(f"Nuvarande content: {selected.content}")
        self._ui.display.info(f"Nuvarande type: {selected.type or '(ingen)'}")

        new_content = self._ui.prompt_optional("nytt content")

        type_choice = self._ui.select_option(
            ["relation", "ta bort type", "behall nuvarande"],
            "Ny type",
        )
        if type_choice == "relation":
            update_ok = self._repo.update(
                selected.claim_id,
                content=new_content,
                claim_type="relation",
            )
        elif type_choice == "ta bort type":
            update_ok = self._repo.update(
                selected.claim_id,
                content=new_content,
                claim_type="",
            )
        else:
            update_ok = self._repo.update(selected.claim_id, content=new_content)

        if update_ok:
            self._ui.display.success(f"CLAIM {selected.claim_id} uppdaterad")
        else:
            self._ui.display.error("Inga andringar gjorda")


class ReindexClaimIdsCommand(Command):
    def __init__(self, repo: ClaimRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Ratta till CLAIM-IDn"

    def execute(self) -> None:
        claims = self._repo.list_all()
        if not claims:
            self._ui.display.error("Inga CLAIMs hittades")
            return

        if not self._ui.confirm("Ratta till CLAIM-IDn till C1, C2, C3 utan gap?"):
            return

        changes = self._repo.reindex_claim_ids()
        if not changes:
            self._ui.display.info("CLAIM-IDn var redan i ratt ordning utan gap")
            return

        self._ui.display.success(f"Rattade till {len(changes)} CLAIM-IDn")
        self._ui.display.header("Andringar")
        for old_id, new_id in changes:
            self._ui.display.info(f"{old_id} -> {new_id}")


class DeleteClaimCommand(Command):
    def __init__(self, repo: ClaimRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Ta bort en CLAIM"

    def execute(self) -> None:
        claims = self._repo.list_all()
        selected = self._ui.select_from_list(claims, Claim.display_str, "Alla CLAIMs")
        if not selected:
            return

        if self._ui.confirm(f"Ta bort CLAIM {selected.claim_id}?"):
            ok, counts = self._repo.delete(selected.claim_id)
            if ok:
                self._ui.display.success(f"CLAIM {selected.claim_id} borttagen")
                if counts["opinions"] > 0:
                    self._ui.display.info(
                        f"{counts['opinions']} HAS_OPINION relationer borttagna"
                    )
                if counts["references"] > 0:
                    self._ui.display.info(
                        f"{counts['references']} REFERENCE relationer borttagna"
                    )
                if counts["mysteries"] > 0:
                    self._ui.display.info(
                        f"{counts['mysteries']} PART_OF (mysterium) relationer borttagna"
                    )
                if counts.get("other_relations", 0) > 0:
                    self._ui.display.info(
                        f"{counts['other_relations']} ovriga relationer borttagna"
                    )
            else:
                self._ui.display.error("Kunde inte ta bort CLAIM")


class ListClaimsCommand(Command):
    def __init__(self, repo: ClaimRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Visa alla CLAIMs"

    def execute(self) -> None:
        claims = self._repo.list_all()
        if not claims:
            self._ui.display.error("Inga CLAIMs hittades")
            return
        self._ui.display.header("Alla CLAIMs")
        self._ui.display.list_items(claims, Claim.display_str)


class RegenerateEmbeddingsCommand(Command):
    def __init__(self, repo: ClaimRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Regenerera embeddings for alla CLAIMs"

    def execute(self) -> None:
        if not self._ui.confirm("Detta kommer regenerera embeddings for ALLA claims. Fortsatt?"):
            return

        claims = self._repo.list_all()
        if not claims:
            self._ui.display.error("Inga claims att uppdatera.")
            return

        count = 0
        total = len(claims)
        print(f"Startar uppdatering av {total} claims...")

        for claim in claims:
            # Genom att anropa update med samma content triggar vi en ny embedding-utrakning
            # i ClaimRepo, som nu anvander den korrigerade 'hf_embeddings.py'-logiken.
            ok = self._repo.update(claim.claim_id, content=claim.content)
            if ok:
                count += 1
                if count % 10 == 0:
                    print(f"  Uppdaterat {count}/{total}...")
            else:
                print(f"  ! Misslyckades med {claim.claim_id}")

        self._ui.display.success(f"Klart! {count}/{total} claims har fatt nya embeddings.")
