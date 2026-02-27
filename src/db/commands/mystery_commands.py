from .base import Command
from ..repositories import ClaimRepo
from ..repositories.mystery_repo import MysteryRepo
from ..models import Claim
from ..models.mystery import Mystery
from ..ui import InputHelpers


class CreateMysteryCommand(Command):
    def __init__(self, repo: MysteryRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Skapa ett nytt mysterium"

    def execute(self) -> None:
        name_val = self._ui.prompt("mysteriumnamn")
        mystery = self._repo.create(name_val)
        self._ui.display.success(f"MYSTERY '{mystery.name}' skapad")


class DeleteMysteryCommand(Command):
    def __init__(self, repo: MysteryRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Ta bort ett mysterium"

    def execute(self) -> None:
        mysteries = self._repo.list_all()
        selected = self._ui.select_from_list(mysteries, Mystery.display_str, "Alla mysterier")
        if not selected:
            return

        if self._ui.confirm(f"Ta bort MYSTERY '{selected.name}'?"):
            if self._repo.delete(selected.name):
                self._ui.display.success(f"MYSTERY '{selected.name}' borttagen")
            else:
                self._ui.display.error("Kunde inte ta bort mysteriet")


class ListMysteriesCommand(Command):
    def __init__(self, repo: MysteryRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Visa alla mysterier"

    def execute(self) -> None:
        mysteries = self._repo.list_all()
        if not mysteries:
            self._ui.display.error("Inga mysterier hittades")
            return
        self._ui.display.header("Alla mysterier")
        self._ui.display.list_items(mysteries, Mystery.display_str)


class LinkClaimToMysteryCommand(Command):
    def __init__(self, mystery_repo: MysteryRepo, claim_repo: ClaimRepo,
                 ui: InputHelpers) -> None:
        self._mystery_repo = mystery_repo
        self._claim_repo = claim_repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Koppla CLAIM till mysterium"

    def execute(self) -> None:
        mysteries = self._mystery_repo.list_all()
        mystery = self._ui.select_from_list(mysteries, Mystery.display_str, "Valj mysterium")
        if not mystery:
            return

        claims = self._claim_repo.list_all()
        claim = self._ui.select_from_list(claims, Claim.display_str, "Valj CLAIM")
        if not claim:
            return

        if self._mystery_repo.link_claim(claim.claim_id, mystery.name):
            self._ui.display.success(f"CLAIM {claim.claim_id} kopplad till '{mystery.name}'")
        else:
            self._ui.display.error("Kunde inte koppla claim till mysteriet")


class UnlinkClaimFromMysteryCommand(Command):
    def __init__(self, mystery_repo: MysteryRepo, claim_repo: ClaimRepo,
                 ui: InputHelpers) -> None:
        self._mystery_repo = mystery_repo
        self._claim_repo = claim_repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Ta bort CLAIM fran mysterium"

    def execute(self) -> None:
        mysteries = self._mystery_repo.list_all()
        mystery = self._ui.select_from_list(mysteries, Mystery.display_str, "Valj mysterium")
        if not mystery:
            return

        claims = self._mystery_repo.list_claims(mystery.name)
        if not claims:
            self._ui.display.error(f"Inga claims kopplade till '{mystery.name}'")
            return

        claim = self._ui.select_from_list(claims, Claim.display_str, "Valj CLAIM att ta bort")
        if not claim:
            return

        if self._mystery_repo.unlink_claim(claim.claim_id, mystery.name):
            self._ui.display.success(f"CLAIM {claim.claim_id} bortkopplad fran '{mystery.name}'")
        else:
            self._ui.display.error("Kunde inte ta bort kopplingen")


class ListClaimsByMysteryCommand(Command):
    def __init__(self, mystery_repo: MysteryRepo, ui: InputHelpers) -> None:
        self._mystery_repo = mystery_repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Visa claims per mysterium"

    def execute(self) -> None:
        mysteries = self._mystery_repo.list_all()
        mystery = self._ui.select_from_list(mysteries, Mystery.display_str, "Valj mysterium")
        if not mystery:
            return

        claims = self._mystery_repo.list_claims(mystery.name)
        if not claims:
            self._ui.display.error(f"Inga claims kopplade till '{mystery.name}'")
            return

        self._ui.display.header(f"Claims i '{mystery.name}'")
        self._ui.display.list_items(claims, Claim.display_str)
