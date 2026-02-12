from .base import Command
from ..repositories import ClaimRepo
from ..models import Claim
from ..ui import InputHelpers


class CreateClaimCommand(Command):
    def __init__(self, repo: ClaimRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Skapa en ny CLAIM"

    def execute(self) -> None:
        content = self._ui.prompt("content")
        is_relation = self._ui.confirm("Ar detta en relations-claim?")
        claim_type = "relation" if is_relation else None

        claim = self._repo.create(content, claim_type=claim_type)
        self._ui.display.success(f"CLAIM {claim.claim_id} skapad: '{content}'")


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
            new_type = "relation"
        elif type_choice == "ta bort type":
            new_type = ""
        else:
            new_type = ...  # sentinel: no change

        if self._repo.update(selected.claim_id, content=new_content,
                             claim_type=new_type):
            self._ui.display.success(f"CLAIM {selected.claim_id} uppdaterad")
        else:
            self._ui.display.error("Inga andringar gjorda")


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
            ok, opinion_count = self._repo.delete(selected.claim_id)
            if ok:
                self._ui.display.success(f"CLAIM {selected.claim_id} borttagen")
                if opinion_count > 0:
                    self._ui.display.info(f"{opinion_count} HAS_OPINION relationer borttagna")
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
