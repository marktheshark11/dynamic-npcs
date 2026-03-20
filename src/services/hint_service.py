from collections.abc import Callable
from dataclasses import dataclass, field

from db.repositories import PlayerRepo


@dataclass(frozen=True)
class PlayerStateSnapshot:
    aware_claim_ids: set[str]
    seen_object_ids: set[str]
    inventory_item_ids: set[str]

    def knows_claim(self, claim_id: str) -> bool:
        return claim_id in self.aware_claim_ids

    def has_seen_object(self, object_id: str) -> bool:
        return object_id in self.seen_object_ids

    def has_item(self, object_id: str) -> bool:
        return object_id in self.inventory_item_ids


@dataclass(frozen=True)
class HintCheck:
    required_claim_ids: set[str] = field(default_factory=set)
    excluded_claim_ids: set[str] = field(default_factory=set)
    required_seen_object_ids: set[str] = field(default_factory=set)
    excluded_seen_object_ids: set[str] = field(default_factory=set)
    required_item_ids: set[str] = field(default_factory=set)
    excluded_item_ids: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class HintRule:
    text: str
    check: HintCheck | None = None
    matcher: Callable[[PlayerStateSnapshot], bool] | None = None


class HintService:
    def __init__(self, driver):
        self.player_repo = PlayerRepo(driver)
        self._text_rules: list[HintRule] = [
            HintRule(
                text="Du borde se det här tills du lärt dig att Wolmars slott används idag som sommarhus av Nils och Pamela [C3] (fråga Herr Bergström)",
                matcher=lambda state: not state.knows_claim("C3"),
            ),
            HintRule(
                text="Test2",
                check=HintCheck(
                    required_seen_object_ids={"item_brev"},
                    excluded_item_ids={"item_brev"},
                ),
            ),
            HintRule(
                text="Test3",
                check=HintCheck(
                    required_item_ids={"item_brev"},
                ),
            ),
        ]

    def get_hint_text(self, player_id: str) -> str:
        player_profile = self.player_repo.get_profile_by_id(player_id)
        if not player_profile:
            raise ValueError("Kunde inte hämta hint: spelaren hittades inte.")

        state = self._build_player_state(player_id)
        lines = self._collect_matching_texts(state)
        if not lines:
            return (
                "Kommissarien skakar på huvudet. 'Du har inget tillräckligt konkret ännu. "
                "Undersök fler föremål och prata med fler personer först.'"
            )

        return "\n".join(lines)

    def has_hint(
        self,
        player_id: str,
        check: HintCheck | None = None,
        matcher: Callable[[PlayerStateSnapshot], bool] | None = None,
    ) -> bool:
        player_profile = self.player_repo.get_profile_by_id(player_id)
        if not player_profile:
            raise ValueError("Kunde inte kontrollera hintar: spelaren hittades inte.")

        state = self._build_player_state(player_id)
        return self._matches_rule(state, check=check, matcher=matcher)

    def _build_player_state(self, player_id: str) -> PlayerStateSnapshot:
        return PlayerStateSnapshot(
            aware_claim_ids=self.player_repo.get_aware_claim_ids(player_id),
            seen_object_ids=self.player_repo.get_seen_object_ids(player_id),
            inventory_item_ids=self.player_repo.get_inventory_item_ids(player_id),
        )

    def _collect_matching_texts(self, state: PlayerStateSnapshot) -> list[str]:
        lines: list[str] = []
        for rule in self._text_rules:
            if self._matches_rule(state, check=rule.check, matcher=rule.matcher):
                lines.append(rule.text)
        return lines

    @classmethod
    def _matches_rule(
        cls,
        state: PlayerStateSnapshot,
        check: HintCheck | None = None,
        matcher: Callable[[PlayerStateSnapshot], bool] | None = None,
    ) -> bool:
        if matcher is not None:
            return matcher(state)
        if check is None:
            return False
        return cls._matches_check(state, check)

    @staticmethod
    def _matches_check(state: PlayerStateSnapshot, check: HintCheck) -> bool:
        if not check.required_claim_ids.issubset(state.aware_claim_ids):
            return False
        if check.excluded_claim_ids.intersection(state.aware_claim_ids):
            return False
        if not check.required_seen_object_ids.issubset(state.seen_object_ids):
            return False
        if check.excluded_seen_object_ids.intersection(state.seen_object_ids):
            return False
        if not check.required_item_ids.issubset(state.inventory_item_ids):
            return False
        if check.excluded_item_ids.intersection(state.inventory_item_ids):
            return False
        return True
