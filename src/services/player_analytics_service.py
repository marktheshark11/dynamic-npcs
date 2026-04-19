from collections import Counter
from datetime import datetime, timezone
from copy import deepcopy
from typing import Any

from db.repositories import ConversationRepo, FormRepo, PlayerRepo, UserRepo


class PlayerAnalyticsService:
    def __init__(self, driver):
        self.player_repo = PlayerRepo(driver)
        self.conversation_repo = ConversationRepo(driver)
        self.form_repo = FormRepo(driver)
        self.user_repo = UserRepo(driver)

    @staticmethod
    def _exported_at() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _stringify(value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        return str(value)

    @classmethod
    def _normalize_conversation(cls, conversation: dict) -> dict:
        return {
            "conversation_id": conversation.get("conv_id"),
            "npc_id": conversation.get("npc_id"),
            "player_id": conversation.get("player_id"),
            "created_at": cls._stringify(conversation.get("created_at")),
            "ended_at": cls._stringify(conversation.get("ended_at")),
            "summary": conversation.get("summary"),
            "summary_updated_at": cls._stringify(conversation.get("summary_updated_at")),
            "exchange_count": int(conversation.get("exchange_count") or 0),
        }

    @classmethod
    def _make_event(
        cls,
        event_type: str,
        timestamp: Any,
        payload: dict | None = None,
        sort_key: str | None = None,
    ) -> dict:
        return {
            "type": event_type,
            "timestamp": cls._stringify(timestamp),
            "sort_key": sort_key or cls._stringify(timestamp) or "",
            "payload": payload or {},
        }

    @staticmethod
    def _summary_without_user(summary: dict) -> dict:
        normalized_summary = deepcopy(summary)
        normalized_summary.pop("user", None)
        return normalized_summary

    def get_player_summary(self, player_id: str) -> dict | None:
        profile = self.player_repo.get_profile_by_id(player_id)
        if not profile:
            return None

        user = self.user_repo.get_public_by_player_id(player_id)
        locale = (user or {}).get("locale") or self.user_repo.get_locale_by_player_id(player_id)
        clues = self.player_repo.get_clues(player_id, locale=locale)
        conversations = self.conversation_repo.list_for_player(player_id)
        forms = self.form_repo.list_player_forms_with_answers(player_id, locale=locale)

        normalized_conversations = [self._normalize_conversation(conversation) for conversation in conversations]
        npc_counter = Counter(
            conversation["npc_id"] for conversation in normalized_conversations if conversation.get("npc_id")
        )
        total_exchanges = sum(conversation["exchange_count"] for conversation in normalized_conversations)

        created_at = profile.get("created_at")
        completed_at = profile.get("completed_at")
        progress = {
            "claims_known": len(clues.get("claims", [])),
            "items_seen": sum(1 for item in clues.get("items", []) if item.get("seen")),
            "items_picked_up": sum(1 for item in clues.get("items", []) if item.get("picked_up")),
            "doors_seen": sum(1 for door in clues.get("doors", []) if door.get("seen")),
            "doors_opened": sum(1 for door in clues.get("doors", []) if door.get("opened")),
            "forms_answered": len(forms),
            "conversation_count": len(normalized_conversations),
            "exchange_count": total_exchanges,
            "unique_npcs_spoken_to": len(npc_counter),
        }

        return {
            "player_id": player_id,
            "locale": locale,
            "user": user,
            "profile": {
                "name": profile.get("name"),
                "appearance": profile.get("appearance"),
                "created_at": created_at,
                "completed_at": completed_at,
            },
            "game": {
                "has_completed_game": bool(profile.get("has_completed_game")),
                "accused_correct_npc": profile.get("accused_correct_npc"),
                "accused_npc_id": profile.get("accused_npc_id"),
            },
            "progress": progress,
            "clues": clues,
            "forms": forms,
            "conversation_metrics": {
                "by_npc": [
                    {"npc_id": npc_id, "conversation_count": count}
                    for npc_id, count in sorted(npc_counter.items())
                ],
                "conversations": normalized_conversations,
            },
        }

    def get_player_timeline(self, player_id: str) -> dict | None:
        profile = self.player_repo.get_profile_by_id(player_id)
        if not profile:
            return None

        locale = self.user_repo.get_locale_by_player_id(player_id)
        events: list[dict] = []

        if profile.get("created_at"):
            events.append(
                self._make_event(
                    "player_created",
                    profile.get("created_at"),
                    payload={"player_id": player_id},
                )
            )

        for claim in self.player_repo.get_aware_claims(player_id, locale=locale):
            events.append(
                self._make_event(
                    "claim_learned",
                    claim.get("created_at"),
                    payload={
                        "claim_id": claim.get("claim_id"),
                        "content": claim.get("content"),
                        "type": claim.get("type"),
                        "important": bool(claim.get("important")),
                        "npc_ids": claim.get("npc_ids") or [],
                    },
                    sort_key=f"{claim.get('created_at') or ''}|claim|{claim.get('claim_id') or ''}",
                )
            )

        for item in self.player_repo.get_seen_items(player_id, locale=locale):
            events.append(
                self._make_event(
                    "item_seen",
                    item.get("created_at"),
                    payload={
                        "object_id": item.get("object_id"),
                        "name": item.get("name"),
                        "pickupable": bool(item.get("pickupable")),
                    },
                    sort_key=f"{item.get('created_at') or ''}|item_seen|{item.get('object_id') or ''}",
                )
            )

        for item in self.player_repo.get_picked_up_items(player_id, locale=locale):
            events.append(
                self._make_event(
                    "item_picked_up",
                    item.get("created_at"),
                    payload={
                        "object_id": item.get("object_id"),
                        "name": item.get("name"),
                    },
                    sort_key=f"{item.get('created_at') or ''}|item_picked|{item.get('object_id') or ''}",
                )
            )

        for door in self.player_repo.get_seen_doors(player_id, locale=locale):
            events.append(
                self._make_event(
                    "door_seen",
                    door.get("created_at"),
                    payload={
                        "object_id": door.get("object_id"),
                        "name": door.get("name"),
                        "lock_type": door.get("lock_type"),
                    },
                    sort_key=f"{door.get('created_at') or ''}|door_seen|{door.get('object_id') or ''}",
                )
            )

        for door in self.player_repo.get_opened_doors(player_id, locale=locale):
            events.append(
                self._make_event(
                    "door_opened",
                    door.get("created_at"),
                    payload={
                        "object_id": door.get("object_id"),
                        "name": door.get("name"),
                        "lock_type": door.get("lock_type"),
                    },
                    sort_key=f"{door.get('created_at') or ''}|door_opened|{door.get('object_id') or ''}",
                )
            )

        for door_entry in self.player_repo.get_door_entries(player_id, locale=locale):
            events.append(
                self._make_event(
                    "door_entered",
                    door_entry.get("created_at"),
                    payload={
                        "object_id": door_entry.get("object_id"),
                        "name": door_entry.get("name"),
                    },
                    sort_key=f"{door_entry.get('created_at') or ''}|door_entered|{door_entry.get('object_id') or ''}",
                )
            )

        for conversation in self.conversation_repo.list_for_player(player_id):
            normalized_conversation = self._normalize_conversation(conversation)
            conversation_id = normalized_conversation["conversation_id"]
            events.append(
                self._make_event(
                    "conversation_started",
                    normalized_conversation.get("created_at"),
                    payload={
                        "conversation_id": conversation_id,
                        "npc_id": normalized_conversation.get("npc_id"),
                    },
                    sort_key=(
                        f"{normalized_conversation.get('created_at') or ''}|conversation|"
                        f"{conversation_id or ''}"
                    ),
                )
            )

            for exchange in self.conversation_repo.list_exchanges(conversation_id):
                events.append(
                    self._make_event(
                        "exchange_recorded",
                        exchange.get("created_at"),
                        payload={
                            "conversation_id": conversation_id,
                            "exchange_id": exchange.get("exch_id"),
                            "npc_id": normalized_conversation.get("npc_id"),
                            "turn_index": exchange.get("turn_index"),
                            "player_text": exchange.get("player_text"),
                            "npc_text": exchange.get("npc_text"),
                        },
                        sort_key=(
                            f"{exchange.get('created_at') or ''}|exchange|{conversation_id or ''}|"
                            f"{exchange.get('turn_index') or 0:04d}"
                        ),
                    )
                )

        for form in self.form_repo.list_player_forms_with_answers(player_id, locale=locale):
            for answer in form.get("answers", []):
                events.append(
                    self._make_event(
                        "form_answer_saved",
                        None,
                        payload={
                            "form_id": form.get("form_id"),
                            "form_name": form.get("name"),
                            "question_id": answer.get("question_id"),
                            "question": answer.get("question"),
                            "raw_answer": answer.get("raw_answer"),
                            "answer_text": answer.get("answer_text"),
                            "answer_int": answer.get("answer_int"),
                            "answer_bool": answer.get("answer_bool"),
                        },
                        sort_key=f"zzzz|form|{form.get('form_id') or ''}|{answer.get('order') or 0:04d}",
                    )
                )

        if profile.get("completed_at"):
            events.append(
                self._make_event(
                    "game_completed",
                    profile.get("completed_at"),
                    payload={
                        "accused_npc_id": profile.get("accused_npc_id"),
                        "accused_correct_npc": profile.get("accused_correct_npc"),
                    },
                    sort_key=f"{profile.get('completed_at') or ''}|game_completed",
                )
            )

        events.sort(key=lambda event: event.get("sort_key") or "")
        normalized_events = [
            {
                "type": event["type"],
                "timestamp": event["timestamp"],
                "payload": event["payload"],
            }
            for event in events
        ]

        return {
            "player_id": player_id,
            "locale": locale,
            "event_count": len(normalized_events),
            "events": normalized_events,
        }

    def export_player_analytics(self, player_id: str) -> dict | None:
        summary = self.get_player_summary(player_id)
        if not summary:
            return None
        timeline = self.get_player_timeline(player_id)
        return {
            "exported_at": self._exported_at(),
            "user": summary.get("user"),
            "player_id": player_id,
            "summary": self._summary_without_user(summary),
            "timeline": timeline,
        }

    def export_players(self, player_ids: list[str] | None = None) -> dict:
        resolved_player_ids = player_ids or self.player_repo.list_all_ids()
        users_by_id: dict[str, dict] = {}
        for player_id in resolved_player_ids:
            export = self.export_player_analytics(player_id)
            if not export:
                continue

            user = export.get("user") or {"user_id": None, "username": None, "locale": None}
            user_id = user.get("user_id") or "__unowned__"
            user_entry = users_by_id.setdefault(
                user_id,
                {
                    "user": user,
                    "players": [],
                },
            )
            user_entry["players"].append(
                {
                    "player_id": export["player_id"],
                    "summary": export["summary"],
                    "timeline": export["timeline"],
                }
            )

        users = []
        for user_id in sorted(users_by_id.keys()):
            user_entry = users_by_id[user_id]
            players = sorted(user_entry["players"], key=lambda player: player["player_id"])
            users.append(
                {
                    "user": user_entry["user"],
                    "player_count": len(players),
                    "players": players,
                }
            )

        return {
            "exported_at": self._exported_at(),
            "user_count": len(users),
            "users": users,
        }

    def export_players_for_user(self, user_id: str) -> dict:
        player_ids = [player.player_id for player in self.player_repo.list_by_user(user_id)]
        return self.export_players(player_ids=player_ids)
