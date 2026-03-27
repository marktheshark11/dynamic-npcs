from collections.abc import Callable
from dataclasses import dataclass, field

from db.repositories import PlayerRepo


@dataclass(frozen=True)
class PlayerStateSnapshot:
    aware_claim_ids: set[str]
    seen_object_ids: set[str]
    inventory_item_ids: set[str]
    seen_door_ids: set[str]
    opened_door_ids: set[str]

    def knows_claim(self, claim_id: str) -> bool:
        return claim_id in self.aware_claim_ids

    def has_seen_object(self, object_id: str) -> bool:
        return object_id in self.seen_object_ids

    def has_item(self, object_id: str) -> bool:
        return object_id in self.inventory_item_ids

    def has_seen_door(self, object_id: str) -> bool:
        return object_id in self.seen_door_ids

    def has_opened_door(self, object_id: str) -> bool:
        return object_id in self.opened_door_ids


@dataclass(frozen=True)
class HintCheck:
    required_claim_ids: set[str] = field(default_factory=set)
    excluded_claim_ids: set[str] = field(default_factory=set)
    required_seen_object_ids: set[str] = field(default_factory=set)
    excluded_seen_object_ids: set[str] = field(default_factory=set)
    required_item_ids: set[str] = field(default_factory=set)
    excluded_item_ids: set[str] = field(default_factory=set)
    required_seen_door_ids: set[str] = field(default_factory=set)
    excluded_seen_door_ids: set[str] = field(default_factory=set)
    required_opened_door_ids: set[str] = field(default_factory=set)
    excluded_opened_door_ids: set[str] = field(default_factory=set)


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
                text="Gå och undersök kroppen. Den finns i huvudsovrummet. Det är det sista rummet till höger på övervåning.",
                matcher=lambda state: not state.has_seen_object("object_body"),
            ),
            HintRule(
                text="Du borde tala med Wilhelm, sonen till den avlidne. Han är i sitt rum, det första rummet till vänster på övervåningen. Han verkar ha hört någonting, undersök var ljudet kom ifrån.",
                matcher=lambda state: state.has_seen_object("object_body") and not state.knows_claim("C79"),
            ),
            HintRule(
                text="Wilhelm sa att han hörde ett ljud från arbetsrummet. Det kan vara värt att undersöka det rummet lite mer noggrant.",
                matcher=lambda state: state.knows_claim("C79") and not state.has_seen_door("door_study"),
            ),
            HintRule(
                text="Det verkar som att du behöver en nyckel för att kunna komma in i arbetsrummet. Fråga runt efter den.",
                matcher=lambda state: state.has_seen_door("door_study") and not state.has_opened_door("door_study"),
            ),
            HintRule(
                text="Du behöver en 4-siffrig kod för att komma in i kassaskåpet. Se om du kan lista ut vad den kan vara.",
                matcher=lambda state: state.has_seen_door("object_safe") and not state.has_opened_door("object_safe"),
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
            seen_door_ids=self.player_repo.get_seen_door_ids(player_id),
            opened_door_ids=self.player_repo.get_opened_door_ids(player_id),
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
        if not check.required_seen_door_ids.issubset(state.seen_door_ids):
            return False
        if check.excluded_seen_door_ids.intersection(state.seen_door_ids):
            return False
        if not check.required_opened_door_ids.issubset(state.opened_door_ids):
            return False
        if check.excluded_opened_door_ids.intersection(state.opened_door_ids):
            return False
        return True
