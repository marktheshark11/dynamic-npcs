from .base import BaseRepository
from ..models import Item, Player
from .user_repo import ADMIN_USER_ID


class PlayerRepo(BaseRepository):
    """CRUD operations for PLAYER nodes."""

    @staticmethod
    def _created_at_sort_key(item: dict, id_key: str) -> tuple[bool, str, str]:
        created_at = item.get("created_at") or ""
        return item.get("created_at") is None, created_at, item.get(id_key, "")

    def _next_player_id(self) -> str:
        record = self._run_single(
            "MATCH (p:PLAYER) "
            "WITH CASE "
            "WHEN p.player_id STARTS WITH 'player_' THEN toInteger(split(p.player_id, '_')[1]) "
            "WHEN p.player_id STARTS WITH 'p_' THEN toInteger(split(p.player_id, '_')[1]) "
            "ELSE NULL "
            "END AS numeric_id "
            "RETURN coalesce(max(numeric_id), 0) + 1 AS next_id"
        )
        next_id = 1 if not record else record["next_id"]
        return f"player_{next_id}"

    def create(self, name: str, appearance: str, user_id: str | None = None) -> Player:
        player_id = self._next_player_id()
        # Use admin user as fallback if no user_id provided
        actual_user_id = user_id or ADMIN_USER_ID
        self._run(
            "MATCH (u:USER {user_id: $user_id}) "
            "CREATE (p:PLAYER {player_id: $player_id, name: $name, appearance: $appearance}) "
            "CREATE (u)-[:HAS_CHARACTER]->(p)",
            player_id=player_id,
            name=name,
            appearance=appearance,
            user_id=actual_user_id,
        )
        return Player(player_id=player_id, name=name, appearance=appearance)

    def get_profile_by_id(self, player_id: str) -> dict | None:
        record = self._run_single(
            "MATCH (p:PLAYER {player_id: $player_id}) "
            "RETURN p.name AS name, p.appearance AS appearance "
            "LIMIT 1",
            player_id=player_id,
        )
        if not record:
            return None
        return {
            "name": record["name"],
            "appearance": record.get("appearance"),
        }

    def list_all(self) -> list[Player]:
        records = self._run(
            "MATCH (p:PLAYER) "
            "RETURN p.player_id AS player_id, p.name AS name, p.appearance AS appearance "
            "ORDER BY p.player_id"
        )
        return [
            Player(
                player_id=r["player_id"],
                name=r["name"],
                appearance=r["appearance"],
            )
            for r in records
        ]

    def list_by_user(self, user_id: str) -> list[Player]:
        """List all players owned by a user."""
        records = self._run(
            "MATCH (u:USER {user_id: $user_id})-[:HAS_CHARACTER]->(p:PLAYER) "
            "RETURN p.player_id AS player_id, p.name AS name, p.appearance AS appearance "
            "ORDER BY p.player_id",
            user_id=user_id,
        )
        return [
            Player(
                player_id=r["player_id"],
                name=r["name"],
                appearance=r["appearance"],
            )
            for r in records
        ]

    def set_user(self, player_id: str, user_id: str | None = None) -> bool:
        """Assign a player to a user with HAS_CHARACTER relationship. Uses admin as fallback if user_id is None."""
        actual_user_id = user_id or ADMIN_USER_ID
        record = self._run_single(
            "MATCH (u:USER {user_id: $user_id}) "
            "MATCH (p:PLAYER {player_id: $player_id}) "
            "MERGE (u)-[:HAS_CHARACTER]->(p) "
            "RETURN p.player_id AS player_id",
            user_id=actual_user_id,
            player_id=player_id,
        )
        return record is not None

    def update(self, player_id: str, name: str | None = None, appearance: str | None = None) -> bool:
        set_clauses = []
        params: dict[str, str] = {"player_id": player_id}

        if name is not None:
            set_clauses.append("p.name = $name")
            params["name"] = name

        if appearance is not None:
            set_clauses.append("p.appearance = $appearance")
            params["appearance"] = appearance

        if not set_clauses:
            return False

        query = f"MATCH (p:PLAYER {{player_id: $player_id}}) SET {', '.join(set_clauses)} RETURN p"
        record = self._run_single(query, **params)
        return record is not None

    def mark_aware_of(self, player_id: str, claim_ids: list[str], npc_id: str | None = None) -> int:
        """
        Drag AWARE_OF-pilar från spelaren till varje claim i listan.
        Skapar bara pilen om den inte redan finns (MERGE).
        Spårar vilka NPCs som nämnt claimet via npc_ids-listan på kanten.
        Returnerar antalet pilar som faktiskt skapades.
        """
        if not claim_ids:
            return 0
        record = self._run_single(
            """
            MATCH (p:PLAYER {player_id: $player_id})
            UNWIND $claim_ids AS cid
            MATCH (c:CLAIM {claim_id: cid})
            MERGE (p)-[r:AWARE_OF]->(c)
            ON CREATE SET
              r.created_at = datetime(),
              r.npc_ids = CASE WHEN $npc_id IS NOT NULL THEN [$npc_id] ELSE [] END
            ON MATCH SET
              r.npc_ids = CASE
                WHEN $npc_id IS NULL THEN coalesce(r.npc_ids, [])
                WHEN $npc_id IN coalesce(r.npc_ids, []) THEN r.npc_ids
                ELSE coalesce(r.npc_ids, []) + $npc_id
              END
            RETURN count(r) AS total
            """,
            player_id=player_id,
            claim_ids=claim_ids,
            npc_id=npc_id,
        )
        return record["total"] if record else 0

    def clear_aware_of(self, player_id: str) -> int:
        """Tar bort alla AWARE_OF-pilar för en specifik spelare. Returnerar antal borttagna."""
        record = self._run_single(
            """
            MATCH (p:PLAYER {player_id: $player_id})-[r:AWARE_OF]->()
            WITH count(r) AS total
            MATCH (p2:PLAYER {player_id: $player_id})-[r2:AWARE_OF]->()
            DELETE r2
            RETURN total
            """,
            player_id=player_id,
        )
        return record["total"] if record else 0

    def clear_aware_of_all(self) -> int:
        """Tar bort alla AWARE_OF-pilar i hela grafen. Returnerar antal borttagna."""
        record = self._run_single(
            """
            MATCH ()-[r:AWARE_OF]->()
            WITH count(r) AS total
            MATCH ()-[r2:AWARE_OF]->()
            DELETE r2
            RETURN total
            """,
        )
        return record["total"] if record else 0

    def get_aware_claims(self, player_id: str) -> list[dict]:
        """Returnerar alla claims som spelaren känner till via AWARE_OF."""
        records = self._run(
            """
            MATCH (p:PLAYER {player_id: $player_id})-[r:AWARE_OF]->(c:CLAIM)
            RETURN c.claim_id AS claim_id, c.content AS content, c.type AS type,
                   r.created_at AS created_at, r.npc_ids AS npc_ids
            ORDER BY c.claim_id
            """,
            player_id=player_id,
        )
        return [
            {
                "claim_id": r["claim_id"],
                "content": r["content"],
                "type": r.get("type"),
                "created_at": str(r["created_at"]) if r.get("created_at") else None,
                "npc_ids": list(r.get("npc_ids") or []),
            }
            for r in records
        ]

    def get_aware_claim_ids_from_npc(self, player_id: str, npc_id: str) -> set[str]:
        """Returnerar claim_ids som spelaren redan fått av en specifik NPC."""
        records = self._run(
            """
            MATCH (p:PLAYER {player_id: $player_id})-[r:AWARE_OF]->(c:CLAIM)
            WHERE $npc_id IN coalesce(r.npc_ids, [])
            RETURN c.claim_id AS claim_id
            """,
            player_id=player_id,
            npc_id=npc_id,
        )
        return {r["claim_id"] for r in records if r.get("claim_id")}

    def get_aware_claim_ids(self, player_id: str) -> set[str]:
        records = self._run(
            """
            MATCH (:PLAYER {player_id: $player_id})-[:AWARE_OF]->(c:CLAIM)
            RETURN c.claim_id AS claim_id
            """,
            player_id=player_id,
        )
        return {r["claim_id"] for r in records if r.get("claim_id")}

    def get_seen_object_ids(self, player_id: str) -> set[str]:
        records = self._run(
            """
            MATCH (:PLAYER {player_id: $player_id})-[:SEEN_OBJECT]->(o:OBJECT:ITEM)
            RETURN o.object_id AS object_id
            """,
            player_id=player_id,
        )
        return {r["object_id"] for r in records if r.get("object_id")}

    def get_inventory_item_ids(self, player_id: str) -> set[str]:
        records = self._run(
            """
            MATCH (:PLAYER {player_id: $player_id})-[:HAS_ITEM]->(o:OBJECT:ITEM)
            RETURN o.object_id AS object_id
            """,
            player_id=player_id,
        )
        return {r["object_id"] for r in records if r.get("object_id")}

    def has_item(self, player_id: str, object_id: str) -> bool:
        record = self._run_single(
            "MATCH (:PLAYER {player_id: $player_id})-[:HAS_ITEM]->(:OBJECT:ITEM {object_id: $object_id}) "
            "RETURN $object_id AS object_id LIMIT 1",
            player_id=player_id,
            object_id=object_id,
        )
        return record is not None

    def has_opened_door(self, player_id: str, object_id: str) -> bool:
        record = self._run_single(
            "MATCH (:PLAYER {player_id: $player_id})-[:HAS_OPENED]->(:OBJECT:DOOR {object_id: $object_id}) "
            "RETURN $object_id AS object_id LIMIT 1",
            player_id=player_id,
            object_id=object_id,
        )
        return record is not None

    def mark_seen_door(self, player_id: str, object_id: str) -> bool:
        record = self._run_single(
            "MATCH (p:PLAYER {player_id: $player_id}) "
            "MATCH (d:OBJECT:DOOR {object_id: $object_id}) "
            "MERGE (p)-[r:SEEN_DOOR]->(d) "
            "ON CREATE SET r.created_at = datetime() "
            "RETURN d.object_id AS object_id",
            player_id=player_id,
            object_id=object_id,
        )
        return record is not None

    def mark_opened_door(self, player_id: str, object_id: str) -> bool:
        record = self._run_single(
            "MATCH (p:PLAYER {player_id: $player_id}) "
            "MATCH (d:OBJECT:DOOR {object_id: $object_id}) "
            "MERGE (p)-[r:HAS_OPENED]->(d) "
            "ON CREATE SET r.created_at = datetime() "
            "RETURN d.object_id AS object_id",
            player_id=player_id,
            object_id=object_id,
        )
        return record is not None

    def mark_seen_object(self, player_id: str, object_id: str) -> bool:
        record = self._run_single(
            "MATCH (p:PLAYER {player_id: $player_id}) "
            "MATCH (o:OBJECT:ITEM {object_id: $object_id}) "
            "MERGE (p)-[r:SEEN_OBJECT]->(o) "
            "ON CREATE SET r.created_at = datetime() "
            "RETURN o.object_id AS object_id",
            player_id=player_id,
            object_id=object_id,
        )
        return record is not None

    def pickup_item(self, player_id: str, object_id: str) -> tuple[bool, str]:
        record = self._run_single(
            "MATCH (p:PLAYER {player_id: $player_id}) "
            "MATCH (o:OBJECT:ITEM {object_id: $object_id}) "
            "WITH p, o, coalesce(o.pickupable, false) AS pickupable "
            "FOREACH (_ IN CASE WHEN pickupable THEN [1] ELSE [] END | "
            "    MERGE (p)-[has:HAS_ITEM]->(o) "
            "    ON CREATE SET has.created_at = datetime() "
            "    MERGE (p)-[seen:SEEN_OBJECT]->(o) "
            "    ON CREATE SET seen.created_at = datetime()"
            ") "
            "RETURN pickupable AS pickupable",
            player_id=player_id,
            object_id=object_id,
        )
        if not record:
            return False, "Item eller player hittades inte"
        if not record["pickupable"]:
            return False, "Det itemet kan inte plockas upp"
        return True, "Item upplockat"

    def list_inventory(self, player_id: str) -> list[Item]:
        records = self._run(
            "MATCH (:PLAYER {player_id: $player_id})-[:HAS_ITEM]->(o:OBJECT:ITEM) "
            "RETURN o.object_id AS object_id, o.name AS name, o.inspect_text AS inspect_text, o.pickupable AS pickupable "
            "ORDER BY o.object_id",
            player_id=player_id,
        )
        return [
            Item(
                object_id=r["object_id"],
                name=r["name"],
                inspect_text=r.get("inspect_text") or "",
                pickupable=bool(r.get("pickupable")),
            )
            for r in records
        ]

    def get_seen_doors(self, player_id: str) -> list[dict]:
        records = self._run(
            """
            MATCH (:PLAYER {player_id: $player_id})-[r:SEEN_DOOR]->(d:OBJECT:DOOR)
            RETURN d.object_id AS object_id,
                   d.name AS name,
                   d.inspect_text AS inspect_text,
                   d.lock_type AS lock_type,
                   r.created_at AS created_at
            ORDER BY d.object_id
            """,
            player_id=player_id,
        )
        return [
            {
                "object_id": r["object_id"],
                "name": r["name"],
                "inspect_text": r.get("inspect_text") or "",
                "lock_type": r.get("lock_type") or "none",
                "created_at": str(r["created_at"]) if r.get("created_at") else None,
                "seen": True,
                "opened": False,
            }
            for r in records
        ]

    def get_opened_doors(self, player_id: str) -> list[dict]:
        records = self._run(
            """
            MATCH (:PLAYER {player_id: $player_id})-[r:HAS_OPENED]->(d:OBJECT:DOOR)
            RETURN d.object_id AS object_id,
                   d.name AS name,
                   d.inspect_text AS inspect_text,
                   d.lock_type AS lock_type,
                   r.created_at AS created_at
            ORDER BY d.object_id
            """,
            player_id=player_id,
        )
        return [
            {
                "object_id": r["object_id"],
                "name": r["name"],
                "inspect_text": r.get("inspect_text") or "",
                "lock_type": r.get("lock_type") or "none",
                "created_at": str(r["created_at"]) if r.get("created_at") else None,
                "seen": True,
                "opened": True,
            }
            for r in records
        ]

    def get_seen_items(self, player_id: str) -> list[dict]:
        records = self._run(
            """
            MATCH (:PLAYER {player_id: $player_id})-[r:SEEN_OBJECT]->(o:OBJECT:ITEM)
            RETURN o.object_id AS object_id,
                   o.name AS name,
                   o.inspect_text AS inspect_text,
                   o.pickupable AS pickupable,
                   r.created_at AS created_at
            ORDER BY o.object_id
            """,
            player_id=player_id,
        )
        return [
            {
                "object_id": r["object_id"],
                "name": r["name"],
                "inspect_text": r.get("inspect_text") or "",
                "pickupable": bool(r.get("pickupable")),
                "created_at": str(r["created_at"]) if r.get("created_at") else None,
                "seen": True,
                "picked_up": False,
            }
            for r in records
        ]

    def get_picked_up_items(self, player_id: str) -> list[dict]:
        records = self._run(
            """
            MATCH (:PLAYER {player_id: $player_id})-[r:HAS_ITEM]->(o:OBJECT:ITEM)
            RETURN o.object_id AS object_id,
                   o.name AS name,
                   o.inspect_text AS inspect_text,
                   o.pickupable AS pickupable,
                   r.created_at AS created_at
            ORDER BY o.object_id
            """,
            player_id=player_id,
        )
        return [
            {
                "object_id": r["object_id"],
                "name": r["name"],
                "inspect_text": r.get("inspect_text") or "",
                "pickupable": bool(r.get("pickupable")),
                "created_at": str(r["created_at"]) if r.get("created_at") else None,
                "seen": True,
                "picked_up": True,
            }
            for r in records
        ]

    def get_clues(self, player_id: str) -> dict:
        claims = self.get_aware_claims(player_id)
        seen_items = self.get_seen_items(player_id)
        picked_up_items = self.get_picked_up_items(player_id)
        seen_doors = self.get_seen_doors(player_id)
        opened_doors = self.get_opened_doors(player_id)

        items_by_id: dict[str, dict] = {}
        for item in seen_items:
            items_by_id[item["object_id"]] = item

        for item in picked_up_items:
            existing = items_by_id.get(item["object_id"])
            if not existing:
                items_by_id[item["object_id"]] = item
                continue

            existing["picked_up"] = True
            if existing.get("created_at") is None:
                existing["created_at"] = item.get("created_at")

        doors_by_id: dict[str, dict] = {}
        for door in seen_doors:
            doors_by_id[door["object_id"]] = door

        for door in opened_doors:
            existing = doors_by_id.get(door["object_id"])
            if not existing:
                doors_by_id[door["object_id"]] = door
                continue

            existing["opened"] = True
            if existing.get("created_at") is None:
                existing["created_at"] = door.get("created_at")

        return {
            "claims": sorted(claims, key=lambda claim: self._created_at_sort_key(claim, "claim_id")),
            "items": sorted(items_by_id.values(), key=lambda item: self._created_at_sort_key(item, "object_id")),
            "doors": sorted(doors_by_id.values(), key=lambda door: self._created_at_sort_key(door, "object_id")),
        }

    def delete(self, player_id: str) -> bool:
        record = self._run_single(
            "MATCH (p:PLAYER {player_id: $player_id}) "
            "RETURN p.player_id AS player_id",
            player_id=player_id,
        )
        if not record:
            return False

        self._run(
            "MATCH (p:PLAYER {player_id: $player_id})-[:HAS_CONVERSATION]->(c:CONVERSATION) "
            "SET c.player_id = NULL",
            player_id=player_id,
        )
        self._run(
            "MATCH (p:PLAYER {player_id: $player_id}) "
            "DETACH DELETE p",
            player_id=player_id,
        )
        return True
