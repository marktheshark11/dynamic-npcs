from datetime import datetime, timezone

from .base import BaseRepository


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationRepo(BaseRepository):
    def _next_conversation_id(self) -> str:
        records = self._run(
            "MATCH (c:CONVERSATION) "
            "WHERE c.conv_id IS NOT NULL AND c.conv_id STARTS WITH 'conv_' "
            "RETURN c.conv_id AS conv_id"
        )
        if not records:
            return "conv_1"

        max_num = 0
        for record in records:
            current_id = record.get("conv_id")
            if not current_id:
                continue
            suffix = current_id[5:]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))

        return f"conv_{max_num + 1}"

    def create_conversation(self, npc_id: str) -> str | None:
        conversation_id = self._next_conversation_id()
        record = self._run_single(
            "MATCH (npc:NPC {id: $npc_id}) "
            "CREATE (c:CONVERSATION {"
            "conv_id: $conversation_id, npc_id: $npc_id, created_at: $created_at"
            "}) "
            "CREATE (npc)-[:HAS_CONVERSATION]->(c) "
            "RETURN c.conv_id AS conv_id",
            npc_id=npc_id,
            conversation_id=conversation_id,
            created_at=_now_utc_iso(),
        )
        if not record:
            return None
        return record["conv_id"]

    def get_conversation(self, conversation_id: str) -> dict | None:
        record = self._run_single(
            "MATCH (c:CONVERSATION {conv_id: $conversation_id}) "
            "RETURN c.conv_id AS conv_id, c.npc_id AS npc_id, "
            "c.created_at AS created_at",
            conversation_id=conversation_id,
        )
        if not record:
            return None
        return {
            "conv_id": record["conv_id"],
            "npc_id": record["npc_id"],
            "created_at": record.get("created_at"),
            "ended_at": None,
        }

    def append_exchange(self, conversation_id: str, player_text: str, npc_text: str) -> str | None:
        conversation_exists = self._run_single(
            "MATCH (c:CONVERSATION {conv_id: $conversation_id}) RETURN c.conv_id AS conv_id",
            conversation_id=conversation_id,
        )
        if not conversation_exists:
            return None

        tail_record = self._run_single(
            "MATCH (c:CONVERSATION {conv_id: $conversation_id}) "
            "OPTIONAL MATCH (c)-[:FIRST_EXCHANGE]->(first:EXCHANGE) "
            "OPTIONAL MATCH (first)-[:NEXT*0..]->(last:EXCHANGE) "
            "WITH first, last "
            "ORDER BY last.turn_index DESC "
            "RETURN first IS NOT NULL AS has_first, last.exch_id AS tail_exch_id, "
            "coalesce(last.turn_index, 0) AS tail_turn_index "
            "LIMIT 1",
            conversation_id=conversation_id,
        )

        has_first = bool(tail_record["has_first"]) if tail_record else False
        tail_exch_id = tail_record.get("tail_exch_id") if tail_record else None
        turn_index = int(tail_record["tail_turn_index"]) + 1 if tail_record else 1

        exchange_id = f"{conversation_id}_ex_{turn_index}"
        now_iso = _now_utc_iso()

        if not has_first:
            self._run(
                "MATCH (c:CONVERSATION {conv_id: $conversation_id}) "
                "CREATE (e:EXCHANGE {"
                "exch_id: $exchange_id, turn_index: $turn_index, "
                "player_text: $player_text, npc_text: $npc_text, created_at: $created_at"
                "}) "
                "CREATE (c)-[:FIRST_EXCHANGE]->(e)",
                conversation_id=conversation_id,
                exchange_id=exchange_id,
                turn_index=turn_index,
                player_text=player_text,
                npc_text=npc_text,
                created_at=now_iso,
            )
            return exchange_id

        if not tail_exch_id:
            return None

        self._run(
            "MATCH (tail:EXCHANGE {exch_id: $tail_exch_id}) "
            "CREATE (e:EXCHANGE {"
            "exch_id: $exchange_id, turn_index: $turn_index, "
            "player_text: $player_text, npc_text: $npc_text, created_at: $created_at"
            "}) "
            "CREATE (tail)-[:NEXT]->(e)",
            tail_exch_id=tail_exch_id,
            exchange_id=exchange_id,
            turn_index=turn_index,
            player_text=player_text,
            npc_text=npc_text,
            created_at=now_iso,
        )
        return exchange_id

    def list_exchanges(self, conversation_id: str, limit: int | None = None) -> list[dict]:
        records = self._run(
            "MATCH (c:CONVERSATION {conv_id: $conversation_id})-[:FIRST_EXCHANGE]->(first:EXCHANGE) "
            "MATCH (first)-[:NEXT*0..]->(e:EXCHANGE) "
            "RETURN DISTINCT e.exch_id AS exch_id, e.turn_index AS turn_index, "
            "e.player_text AS player_text, e.npc_text AS npc_text, e.created_at AS created_at "
            "ORDER BY e.turn_index",
            conversation_id=conversation_id,
        )

        exchanges = [
            {
                "exch_id": r["exch_id"],
                "turn_index": r["turn_index"],
                "player_text": r.get("player_text"),
                "npc_text": r.get("npc_text"),
                "created_at": r.get("created_at"),
            }
            for r in records
        ]
        if limit is not None and limit > 0:
            return exchanges[-limit:]
        return exchanges

    def list_conversations(self) -> list[dict]:
        records = self._run(
            "MATCH (npc:NPC)-[:HAS_CONVERSATION]->(c:CONVERSATION) "
            "OPTIONAL MATCH (c)-[:FIRST_EXCHANGE]->(first:EXCHANGE) "
            "OPTIONAL MATCH (first)-[:NEXT*0..]->(e:EXCHANGE) "
            "RETURN c.conv_id AS conv_id, c.npc_id AS npc_id, c.created_at AS created_at, "
            "count(DISTINCT e) AS exchange_count "
            "ORDER BY c.created_at DESC"
        )
        return [
            {
                "conv_id": r["conv_id"],
                "npc_id": r["npc_id"],
                "created_at": r.get("created_at"),
                "exchange_count": r.get("exchange_count", 0),
            }
            for r in records
        ]

    def delete_conversation(self, conversation_id: str) -> bool:
        record = self._run_single(
            "MATCH (c:CONVERSATION {conv_id: $conversation_id}) "
            "RETURN c.conv_id AS conv_id",
            conversation_id=conversation_id,
        )
        if not record:
            return False

        self._run(
            "MATCH (c:CONVERSATION {conv_id: $conversation_id}) "
            "OPTIONAL MATCH (c)-[:FIRST_EXCHANGE]->(first:EXCHANGE) "
            "OPTIONAL MATCH (first)-[:NEXT*0..]->(e:EXCHANGE) "
            "WITH collect(DISTINCT e) AS exchanges "
            "UNWIND exchanges AS ex "
            "DETACH DELETE ex",
            conversation_id=conversation_id,
        )
        self._run(
            "MATCH (c:CONVERSATION {conv_id: $conversation_id}) "
            "DETACH DELETE c",
            conversation_id=conversation_id,
        )
        return True

    def delete_all_conversations(self) -> int:
        record = self._run_single(
            "MATCH (c:CONVERSATION) "
            "RETURN count(c) AS cnt"
        )
        if not record:
            return 0

        count = int(record.get("cnt") or 0)
        if count == 0:
            return 0

        self._run("MATCH (e:EXCHANGE) DETACH DELETE e")
        self._run("MATCH (c:CONVERSATION) DETACH DELETE c")
        return count
