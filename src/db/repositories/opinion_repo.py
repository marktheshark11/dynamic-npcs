from dataclasses import dataclass
from .base import BaseRepository


@dataclass
class OpinionData:
    """Represents a HAS_OPINION relation between an entity and a claim."""
    entity_id: str      # NPC id or GROUP name
    entity_type: str    # "NPC" or "GROUP"
    claim_id: str
    claim_content: str
    prefix: str | None
    suffix: str | None
    prefix_en: str | None = None
    suffix_en: str | None = None
    overwrite_suffix: str | None = None  # Används istället för default när claim är aware_of
    overwrite_suffix_en: str | None = None
    required_claim_ids: list[str] | None = None
    excluded_claim_ids: list[str] | None = None
    required_seen_object_ids: list[str] | None = None
    excluded_seen_object_ids: list[str] | None = None
    required_item_ids: list[str] | None = None
    excluded_item_ids: list[str] | None = None
    required_seen_door_ids: list[str] | None = None
    excluded_seen_door_ids: list[str] | None = None
    required_opened_door_ids: list[str] | None = None
    excluded_opened_door_ids: list[str] | None = None


class OpinionRepo(BaseRepository):
    """CRUD operations for HAS_OPINION relations."""

    def create(
        self,
        entity_id: str,
        entity_type: str,
        claim_id: str,
        prefix: str | None,
        suffix: str | None,
        prefix_en: str | None = None,
        suffix_en: str | None = None,
        overwrite_suffix: str | None = None,
        overwrite_suffix_en: str | None = None,
        required_claim_ids: list[str] | None = None,
        excluded_claim_ids: list[str] | None = None,
        required_seen_object_ids: list[str] | None = None,
        excluded_seen_object_ids: list[str] | None = None,
        required_item_ids: list[str] | None = None,
        excluded_item_ids: list[str] | None = None,
        required_seen_door_ids: list[str] | None = None,
        excluded_seen_door_ids: list[str] | None = None,
        required_opened_door_ids: list[str] | None = None,
        excluded_opened_door_ids: list[str] | None = None,
    ) -> bool:
        """Create a HAS_OPINION relation from NPC/GROUP to CLAIM.

        entity_type: 'NPC' or 'GROUP'
        For NPC: entity_id matches npc.id
        For GROUP: entity_id matches group.name
        """
        if entity_type == "NPC":
            query = """
            MATCH (npc:NPC {id: $entity_id})
            MATCH (c:CLAIM {claim_id: $claim_id})
            CREATE (npc)-[o:HAS_OPINION]->(c)
            SET o = $props
            RETURN o
            """
        else:
            query = """
            MATCH (g:GROUP {name: $entity_id})
            MATCH (c:CLAIM {claim_id: $claim_id})
            CREATE (g)-[o:HAS_OPINION]->(c)
            SET o = $props
            RETURN o
            """
        props = self._build_props(
            prefix=prefix,
            suffix=suffix,
            prefix_en=prefix_en,
            suffix_en=suffix_en,
            overwrite_suffix=overwrite_suffix,
            overwrite_suffix_en=overwrite_suffix_en,
            required_claim_ids=required_claim_ids,
            excluded_claim_ids=excluded_claim_ids,
            required_seen_object_ids=required_seen_object_ids,
            excluded_seen_object_ids=excluded_seen_object_ids,
            required_item_ids=required_item_ids,
            excluded_item_ids=excluded_item_ids,
            required_seen_door_ids=required_seen_door_ids,
            excluded_seen_door_ids=excluded_seen_door_ids,
            required_opened_door_ids=required_opened_door_ids,
            excluded_opened_door_ids=excluded_opened_door_ids,
        )
        record = self._run_single(
            query, entity_id=entity_id, claim_id=claim_id, props=props,
        )
        return record is not None

    @staticmethod
    def _build_props(**values) -> dict:
        list_fields = {
            "required_claim_ids",
            "excluded_claim_ids",
            "required_seen_object_ids",
            "excluded_seen_object_ids",
            "required_item_ids",
            "excluded_item_ids",
            "required_seen_door_ids",
            "excluded_seen_door_ids",
            "required_opened_door_ids",
            "excluded_opened_door_ids",
        }
        return {
            key: (list(value or []) if key in list_fields else value)
            for key, value in values.items()
        }

    def list_for_entity(self, entity_id: str, entity_type: str) -> list[OpinionData]:
        """List all opinions for a given NPC or GROUP."""
        if entity_type == "NPC":
            query = """
            MATCH (npc:NPC {id: $entity_id})-[o:HAS_OPINION]->(c:CLAIM)
            RETURN npc.id AS eid, c.claim_id AS claim_id, c.content AS content,
                   o.prefix AS prefix, o.suffix AS suffix, o.prefix_en AS prefix_en, o.suffix_en AS suffix_en,
                   o.overwrite_suffix AS overwrite_suffix, o.overwrite_suffix_en AS overwrite_suffix_en,
                   coalesce(o.required_claim_ids, []) AS required_claim_ids,
                   coalesce(o.excluded_claim_ids, []) AS excluded_claim_ids,
                   coalesce(o.required_seen_object_ids, []) AS required_seen_object_ids,
                   coalesce(o.excluded_seen_object_ids, []) AS excluded_seen_object_ids,
                   coalesce(o.required_item_ids, []) AS required_item_ids,
                   coalesce(o.excluded_item_ids, []) AS excluded_item_ids,
                   coalesce(o.required_seen_door_ids, []) AS required_seen_door_ids,
                   coalesce(o.excluded_seen_door_ids, []) AS excluded_seen_door_ids,
                   coalesce(o.required_opened_door_ids, []) AS required_opened_door_ids,
                   coalesce(o.excluded_opened_door_ids, []) AS excluded_opened_door_ids
            ORDER BY c.claim_id
            """
        else:
            query = """
            MATCH (g:GROUP {name: $entity_id})-[o:HAS_OPINION]->(c:CLAIM)
            RETURN g.name AS eid, c.claim_id AS claim_id, c.content AS content,
                   o.prefix AS prefix, o.suffix AS suffix, o.prefix_en AS prefix_en, o.suffix_en AS suffix_en,
                   o.overwrite_suffix AS overwrite_suffix, o.overwrite_suffix_en AS overwrite_suffix_en,
                   coalesce(o.required_claim_ids, []) AS required_claim_ids,
                   coalesce(o.excluded_claim_ids, []) AS excluded_claim_ids,
                   coalesce(o.required_seen_object_ids, []) AS required_seen_object_ids,
                   coalesce(o.excluded_seen_object_ids, []) AS excluded_seen_object_ids,
                   coalesce(o.required_item_ids, []) AS required_item_ids,
                   coalesce(o.excluded_item_ids, []) AS excluded_item_ids,
                   coalesce(o.required_seen_door_ids, []) AS required_seen_door_ids,
                   coalesce(o.excluded_seen_door_ids, []) AS excluded_seen_door_ids,
                   coalesce(o.required_opened_door_ids, []) AS required_opened_door_ids,
                   coalesce(o.excluded_opened_door_ids, []) AS excluded_opened_door_ids
            ORDER BY c.claim_id
            """
        records = self._run(query, entity_id=entity_id)
        return [
            OpinionData(
                entity_id=r["eid"],
                entity_type=entity_type,
                claim_id=r["claim_id"],
                claim_content=r["content"],
                prefix=r.get("prefix"),
                suffix=r.get("suffix"),
                prefix_en=r.get("prefix_en"),
                suffix_en=r.get("suffix_en"),
                overwrite_suffix=r.get("overwrite_suffix"),
                overwrite_suffix_en=r.get("overwrite_suffix_en"),
                required_claim_ids=list(r.get("required_claim_ids") or []),
                excluded_claim_ids=list(r.get("excluded_claim_ids") or []),
                required_seen_object_ids=list(r.get("required_seen_object_ids") or []),
                excluded_seen_object_ids=list(r.get("excluded_seen_object_ids") or []),
                required_item_ids=list(r.get("required_item_ids") or []),
                excluded_item_ids=list(r.get("excluded_item_ids") or []),
                required_seen_door_ids=list(r.get("required_seen_door_ids") or []),
                excluded_seen_door_ids=list(r.get("excluded_seen_door_ids") or []),
                required_opened_door_ids=list(r.get("required_opened_door_ids") or []),
                excluded_opened_door_ids=list(r.get("excluded_opened_door_ids") or []),
            )
            for r in records
        ]

    def delete(self, entity_id: str, entity_type: str, claim_id: str) -> bool:
        """Delete the HAS_OPINION relation between an entity and a claim."""
        if entity_type == "NPC":
            query = """
            MATCH (npc:NPC {id: $entity_id})-[o:HAS_OPINION]->(c:CLAIM {claim_id: $claim_id})
            DELETE o
            RETURN count(o) AS deleted
            """
        else:
            query = """
            MATCH (g:GROUP {name: $entity_id})-[o:HAS_OPINION]->(c:CLAIM {claim_id: $claim_id})
            DELETE o
            RETURN count(o) AS deleted
            """
        record = self._run_single(query, entity_id=entity_id, claim_id=claim_id)
        return record is not None and record["deleted"] > 0

    def update(
        self,
        entity_id: str,
        entity_type: str,
        claim_id: str,
        prefix: str | None,
        suffix: str | None,
        prefix_en: str | None = None,
        suffix_en: str | None = None,
        overwrite_suffix: str | None = None,
        overwrite_suffix_en: str | None = None,
        required_claim_ids: list[str] | None = None,
        excluded_claim_ids: list[str] | None = None,
        required_seen_object_ids: list[str] | None = None,
        excluded_seen_object_ids: list[str] | None = None,
        required_item_ids: list[str] | None = None,
        excluded_item_ids: list[str] | None = None,
        required_seen_door_ids: list[str] | None = None,
        excluded_seen_door_ids: list[str] | None = None,
        required_opened_door_ids: list[str] | None = None,
        excluded_opened_door_ids: list[str] | None = None,
    ) -> bool:
        """Update prefix, suffix and overwrite_suffix for an existing HAS_OPINION relation."""
        if entity_type == "NPC":
            query = """
            MATCH (npc:NPC {id: $entity_id})-[o:HAS_OPINION]->(c:CLAIM {claim_id: $claim_id})
            SET o += $props
            RETURN o
            """
        else:
            query = """
            MATCH (g:GROUP {name: $entity_id})-[o:HAS_OPINION]->(c:CLAIM {claim_id: $claim_id})
            SET o += $props
            RETURN o
            """
        props = self._build_props(
            prefix=prefix,
            suffix=suffix,
            prefix_en=prefix_en,
            suffix_en=suffix_en,
            overwrite_suffix=overwrite_suffix,
            overwrite_suffix_en=overwrite_suffix_en,
            required_claim_ids=required_claim_ids,
            excluded_claim_ids=excluded_claim_ids,
            required_seen_object_ids=required_seen_object_ids,
            excluded_seen_object_ids=excluded_seen_object_ids,
            required_item_ids=required_item_ids,
            excluded_item_ids=excluded_item_ids,
            required_seen_door_ids=required_seen_door_ids,
            excluded_seen_door_ids=excluded_seen_door_ids,
            required_opened_door_ids=required_opened_door_ids,
            excluded_opened_door_ids=excluded_opened_door_ids,
        )

        record = self._run_single(
            query,
            entity_id=entity_id,
            claim_id=claim_id,
            props=props,
        )
        return record is not None
