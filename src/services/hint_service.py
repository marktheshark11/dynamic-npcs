from collections.abc import Callable
from dataclasses import dataclass, field

from db.repositories import PlayerRepo, UserRepo


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
    text_en: str | None = None
    check: HintCheck | None = None
    matcher: Callable[[PlayerStateSnapshot], bool] | None = None


class HintService:
    def __init__(self, driver):
        self.player_repo = PlayerRepo(driver)
        self.user_repo = UserRepo(driver)
        self._text_rules: list[HintRule] = [
            HintRule(
                text="Gå och undersök kroppen i huvudsovrummet. Det är det sista rummet till höger på övervåningen."
                text_en="Go and examine the body in the master bedroom. It is the last room to the right upstairs.",
                matcher=lambda state: not state.has_seen_object("object_body"),
            ),
            HintRule(
                text="Du bör även tala med Wilhelm, den avlidnes son. Han befinner sig i sitt sovrum, den första dörren till vänster på övervåningen. Han verkar ha hört någonting under kvällen undersök var ljudet kom ifrån.",
                text_en="You should also talk to Wilhelm, the son of the deceased. He is in his bedroom, the first door to the left upstairs. He seems to have heard something during the evening, investigate where the sound came from.",
                matcher=lambda state: not state.has_seen_object("object_body")
            ),
            HintRule(
                text="Wilhelm sa att han hörde ett ljud från arbetsrummet. Det kan vara värt att undersöka det rummet lite mer noggrant.",
                text_en="Wilhelm said that he heard a sound from the study. It may be worth investigating that room more carefully.",
                matcher=lambda state: state.knows_claim("C79") and not state.has_seen_door("door_study"),
            ),
            HintRule(
                text="Det verkar som att du behöver en nyckel för att kunna komma in i arbetsrummet. Fråga runt efter den.",
                text_en="It seems that you need a key to get into the study. Ask around about it.",
                matcher=lambda state: state.has_seen_door("door_study") and not state.has_opened_door("door_study"),
            ),
            HintRule(
                text="Du behöver en 4-siffrig kod för att komma in i kassaskåpet i arbetsrummet. Se om du kan lista ut vad den kan vara genom att prata med karaktärerna.",
                text_en="You need a 4-digit code to open the safe in the study. See if you can figure out what it might be by talking to the characters.",
                matcher=lambda state: state.has_opened_door("door_study") and not state.has_opened_door("object_safe"),
            ), 
            HintRule(
                text="Du hittade ett brev i kassaskåpet som nämner viktig information angående Beatrice. Det kan vara en bra idé att prata med henne om det.",
                text_en="You found a letter in the safe that mentions important information regarding Beatrice. It might be a good idea to talk to her about it.",
                matcher=lambda state: state.has_seen_object("object_letter"),
            )
        ]

    @staticmethod
    def _is_english(locale: str | None) -> bool:
        return (locale or "sv").strip().lower() == "en"

    def get_hint_text(self, player_id: str) -> str:
        player_profile = self.player_repo.get_profile_by_id(player_id)
        locale = self.user_repo.get_locale_by_player_id(player_id)
        if not player_profile:
            raise ValueError("Could not fetch hint: player not found." if self._is_english(locale) else "Kunde inte hämta hint: spelaren hittades inte.")

        state = self._build_player_state(player_id)
        lines = self._collect_matching_texts(state, locale)
        if not lines:
            if self._is_english(locale):
                return (
                    "The commissioner shakes his head. 'You do not have anything concrete enough yet. "
                    "Examine more objects and talk to more people first.'"
                )
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
        locale = self.user_repo.get_locale_by_player_id(player_id)
        if not player_profile:
            raise ValueError("Could not check hints: player not found." if self._is_english(locale) else "Kunde inte kontrollera hintar: spelaren hittades inte.")

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

    def _collect_matching_texts(self, state: PlayerStateSnapshot, locale: str) -> list[str]:
        lines: list[str] = []
        is_english = self._is_english(locale)
        for rule in self._text_rules:
            if self._matches_rule(state, check=rule.check, matcher=rule.matcher):
                lines.append(rule.text_en if is_english else rule.text)
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
