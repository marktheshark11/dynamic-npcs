# DB Builder Restructure Plan

## Overview

Restructure `db/builder.py` and `db/node_builder.py` into a well-organized class-based architecture with Command pattern, Repository pattern, and reusable UI helpers. The schema is migrated from `Mark/db_utils.py` with `HAS_OPINION` replacing `BELIEF/STANCE`, and adding GROUPs, OBJECTs, PLACEs, structural/affective relations, and REFERENCEs.

## Directory Structure

```
db/
├── main.py                     # Entry point
├── config.py                   # Config class: DB connection + embedding model
├── app.py                      # App class: builds menus, runs main loop
│
├── models/
│   ├── __init__.py
│   ├── npc.py                  # NPC, Group dataclasses
│   ├── claim.py                # Claim dataclass
│   └── constant.py             # Object, Place dataclasses
│
├── repositories/
│   ├── __init__.py
│   ├── base.py                 # BaseRepository with driver + session helpers
│   ├── npc_repo.py             # NPC CRUD + GROUP CRUD
│   ├── claim_repo.py           # Claim CRUD (auto-ID, embedding on create/edit)
│   ├── constant_repo.py        # OBJECT + PLACE CRUD
│   ├── opinion_repo.py         # HAS_OPINION CRUD (NPC/GROUP -> CLAIM)
│   └── relation_repo.py        # Structural, affective, REFERENCE, MEMBER_OF
│
├── services/
│   ├── __init__.py
│   └── embedding.py            # EmbeddingService wrapper
│
├── commands/
│   ├── __init__.py
│   ├── base.py                 # Command ABC
│   ├── npc_commands.py         # CreateNPC, EditNPC, DeleteNPC, ListNPCs
│   ├── group_commands.py       # CreateGroup, DeleteGroup, ListGroups
│   ├── claim_commands.py       # CreateClaim, EditClaim, DeleteClaim, ListClaims
│   ├── constant_commands.py    # CreateObject, CreatePlace, ListConstants
│   ├── opinion_commands.py     # CreateOpinion, DeleteOpinion, ListOpinions
│   └── relation_commands.py    # Structural, affective, reference, membership
│
└── ui/
    ├── __init__.py
    ├── menu.py                 # Menu + SubMenu classes
    ├── display.py              # Formatting (headers, success/error, tables)
    └── input_helpers.py        # Validated input, list selection, confirmation
```

## File-by-File Implementation

---

### 1. `db/models/__init__.py`

```python
from .npc import NPC, Group
from .claim import Claim
from .constant import Object, Place

__all__ = ["NPC", "Group", "Claim", "Object", "Place"]
```

### 2. `db/models/npc.py`

```python
from dataclasses import dataclass


@dataclass
class NPC:
    id: str
    name: str
    age: int
    personality: str

    def display_str(self) -> str:
        return f"ID: {self.id}, Namn: {self.name}, Alder: {self.age}, Personlighet: {self.personality}"

    def short_str(self) -> str:
        return f"ID: {self.id}, Namn: {self.name}"


@dataclass
class Group:
    name: str

    def display_str(self) -> str:
        return f"Namn: {self.name}"

    def short_str(self) -> str:
        return self.name
```

### 3. `db/models/claim.py`

```python
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Claim:
    claim_id: str
    content: str
    type: Optional[str] = None
    negative: Optional[str] = None
    embedding: Optional[list[float]] = field(default=None, repr=False)

    def display_str(self) -> str:
        type_str = f" [{self.type}]" if self.type else ""
        content_preview = self.content[:60] + "..." if len(self.content) > 60 else self.content
        return f"{self.claim_id}{type_str}: {content_preview}"

    def short_str(self) -> str:
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"{self.claim_id}: {content_preview}"
```

### 4. `db/models/constant.py`

```python
from dataclasses import dataclass


@dataclass
class Object:
    name: str

    def display_str(self) -> str:
        return f"[OBJECT] {self.name}"

    def short_str(self) -> str:
        return self.name


@dataclass
class Place:
    name: str

    def display_str(self) -> str:
        return f"[PLACE] {self.name}"

    def short_str(self) -> str:
        return self.name
```

---

### 5. `db/services/__init__.py`

```python
from .embedding import EmbeddingService

__all__ = ["EmbeddingService"]
```

### 6. `db/services/embedding.py`

```python
from langchain_community.embeddings import OllamaEmbeddings


class EmbeddingService:
    """Wrapper around the embedding model.

    Centralizes embedding creation so the model can be swapped
    without touching repositories or commands.
    """

    def __init__(self, model: OllamaEmbeddings) -> None:
        self._model = model

    def embed(self, text: str) -> list[float]:
        """Create an embedding vector for document content."""
        return self._model.embed_query(text)

    def embed_query(self, text: str) -> list[float]:
        """Create an embedding vector for a search query (with search prefix)."""
        return self._model.embed_query(
            f"Represent this sentence for searching relevant passages: {text}"
        )
```

---

### 7. `db/repositories/__init__.py`

```python
from .npc_repo import NPCRepo, GroupRepo
from .claim_repo import ClaimRepo
from .constant_repo import ConstantRepo
from .opinion_repo import OpinionRepo
from .relation_repo import RelationRepo

__all__ = [
    "NPCRepo",
    "GroupRepo",
    "ClaimRepo",
    "ConstantRepo",
    "OpinionRepo",
    "RelationRepo",
]
```

### 8. `db/repositories/base.py`

```python
from neo4j import Driver, Record


class BaseRepository:
    """Base class for all repositories. Provides driver access and query helpers."""

    def __init__(self, driver: Driver) -> None:
        self._driver = driver

    def _run(self, query: str, **params) -> list[Record]:
        """Execute a query and return all records."""
        with self._driver.session() as session:
            result = session.run(query, **params)
            return list(result)

    def _run_single(self, query: str, **params) -> Record | None:
        """Execute a query and return the first record, or None."""
        with self._driver.session() as session:
            result = session.run(query, **params)
            return result.single()
```

### 9. `db/repositories/npc_repo.py`

```python
from .base import BaseRepository
from db.models import NPC, Group


class NPCRepo(BaseRepository):
    """CRUD operations for NPC nodes."""

    def create(self, npc: NPC) -> None:
        self._run(
            "MERGE (npc:NPC {id: $id, name: $name, age: $age, personality: $personality})",
            id=npc.id, name=npc.name, age=npc.age, personality=npc.personality,
        )

    def get_by_id(self, id: str) -> NPC | None:
        record = self._run_single(
            "MATCH (npc:NPC {id: $id}) "
            "RETURN npc.id AS id, npc.name AS name, npc.age AS age, npc.personality AS personality",
            id=id,
        )
        if not record:
            return None
        return NPC(
            id=record["id"],
            name=record["name"],
            age=record["age"],
            personality=record["personality"],
        )

    def list_all(self) -> list[NPC]:
        records = self._run(
            "MATCH (npc:NPC) "
            "RETURN npc.id AS id, npc.name AS name, npc.age AS age, npc.personality AS personality "
            "ORDER BY npc.id"
        )
        return [
            NPC(id=r["id"], name=r["name"], age=r["age"], personality=r["personality"])
            for r in records
        ]

    def update(self, id: str, name: str | None = None, age: int | None = None,
               personality: str | None = None) -> bool:
        set_clauses = []
        params: dict = {"id": id}

        if name is not None:
            set_clauses.append("npc.name = $name")
            params["name"] = name
        if age is not None:
            set_clauses.append("npc.age = $age")
            params["age"] = age
        if personality is not None:
            set_clauses.append("npc.personality = $personality")
            params["personality"] = personality

        if not set_clauses:
            return False

        query = f"MATCH (npc:NPC {{id: $id}}) SET {', '.join(set_clauses)} RETURN npc"
        record = self._run_single(query, **params)
        return record is not None

    def delete(self, id: str) -> bool:
        """Delete an NPC and all its relations."""
        record = self._run_single(
            "MATCH (npc:NPC {id: $id}) RETURN npc", id=id,
        )
        if not record:
            return False
        self._run("MATCH (npc:NPC {id: $id}) DETACH DELETE npc", id=id)
        return True


class GroupRepo(BaseRepository):
    """CRUD operations for GROUP nodes."""

    def create(self, name: str) -> Group:
        formatted = name.capitalize()
        self._run("MERGE (g:GROUP {name: $name})", name=formatted)
        return Group(name=formatted)

    def list_all(self) -> list[Group]:
        records = self._run(
            "MATCH (g:GROUP) RETURN g.name AS name ORDER BY g.name"
        )
        return [Group(name=r["name"]) for r in records]

    def delete(self, name: str) -> bool:
        record = self._run_single(
            "MATCH (g:GROUP {name: $name}) RETURN g", name=name,
        )
        if not record:
            return False
        self._run("MATCH (g:GROUP {name: $name}) DETACH DELETE g", name=name)
        return True
```

### 10. `db/repositories/claim_repo.py`

```python
from .base import BaseRepository
from db.models import Claim
from db.services import EmbeddingService


class ClaimRepo(BaseRepository):
    """CRUD operations for CLAIM nodes. Auto-generates IDs and embeddings."""

    def __init__(self, driver, embedding_service: EmbeddingService) -> None:
        super().__init__(driver)
        self._embedding = embedding_service

    def _next_claim_id(self) -> str:
        """Get next available claim ID (C1, C2, C3, ...)."""
        records = self._run(
            "MATCH (c:CLAIM) "
            "WHERE c.claim_id IS NOT NULL AND c.claim_id STARTS WITH 'C' "
            "RETURN c.claim_id AS claim_id"
        )
        if not records:
            return "C1"

        numbers = []
        for r in records:
            try:
                numbers.append(int(r["claim_id"][1:]))
            except ValueError:
                continue

        return f"C{max(numbers) + 1}" if numbers else "C1"

    def create(self, content: str, claim_type: str | None = None,
               negative: str | None = None) -> Claim:
        embedding = self._embedding.embed(content)
        claim_id = self._next_claim_id()

        params: dict = {
            "claim_id": claim_id,
            "content": content,
            "embedding": embedding,
        }

        set_parts = []
        if claim_type:
            set_parts.append("c.type = $type")
            params["type"] = claim_type
        if negative:
            set_parts.append("c.negative = $negative")
            params["negative"] = negative

        set_clause = f" SET {', '.join(set_parts)}" if set_parts else ""
        query = (
            "CREATE (c:CLAIM {claim_id: $claim_id, content: $content, embedding: $embedding})"
            f"{set_clause} RETURN c.claim_id AS claim_id"
        )
        self._run(query, **params)
        return Claim(claim_id=claim_id, content=content, type=claim_type,
                     negative=negative, embedding=embedding)

    def list_all(self) -> list[Claim]:
        records = self._run(
            "MATCH (c:CLAIM) "
            "RETURN c.claim_id AS claim_id, c.content AS content, "
            "c.type AS type, c.negative AS negative "
            "ORDER BY c.claim_id"
        )
        return [
            Claim(
                claim_id=r["claim_id"],
                content=r["content"],
                type=r["type"],
                negative=r["negative"],
            )
            for r in records
        ]

    def get_by_id(self, claim_id: str) -> Claim | None:
        record = self._run_single(
            "MATCH (c:CLAIM {claim_id: $claim_id}) "
            "RETURN c.claim_id AS claim_id, c.content AS content, "
            "c.type AS type, c.negative AS negative",
            claim_id=claim_id,
        )
        if not record:
            return None
        return Claim(
            claim_id=record["claim_id"],
            content=record["content"],
            type=record["type"],
            negative=record["negative"],
        )

    def update(self, claim_id: str, content: str | None = None,
               claim_type: str | None = ..., negative: str | None = ...) -> bool:
        """Update a claim. Use None for 'no change', empty string to remove a property.

        Note: claim_type and negative use sentinel default (...) to distinguish
        'not provided' from 'set to None'.
        """
        record = self._run_single(
            "MATCH (c:CLAIM {claim_id: $claim_id}) RETURN c",
            claim_id=claim_id,
        )
        if not record:
            return False

        updates = []
        params: dict = {"claim_id": claim_id}

        if content is not None:
            embedding = self._embedding.embed(content)
            updates.append("c.content = $content")
            updates.append("c.embedding = $embedding")
            params["content"] = content
            params["embedding"] = embedding

        if claim_type is not ...:
            if claim_type is None or claim_type == "":
                updates.append("c.type = null")
            else:
                updates.append("c.type = $type")
                params["type"] = claim_type

        if negative is not ...:
            if negative is None or negative == "":
                updates.append("c.negative = null")
            else:
                updates.append("c.negative = $negative")
                params["negative"] = negative

        if not updates:
            return False

        query = f"MATCH (c:CLAIM {{claim_id: $claim_id}}) SET {', '.join(updates)} RETURN c"
        self._run(query, **params)
        return True

    def delete(self, claim_id: str) -> tuple[bool, int]:
        """Delete a claim and all HAS_OPINION relations pointing to it.

        Returns (success, opinion_count).
        """
        record = self._run_single(
            "MATCH (c:CLAIM {claim_id: $claim_id}) "
            "OPTIONAL MATCH ()-[r:HAS_OPINION]->(c) "
            "RETURN c.content AS content, count(r) AS opinion_count",
            claim_id=claim_id,
        )
        if not record or not record["content"]:
            return False, 0

        opinion_count = record["opinion_count"]
        self._run(
            "MATCH (c:CLAIM {claim_id: $claim_id}) "
            "OPTIONAL MATCH ()-[r:HAS_OPINION]->(c) "
            "OPTIONAL MATCH (c)-[ref:REFERENCE]-() "
            "DELETE r, ref, c",
            claim_id=claim_id,
        )
        return True, opinion_count
```

### 11. `db/repositories/constant_repo.py`

```python
from .base import BaseRepository
from db.models import Object, Place


class ConstantRepo(BaseRepository):
    """CRUD operations for OBJECT and PLACE nodes."""

    # --- OBJECT ---

    def create_object(self, name: str) -> Object:
        formatted = name.capitalize()
        self._run("MERGE (o:OBJECT {name: $name})", name=formatted)
        return Object(name=formatted)

    def list_objects(self) -> list[Object]:
        records = self._run(
            "MATCH (o:OBJECT) RETURN o.name AS name ORDER BY o.name"
        )
        return [Object(name=r["name"]) for r in records]

    def delete_object(self, name: str) -> bool:
        record = self._run_single(
            "MATCH (o:OBJECT {name: $name}) RETURN o", name=name,
        )
        if not record:
            return False
        self._run("MATCH (o:OBJECT {name: $name}) DETACH DELETE o", name=name)
        return True

    # --- PLACE ---

    def create_place(self, name: str) -> Place:
        formatted = name.capitalize()
        self._run("MERGE (p:PLACE {name: $name})", name=formatted)
        return Place(name=formatted)

    def list_places(self) -> list[Place]:
        records = self._run(
            "MATCH (p:PLACE) RETURN p.name AS name ORDER BY p.name"
        )
        return [Place(name=r["name"]) for r in records]

    def delete_place(self, name: str) -> bool:
        record = self._run_single(
            "MATCH (p:PLACE {name: $name}) RETURN p", name=name,
        )
        if not record:
            return False
        self._run("MATCH (p:PLACE {name: $name}) DETACH DELETE p", name=name)
        return True

    # --- Combined ---

    def list_all(self) -> list[Object | Place]:
        """List all OBJECTs and PLACEs together."""
        records = self._run(
            "MATCH (c) WHERE c:OBJECT OR c:PLACE "
            "RETURN labels(c)[0] AS label, c.name AS name "
            "ORDER BY labels(c)[0], c.name"
        )
        items: list[Object | Place] = []
        for r in records:
            if r["label"] == "OBJECT":
                items.append(Object(name=r["name"]))
            else:
                items.append(Place(name=r["name"]))
        return items
```

### 12. `db/repositories/opinion_repo.py`

```python
from dataclasses import dataclass
from .base import BaseRepository


@dataclass
class OpinionData:
    """Represents a HAS_OPINION relation between an entity and a claim."""
    entity_id: str      # NPC id or GROUP name
    entity_type: str    # "NPC" or "GROUP"
    claim_id: str
    claim_content: str
    belief_in: float
    openness: float


class OpinionRepo(BaseRepository):
    """CRUD operations for HAS_OPINION relations."""

    def create(self, entity_id: str, entity_type: str, claim_id: str,
               belief_in: float, openness: float) -> bool:
        """Create a HAS_OPINION relation from NPC/GROUP to CLAIM.

        entity_type: 'NPC' or 'GROUP'
        For NPC: entity_id matches npc.id
        For GROUP: entity_id matches group.name
        """
        if entity_type == "NPC":
            query = """
            MATCH (npc:NPC {id: $entity_id})
            MATCH (c:CLAIM {claim_id: $claim_id})
            CREATE (npc)-[o:HAS_OPINION {belief_in: $belief_in, openness: $openness}]->(c)
            RETURN o
            """
        else:
            query = """
            MATCH (g:GROUP {name: $entity_id})
            MATCH (c:CLAIM {claim_id: $claim_id})
            CREATE (g)-[o:HAS_OPINION {belief_in: $belief_in, openness: $openness}]->(c)
            RETURN o
            """
        record = self._run_single(
            query, entity_id=entity_id, claim_id=claim_id,
            belief_in=belief_in, openness=openness,
        )
        return record is not None

    def list_for_entity(self, entity_id: str, entity_type: str) -> list[OpinionData]:
        """List all opinions for a given NPC or GROUP."""
        if entity_type == "NPC":
            query = """
            MATCH (npc:NPC {id: $entity_id})-[o:HAS_OPINION]->(c:CLAIM)
            RETURN npc.id AS eid, c.claim_id AS claim_id, c.content AS content,
                   o.belief_in AS belief_in, o.openness AS openness
            ORDER BY c.claim_id
            """
        else:
            query = """
            MATCH (g:GROUP {name: $entity_id})-[o:HAS_OPINION]->(c:CLAIM)
            RETURN g.name AS eid, c.claim_id AS claim_id, c.content AS content,
                   o.belief_in AS belief_in, o.openness AS openness
            ORDER BY c.claim_id
            """
        records = self._run(query, entity_id=entity_id)
        return [
            OpinionData(
                entity_id=r["eid"],
                entity_type=entity_type,
                claim_id=r["claim_id"],
                claim_content=r["content"],
                belief_in=r["belief_in"],
                openness=r["openness"],
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
```

### 13. `db/repositories/relation_repo.py`

```python
from dataclasses import dataclass
from .base import BaseRepository


# Structural relation types with their inverse
STRUCTURAL_RELATIONS = {
    "SIBLING_WITH": "SIBLING_WITH",
    "FRIENDS_WITH": "FRIENDS_WITH",
    "DATING": "DATING",
    "MARRIED_TO": "MARRIED_TO",
    "DIVORCED_FROM": "DIVORCED_FROM",
    "PARENT_TO": "CHILD_TO",
    "CHILD_TO": "PARENT_TO",
}


@dataclass
class StructuralRelation:
    npc_a: str
    npc_b: str
    relation_type: str
    secrecy: float


@dataclass
class AffectiveRelation:
    npc_from: str
    npc_to: str
    affection: float
    demeanour: float


class RelationRepo(BaseRepository):
    """CRUD for structural relations, affective relations, REFERENCE, and MEMBER_OF."""

    # --- Structural ---

    def create_structural(self, name_a: str, name_b: str,
                          relation_type: str, secrecy: float = 0) -> bool:
        """Create a bidirectional structural relation between two NPCs."""
        if relation_type not in STRUCTURAL_RELATIONS:
            return False

        inverse = STRUCTURAL_RELATIONS[relation_type]

        # Forward relation
        self._run(
            f"MATCH (a:NPC {{name: $a}}), (b:NPC {{name: $b}}) "
            f"MERGE (a)-[r:{relation_type}]->(b) SET r.secrecy = $secrecy",
            a=name_a, b=name_b, secrecy=secrecy,
        )
        # Inverse relation
        self._run(
            f"MATCH (a:NPC {{name: $a}}), (b:NPC {{name: $b}}) "
            f"MERGE (b)-[r:{inverse}]->(a) SET r.secrecy = $secrecy",
            a=name_a, b=name_b, secrecy=secrecy,
        )
        return True

    def delete_all_between(self, name_a: str, name_b: str) -> int:
        """Remove all relations between two NPCs. Returns count of deleted."""
        record = self._run_single(
            "MATCH (a:NPC {name: $a})-[r]-(b:NPC {name: $b}) "
            "DELETE r RETURN count(r) AS cnt",
            a=name_a, b=name_b,
        )
        return record["cnt"] if record else 0

    # --- Affective ---

    def create_affective(self, name_from: str, name_to: str,
                         affection: float, demeanour: float) -> bool:
        """Create AFFECTION + DEMEANOUR relations from one NPC to another."""
        record = self._run_single(
            "MATCH (a:NPC {name: $a}), (b:NPC {name: $b}) "
            "MERGE (a)-[aff:AFFECTION]->(b) SET aff.intensity = $affection "
            "MERGE (a)-[dem:DEMEANOUR]->(b) SET dem.intensity = $demeanour "
            "RETURN a",
            a=name_from, b=name_to, affection=affection, demeanour=demeanour,
        )
        return record is not None

    # --- REFERENCE ---

    def create_reference(self, claim_id: str, target_name: str,
                         target_type: str) -> bool:
        """Create a REFERENCE from a CLAIM to another node.

        target_type: 'NPC', 'CLAIM', 'OBJECT', 'PLACE'
        For CLAIMs: target_name is the claim_id (e.g. 'C5')
        For others: target_name is the name property
        """
        if target_type == "CLAIM":
            query = """
            MATCH (c:CLAIM {claim_id: $claim_id})
            MATCH (t:CLAIM {claim_id: $target})
            MERGE (c)-[:REFERENCE]->(t)
            RETURN c
            """
        elif target_type == "NPC":
            query = """
            MATCH (c:CLAIM {claim_id: $claim_id})
            MATCH (t:NPC {name: $target})
            MERGE (c)-[:REFERENCE]->(t)
            RETURN c
            """
        elif target_type == "OBJECT":
            query = """
            MATCH (c:CLAIM {claim_id: $claim_id})
            MATCH (t:OBJECT {name: $target})
            MERGE (c)-[:REFERENCE]->(t)
            RETURN c
            """
        elif target_type == "PLACE":
            query = """
            MATCH (c:CLAIM {claim_id: $claim_id})
            MATCH (t:PLACE {name: $target})
            MERGE (c)-[:REFERENCE]->(t)
            RETURN c
            """
        else:
            return False

        record = self._run_single(query, claim_id=claim_id, target=target_name)
        return record is not None

    # --- MEMBER_OF ---

    def create_membership(self, npc_id: str, group_name: str) -> bool:
        """Create MEMBER_OF relation from NPC to GROUP."""
        record = self._run_single(
            "MATCH (npc:NPC {id: $npc_id}), (g:GROUP {name: $group_name}) "
            "MERGE (npc)-[:MEMBER_OF]->(g) RETURN npc",
            npc_id=npc_id, group_name=group_name,
        )
        return record is not None

    def delete_membership(self, npc_id: str, group_name: str) -> bool:
        """Remove MEMBER_OF relation."""
        record = self._run_single(
            "MATCH (npc:NPC {id: $npc_id})-[r:MEMBER_OF]->(g:GROUP {name: $group_name}) "
            "DELETE r RETURN count(r) AS cnt",
            npc_id=npc_id, group_name=group_name,
        )
        return record is not None and record["cnt"] > 0

    def list_members(self, group_name: str) -> list[str]:
        """List NPC ids that are members of a group."""
        records = self._run(
            "MATCH (npc:NPC)-[:MEMBER_OF]->(g:GROUP {name: $name}) "
            "RETURN npc.id AS id ORDER BY npc.id",
            name=group_name,
        )
        return [r["id"] for r in records]
```

---

### 14. `db/ui/__init__.py`

```python
from .display import Display
from .input_helpers import InputHelpers
from .menu import Menu, SubMenu

__all__ = ["Display", "InputHelpers", "Menu", "SubMenu"]
```

### 15. `db/ui/display.py`

```python
class Display:
    """Terminal display formatting helpers."""

    @staticmethod
    def header(title: str) -> None:
        print(f"\n=== {title} ===")

    @staticmethod
    def success(msg: str) -> None:
        print(f"\n* {msg}")

    @staticmethod
    def error(msg: str) -> None:
        print(f"\nx {msg}")

    @staticmethod
    def info(msg: str) -> None:
        print(f"  {msg}")

    @staticmethod
    def list_items(items: list, display_fn=None) -> None:
        """Print a numbered list of items."""
        for idx, item in enumerate(items, 1):
            text = display_fn(item) if display_fn else str(item)
            print(f"  {idx}. {text}")
```

### 16. `db/ui/input_helpers.py`

```python
from typing import TypeVar, Callable, Optional

from .display import Display

T = TypeVar("T")


class InputHelpers:
    """Reusable validated-input helpers for the terminal UI."""

    def __init__(self) -> None:
        self.display = Display()

    # --- Basic prompts ---

    def prompt(self, label: str) -> str:
        """Prompt for a non-empty string."""
        while True:
            value = input(f"{label}: ").strip()
            if value:
                return value
            self.display.error("Vardet far inte vara tomt")

    def prompt_optional(self, label: str) -> Optional[str]:
        """Prompt for an optional string (empty = None)."""
        value = input(f"{label} (lamna tom for ingen andring): ").strip()
        return value if value else None

    def prompt_int(self, label: str) -> int:
        """Prompt for an integer."""
        while True:
            raw = input(f"{label}: ").strip()
            try:
                return int(raw)
            except ValueError:
                self.display.error("Ange ett heltal")

    def prompt_optional_int(self, label: str) -> Optional[int]:
        """Prompt for an optional integer (empty = None)."""
        raw = input(f"{label} (lamna tom for ingen andring): ").strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            self.display.error("Ogiltigt tal, ingen andring gjord")
            return None

    def prompt_float(self, label: str, min_val: float = -1.0,
                     max_val: float = 1.0) -> float:
        """Prompt for a float within a range."""
        while True:
            raw = input(f"{label} ({min_val} till {max_val}): ").strip()
            try:
                value = float(raw)
                if min_val <= value <= max_val:
                    return value
                self.display.error(f"Vardet maste vara mellan {min_val} och {max_val}")
            except ValueError:
                self.display.error("Ange ett tal")

    def confirm(self, message: str) -> bool:
        """Ask for yes/no confirmation."""
        response = input(f"\n{message} (j/n): ").strip().lower()
        return response == "j"

    # --- List selection ---

    def select_from_list(self, items: list[T], display_fn: Callable[[T], str],
                         title: str = "Valj") -> Optional[T]:
        """Display a numbered list and let the user pick one item.

        Returns the selected item, or None if the list is empty.
        """
        if not items:
            self.display.error("Inga objekt hittades")
            return None

        self.display.header(title)
        self.display.list_items(items, display_fn)

        choice = input(f"\nValj nummer (1-{len(items)}): ").strip()
        try:
            idx = int(choice)
            if 1 <= idx <= len(items):
                return items[idx - 1]
        except ValueError:
            pass

        self.display.error("Ogiltigt val")
        return None

    def select_option(self, options: list[str], title: str = "Valj") -> Optional[str]:
        """Display a list of string options and return the selected one."""
        return self.select_from_list(options, lambda x: x, title)
```

### 17. `db/ui/menu.py`

```python
from __future__ import annotations
from typing import Protocol


class Executable(Protocol):
    """Any object with a name and execute method can be a menu item."""

    @property
    def name(self) -> str: ...

    def execute(self) -> None: ...


class Menu:
    """Interactive numbered menu that loops until the user exits."""

    def __init__(self, title: str, items: list[Executable]) -> None:
        self._title = title
        self._items = items

    def run(self) -> None:
        while True:
            print(f"\n=== {self._title} ===")
            for i, item in enumerate(self._items, 1):
                print(f"  {i}: {item.name}")
            print("  0: Tillbaka")

            choice = input("Valj: ").strip()
            if choice == "0":
                break

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(self._items):
                    self._items[idx].execute()
                else:
                    print("Ogiltigt val")
            except ValueError:
                print("Ogiltigt val")
            except KeyboardInterrupt:
                print("\nAvbruten")
                break


class SubMenu:
    """A menu item that opens a nested Menu when selected."""

    def __init__(self, title: str, items: list[Executable]) -> None:
        self._title = title
        self._menu = Menu(title, items)

    @property
    def name(self) -> str:
        return self._title

    def execute(self) -> None:
        self._menu.run()
```

---

### 18. `db/commands/__init__.py`

```python
from .base import Command
from .npc_commands import CreateNPCCommand, EditNPCCommand, DeleteNPCCommand, ListNPCsCommand
from .group_commands import CreateGroupCommand, DeleteGroupCommand, ListGroupsCommand
from .claim_commands import CreateClaimCommand, EditClaimCommand, DeleteClaimCommand, ListClaimsCommand
from .constant_commands import CreateObjectCommand, CreatePlaceCommand, ListConstantsCommand
from .opinion_commands import CreateOpinionCommand, DeleteOpinionCommand, ListOpinionsCommand
from .relation_commands import (
    CreateStructuralRelationCommand,
    CreateAffectiveRelationCommand,
    CreateReferenceCommand,
    CreateMembershipCommand,
    DeleteMembershipCommand,
)

__all__ = [
    "Command",
    "CreateNPCCommand", "EditNPCCommand", "DeleteNPCCommand", "ListNPCsCommand",
    "CreateGroupCommand", "DeleteGroupCommand", "ListGroupsCommand",
    "CreateClaimCommand", "EditClaimCommand", "DeleteClaimCommand", "ListClaimsCommand",
    "CreateObjectCommand", "CreatePlaceCommand", "ListConstantsCommand",
    "CreateOpinionCommand", "DeleteOpinionCommand", "ListOpinionsCommand",
    "CreateStructuralRelationCommand", "CreateAffectiveRelationCommand",
    "CreateReferenceCommand", "CreateMembershipCommand", "DeleteMembershipCommand",
]
```

### 19. `db/commands/base.py`

```python
from abc import ABC, abstractmethod


class Command(ABC):
    """Abstract base for all menu commands."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Display name shown in the menu."""
        ...

    @abstractmethod
    def execute(self) -> None:
        """Run the command (interactive, may prompt for input)."""
        ...
```

### 20. `db/commands/npc_commands.py`

```python
from .base import Command
from db.repositories import NPCRepo
from db.models import NPC
from db.ui import InputHelpers


class CreateNPCCommand(Command):
    def __init__(self, repo: NPCRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Skapa en ny NPC"

    def execute(self) -> None:
        id_val = self._ui.prompt("id")
        name_val = self._ui.prompt("namn")
        age_val = self._ui.prompt_int("alder")
        personality_val = self._ui.prompt("personlighet")

        npc = NPC(id=id_val, name=name_val, age=age_val, personality=personality_val)
        self._repo.create(npc)
        self._ui.display.success(f"NPC '{name_val}' skapad")


class EditNPCCommand(Command):
    def __init__(self, repo: NPCRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Redigera en NPC"

    def execute(self) -> None:
        npcs = self._repo.list_all()
        selected = self._ui.select_from_list(npcs, NPC.display_str, "Alla NPCs")
        if not selected:
            return

        name_val = self._ui.prompt_optional("namn")
        age_val = self._ui.prompt_optional_int("alder")
        personality_val = self._ui.prompt_optional("personlighet")

        if self._repo.update(selected.id, name_val, age_val, personality_val):
            self._ui.display.success(f"NPC '{selected.id}' uppdaterad")
        else:
            self._ui.display.error("Inga andringar gjorda")


class DeleteNPCCommand(Command):
    def __init__(self, repo: NPCRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Ta bort en NPC"

    def execute(self) -> None:
        npcs = self._repo.list_all()
        selected = self._ui.select_from_list(npcs, NPC.display_str, "Alla NPCs")
        if not selected:
            return

        if self._ui.confirm(f"Ta bort NPC '{selected.name}'?"):
            if self._repo.delete(selected.id):
                self._ui.display.success(f"NPC '{selected.name}' borttagen")
            else:
                self._ui.display.error("Kunde inte ta bort NPC")


class ListNPCsCommand(Command):
    def __init__(self, repo: NPCRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Visa alla NPCs"

    def execute(self) -> None:
        npcs = self._repo.list_all()
        if not npcs:
            self._ui.display.error("Inga NPCs hittades")
            return
        self._ui.display.header("Alla NPCs")
        self._ui.display.list_items(npcs, NPC.display_str)
```

### 21. `db/commands/group_commands.py`

```python
from .base import Command
from db.repositories import GroupRepo
from db.models import Group
from db.ui import InputHelpers


class CreateGroupCommand(Command):
    def __init__(self, repo: GroupRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Skapa en ny grupp"

    def execute(self) -> None:
        name_val = self._ui.prompt("gruppnamn")
        group = self._repo.create(name_val)
        self._ui.display.success(f"GROUP '{group.name}' skapad")


class DeleteGroupCommand(Command):
    def __init__(self, repo: GroupRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Ta bort en grupp"

    def execute(self) -> None:
        groups = self._repo.list_all()
        selected = self._ui.select_from_list(groups, Group.display_str, "Alla grupper")
        if not selected:
            return

        if self._ui.confirm(f"Ta bort GROUP '{selected.name}'?"):
            if self._repo.delete(selected.name):
                self._ui.display.success(f"GROUP '{selected.name}' borttagen")
            else:
                self._ui.display.error("Kunde inte ta bort gruppen")


class ListGroupsCommand(Command):
    def __init__(self, repo: GroupRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Visa alla grupper"

    def execute(self) -> None:
        groups = self._repo.list_all()
        if not groups:
            self._ui.display.error("Inga grupper hittades")
            return
        self._ui.display.header("Alla grupper")
        self._ui.display.list_items(groups, Group.display_str)
```

### 22. `db/commands/claim_commands.py`

```python
from .base import Command
from db.repositories import ClaimRepo
from db.models import Claim
from db.ui import InputHelpers


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
        negative = self._ui.prompt_optional("negativ formulering")

        claim = self._repo.create(content, claim_type=claim_type, negative=negative)
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
        self._ui.display.info(f"Nuvarande negativ: {selected.negative or '(ingen)'}")

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

        new_negative = self._ui.prompt_optional("ny negativ formulering")
        # Use ... sentinel for 'no change'
        neg_val = new_negative if new_negative is not None else ...

        if self._repo.update(selected.claim_id, content=new_content,
                             claim_type=new_type, negative=neg_val):
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
```

### 23. `db/commands/constant_commands.py`

```python
from .base import Command
from db.repositories import ConstantRepo
from db.models import Object, Place
from db.ui import InputHelpers


class CreateObjectCommand(Command):
    def __init__(self, repo: ConstantRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Skapa ett nytt OBJECT"

    def execute(self) -> None:
        name = self._ui.prompt("objektnamn")
        obj = self._repo.create_object(name)
        self._ui.display.success(f"OBJECT '{obj.name}' skapad")


class CreatePlaceCommand(Command):
    def __init__(self, repo: ConstantRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Skapa en ny PLACE"

    def execute(self) -> None:
        name = self._ui.prompt("platsnamn")
        place = self._repo.create_place(name)
        self._ui.display.success(f"PLACE '{place.name}' skapad")


class ListConstantsCommand(Command):
    def __init__(self, repo: ConstantRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Visa alla objekt och platser"

    def execute(self) -> None:
        items = self._repo.list_all()
        if not items:
            self._ui.display.error("Inga objekt eller platser hittades")
            return

        self._ui.display.header("Alla konstanter")
        for idx, item in enumerate(items, 1):
            print(f"  {idx}. {item.display_str()}")
```

### 24. `db/commands/opinion_commands.py`

```python
from .base import Command
from db.repositories import NPCRepo, GroupRepo, ClaimRepo, OpinionRepo
from db.models import NPC, Group, Claim
from db.ui import InputHelpers


class CreateOpinionCommand(Command):
    def __init__(self, npc_repo: NPCRepo, group_repo: GroupRepo,
                 claim_repo: ClaimRepo, opinion_repo: OpinionRepo,
                 ui: InputHelpers) -> None:
        self._npc_repo = npc_repo
        self._group_repo = group_repo
        self._claim_repo = claim_repo
        self._opinion_repo = opinion_repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Koppla NPC/Grupp till CLAIM"

    def execute(self) -> None:
        # Choose entity type
        entity_type = self._ui.select_option(["NPC", "GROUP"], "Valj entitetstyp")
        if not entity_type:
            return

        # Select entity
        if entity_type == "NPC":
            npcs = self._npc_repo.list_all()
            selected = self._ui.select_from_list(npcs, NPC.short_str, "Valj NPC")
            if not selected:
                return
            entity_id = selected.id
        else:
            groups = self._group_repo.list_all()
            selected = self._ui.select_from_list(groups, Group.display_str, "Valj grupp")
            if not selected:
                return
            entity_id = selected.name

        # Select claim
        claims = self._claim_repo.list_all()
        claim = self._ui.select_from_list(claims, Claim.short_str, "Valj CLAIM")
        if not claim:
            return

        # Get belief_in and openness
        belief_in = self._ui.prompt_float("belief_in")
        openness = self._ui.prompt_float("openness")

        if self._opinion_repo.create(entity_id, entity_type, claim.claim_id,
                                      belief_in, openness):
            self._ui.display.success(
                f"HAS_OPINION: {entity_id} -> {claim.claim_id} "
                f"(belief: {belief_in}, openness: {openness})"
            )
        else:
            self._ui.display.error(
                f"Kunde inte skapa koppling. Kontrollera att entiteten och CLAIM finns."
            )


class DeleteOpinionCommand(Command):
    def __init__(self, npc_repo: NPCRepo, group_repo: GroupRepo,
                 opinion_repo: OpinionRepo, ui: InputHelpers) -> None:
        self._npc_repo = npc_repo
        self._group_repo = group_repo
        self._opinion_repo = opinion_repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Ta bort en opinion-koppling"

    def execute(self) -> None:
        entity_type = self._ui.select_option(["NPC", "GROUP"], "Valj entitetstyp")
        if not entity_type:
            return

        if entity_type == "NPC":
            npcs = self._npc_repo.list_all()
            selected = self._ui.select_from_list(npcs, NPC.short_str, "Valj NPC")
            if not selected:
                return
            entity_id = selected.id
        else:
            groups = self._group_repo.list_all()
            selected = self._ui.select_from_list(groups, Group.display_str, "Valj grupp")
            if not selected:
                return
            entity_id = selected.name

        opinions = self._opinion_repo.list_for_entity(entity_id, entity_type)
        if not opinions:
            self._ui.display.error("Inga opinions hittades")
            return

        display_fn = lambda o: (
            f"{o.claim_id}: {o.claim_content[:40]}... "
            f"(belief: {o.belief_in}, openness: {o.openness})"
        )
        opinion = self._ui.select_from_list(opinions, display_fn, "Valj opinion")
        if not opinion:
            return

        if self._ui.confirm(f"Ta bort opinion for {opinion.claim_id}?"):
            if self._opinion_repo.delete(entity_id, entity_type, opinion.claim_id):
                self._ui.display.success("Opinion borttagen")
            else:
                self._ui.display.error("Kunde inte ta bort opinion")


class ListOpinionsCommand(Command):
    def __init__(self, npc_repo: NPCRepo, group_repo: GroupRepo,
                 opinion_repo: OpinionRepo, ui: InputHelpers) -> None:
        self._npc_repo = npc_repo
        self._group_repo = group_repo
        self._opinion_repo = opinion_repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Visa opinions for en entitet"

    def execute(self) -> None:
        entity_type = self._ui.select_option(["NPC", "GROUP"], "Valj entitetstyp")
        if not entity_type:
            return

        if entity_type == "NPC":
            npcs = self._npc_repo.list_all()
            selected = self._ui.select_from_list(npcs, NPC.short_str, "Valj NPC")
            if not selected:
                return
            entity_id = selected.id
        else:
            groups = self._group_repo.list_all()
            selected = self._ui.select_from_list(groups, Group.display_str, "Valj grupp")
            if not selected:
                return
            entity_id = selected.name

        opinions = self._opinion_repo.list_for_entity(entity_id, entity_type)
        if not opinions:
            self._ui.display.error("Inga opinions hittades")
            return

        self._ui.display.header(f"Opinions for {entity_id}")
        for o in opinions:
            content_preview = o.claim_content[:50] + "..." if len(o.claim_content) > 50 else o.claim_content
            print(f"  {o.claim_id}: {content_preview}")
            print(f"    belief_in: {o.belief_in}, openness: {o.openness}")
```

### 25. `db/commands/relation_commands.py`

```python
from .base import Command
from db.repositories import NPCRepo, GroupRepo, ClaimRepo, ConstantRepo, RelationRepo
from db.repositories.relation_repo import STRUCTURAL_RELATIONS
from db.models import NPC, Claim
from db.ui import InputHelpers


class CreateStructuralRelationCommand(Command):
    def __init__(self, npc_repo: NPCRepo, relation_repo: RelationRepo,
                 ui: InputHelpers) -> None:
        self._npc_repo = npc_repo
        self._relation_repo = relation_repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Skapa strukturell relation"

    def execute(self) -> None:
        npcs = self._npc_repo.list_all()

        print("\n--- Valj forsta NPC ---")
        npc_a = self._ui.select_from_list(npcs, NPC.short_str, "NPC A")
        if not npc_a:
            return

        print("\n--- Valj andra NPC ---")
        npc_b = self._ui.select_from_list(npcs, NPC.short_str, "NPC B")
        if not npc_b:
            return

        rel_types = list(STRUCTURAL_RELATIONS.keys())
        rel_type = self._ui.select_option(rel_types, "Relationstyp")
        if not rel_type:
            return

        secrecy = self._ui.prompt_float("secrecy", min_val=0.0, max_val=1.0)

        if self._relation_repo.create_structural(npc_a.name, npc_b.name, rel_type, secrecy):
            inverse = STRUCTURAL_RELATIONS[rel_type]
            self._ui.display.success(f"{npc_a.name} {rel_type} {npc_b.name}")
            self._ui.display.info(f"{npc_b.name} {inverse} {npc_a.name}")
            self._ui.display.info(f"secrecy: {secrecy}")
        else:
            self._ui.display.error("Ogiltig relationstyp")


class CreateAffectiveRelationCommand(Command):
    def __init__(self, npc_repo: NPCRepo, relation_repo: RelationRepo,
                 ui: InputHelpers) -> None:
        self._npc_repo = npc_repo
        self._relation_repo = relation_repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Skapa kanslomassig relation"

    def execute(self) -> None:
        npcs = self._npc_repo.list_all()

        print("\n--- Fran NPC ---")
        npc_from = self._ui.select_from_list(npcs, NPC.short_str, "Fran")
        if not npc_from:
            return

        print("\n--- Till NPC ---")
        npc_to = self._ui.select_from_list(npcs, NPC.short_str, "Till")
        if not npc_to:
            return

        affection = self._ui.prompt_float("affection (intern kansla)")
        demeanour = self._ui.prompt_float("demeanour (yttre uttryck)")

        if self._relation_repo.create_affective(npc_from.name, npc_to.name,
                                                  affection, demeanour):
            self._ui.display.success(f"{npc_from.name} -> {npc_to.name}")
            self._ui.display.info(f"AFFECTION: {affection}")
            self._ui.display.info(f"DEMEANOUR: {demeanour}")
        else:
            self._ui.display.error("Kunde inte skapa relation")


class CreateReferenceCommand(Command):
    def __init__(self, npc_repo: NPCRepo, claim_repo: ClaimRepo,
                 constant_repo: ConstantRepo, relation_repo: RelationRepo,
                 ui: InputHelpers) -> None:
        self._npc_repo = npc_repo
        self._claim_repo = claim_repo
        self._constant_repo = constant_repo
        self._relation_repo = relation_repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Skapa REFERENCE fran CLAIM"

    def execute(self) -> None:
        # Select source claim
        claims = self._claim_repo.list_all()
        source = self._ui.select_from_list(claims, Claim.short_str, "Valj CLAIM (kalla)")
        if not source:
            return

        # Select target type
        target_type = self._ui.select_option(
            ["NPC", "CLAIM", "OBJECT", "PLACE"], "Maltyp"
        )
        if not target_type:
            return

        # Select target
        if target_type == "NPC":
            npcs = self._npc_repo.list_all()
            npc = self._ui.select_from_list(npcs, NPC.short_str, "Valj NPC")
            if not npc:
                return
            target_name = npc.name
        elif target_type == "CLAIM":
            target_claim = self._ui.select_from_list(claims, Claim.short_str, "Valj CLAIM (mal)")
            if not target_claim:
                return
            target_name = target_claim.claim_id
        elif target_type == "OBJECT":
            objects = self._constant_repo.list_objects()
            obj = self._ui.select_from_list(objects, lambda o: o.name, "Valj OBJECT")
            if not obj:
                return
            target_name = obj.name
        else:  # PLACE
            places = self._constant_repo.list_places()
            place = self._ui.select_from_list(places, lambda p: p.name, "Valj PLACE")
            if not place:
                return
            target_name = place.name

        if self._relation_repo.create_reference(source.claim_id, target_name, target_type):
            self._ui.display.success(
                f"REFERENCE: {source.claim_id} -> [{target_type}] {target_name}"
            )
        else:
            self._ui.display.error("Kunde inte skapa referens")


class CreateMembershipCommand(Command):
    def __init__(self, npc_repo: NPCRepo, group_repo: GroupRepo,
                 relation_repo: RelationRepo, ui: InputHelpers) -> None:
        self._npc_repo = npc_repo
        self._group_repo = group_repo
        self._relation_repo = relation_repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Lagg till NPC i grupp"

    def execute(self) -> None:
        npcs = self._npc_repo.list_all()
        npc = self._ui.select_from_list(npcs, NPC.short_str, "Valj NPC")
        if not npc:
            return

        from db.models import Group
        groups = self._group_repo.list_all()
        group = self._ui.select_from_list(groups, Group.display_str, "Valj grupp")
        if not group:
            return

        if self._relation_repo.create_membership(npc.id, group.name):
            self._ui.display.success(f"{npc.name} ar nu medlem i {group.name}")
        else:
            self._ui.display.error("Kunde inte skapa medlemskap")


class DeleteMembershipCommand(Command):
    def __init__(self, npc_repo: NPCRepo, group_repo: GroupRepo,
                 relation_repo: RelationRepo, ui: InputHelpers) -> None:
        self._npc_repo = npc_repo
        self._group_repo = group_repo
        self._relation_repo = relation_repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Ta bort NPC fran grupp"

    def execute(self) -> None:
        from db.models import Group
        groups = self._group_repo.list_all()
        group = self._ui.select_from_list(groups, Group.display_str, "Valj grupp")
        if not group:
            return

        member_ids = self._relation_repo.list_members(group.name)
        if not member_ids:
            self._ui.display.error("Inga medlemmar i gruppen")
            return

        member = self._ui.select_option(member_ids, "Valj NPC att ta bort")
        if not member:
            return

        if self._relation_repo.delete_membership(member, group.name):
            self._ui.display.success(f"{member} borttagen fran {group.name}")
        else:
            self._ui.display.error("Kunde inte ta bort medlemskap")
```

---

### 26. `db/config.py`

```python
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver
from langchain_community.embeddings import OllamaEmbeddings


class Config:
    """Application configuration. Loads environment and creates shared resources."""

    def __init__(self, driver: Driver, embed_model: OllamaEmbeddings) -> None:
        self.driver = driver
        self.embed_model = embed_model

    @classmethod
    def from_env(cls) -> "Config":
        """Create Config from .env file."""
        load_dotenv()

        db_uri = os.getenv("NEO4J_URI")
        db_user = os.getenv("NEO4J_USER")
        db_password = os.getenv("NEO4J_PASSWORD")

        if not db_uri or not db_user or not db_password:
            raise RuntimeError(
                "Saknar NEO4J_URI, NEO4J_USER eller NEO4J_PASSWORD i .env"
            )

        driver = GraphDatabase.driver(db_uri, auth=(db_user, db_password))
        embed_model = OllamaEmbeddings(model="mxbai-embed-large")

        return cls(driver=driver, embed_model=embed_model)

    def close(self) -> None:
        """Close the database driver."""
        self.driver.close()
```

### 27. `db/app.py`

```python
from db.config import Config
from db.services import EmbeddingService
from db.repositories import (
    NPCRepo, GroupRepo, ClaimRepo, ConstantRepo, OpinionRepo, RelationRepo,
)
from db.commands import (
    CreateNPCCommand, EditNPCCommand, DeleteNPCCommand, ListNPCsCommand,
    CreateGroupCommand, DeleteGroupCommand, ListGroupsCommand,
    CreateClaimCommand, EditClaimCommand, DeleteClaimCommand, ListClaimsCommand,
    CreateObjectCommand, CreatePlaceCommand, ListConstantsCommand,
    CreateOpinionCommand, DeleteOpinionCommand, ListOpinionsCommand,
    CreateStructuralRelationCommand, CreateAffectiveRelationCommand,
    CreateReferenceCommand, CreateMembershipCommand, DeleteMembershipCommand,
)
from db.ui import InputHelpers, Menu, SubMenu


class App:
    """Main application. Wires dependencies and builds the menu tree."""

    def __init__(self, config: Config) -> None:
        # Services
        embedding = EmbeddingService(config.embed_model)

        # Repositories
        self._npc_repo = NPCRepo(config.driver)
        self._group_repo = GroupRepo(config.driver)
        self._claim_repo = ClaimRepo(config.driver, embedding)
        self._constant_repo = ConstantRepo(config.driver)
        self._opinion_repo = OpinionRepo(config.driver)
        self._relation_repo = RelationRepo(config.driver)

        # UI
        self._ui = InputHelpers()

    def run(self) -> None:
        ui = self._ui

        main_menu = Menu("Huvudmeny", [
            SubMenu("NPC", [
                CreateNPCCommand(self._npc_repo, ui),
                EditNPCCommand(self._npc_repo, ui),
                DeleteNPCCommand(self._npc_repo, ui),
                ListNPCsCommand(self._npc_repo, ui),
            ]),
            SubMenu("Grupper", [
                CreateGroupCommand(self._group_repo, ui),
                DeleteGroupCommand(self._group_repo, ui),
                ListGroupsCommand(self._group_repo, ui),
            ]),
            SubMenu("Claims", [
                CreateClaimCommand(self._claim_repo, ui),
                EditClaimCommand(self._claim_repo, ui),
                DeleteClaimCommand(self._claim_repo, ui),
                ListClaimsCommand(self._claim_repo, ui),
            ]),
            SubMenu("Konstanter (Objekt/Platser)", [
                CreateObjectCommand(self._constant_repo, ui),
                CreatePlaceCommand(self._constant_repo, ui),
                ListConstantsCommand(self._constant_repo, ui),
            ]),
            SubMenu("Opinions (kopplingar)", [
                CreateOpinionCommand(
                    self._npc_repo, self._group_repo,
                    self._claim_repo, self._opinion_repo, ui,
                ),
                DeleteOpinionCommand(
                    self._npc_repo, self._group_repo,
                    self._opinion_repo, ui,
                ),
                ListOpinionsCommand(
                    self._npc_repo, self._group_repo,
                    self._opinion_repo, ui,
                ),
            ]),
            SubMenu("Relationer", [
                CreateStructuralRelationCommand(
                    self._npc_repo, self._relation_repo, ui,
                ),
                CreateAffectiveRelationCommand(
                    self._npc_repo, self._relation_repo, ui,
                ),
                CreateReferenceCommand(
                    self._npc_repo, self._claim_repo,
                    self._constant_repo, self._relation_repo, ui,
                ),
                CreateMembershipCommand(
                    self._npc_repo, self._group_repo,
                    self._relation_repo, ui,
                ),
                DeleteMembershipCommand(
                    self._npc_repo, self._group_repo,
                    self._relation_repo, ui,
                ),
            ]),
        ])

        main_menu.run()
```

### 28. `db/main.py` (new entry point)

```python
from db.config import Config
from db.app import App


def main():
    config = Config.from_env()
    try:
        app = App(config)
        app.run()
    finally:
        config.close()


if __name__ == "__main__":
    main()
```

---

### 29. `__init__.py` files

All package `__init__.py` files are listed above in their respective sections. Additionally:

**`db/services/__init__.py`:**
```python
from .embedding import EmbeddingService

__all__ = ["EmbeddingService"]
```

**`db/commands/__init__.py`** and **`db/ui/__init__.py`** are already defined above.

---

## Running It

```bash
# From the repo root
python -m db.main
```

Or update `db/main.py` to use relative imports and run directly.

---

## How to Extend

### Adding a new entity type (e.g., EVENT):
1. Add `Event` dataclass to `db/models/event.py`
2. Add `EventRepo` to `db/repositories/event_repo.py`
3. Add commands to `db/commands/event_commands.py`
4. Register as `SubMenu("Event", [...])` in `db/app.py`

### Adding a new command to an existing entity:
1. Add command class to the relevant `commands/*.py` file
2. Register it in the relevant `SubMenu` in `db/app.py`

### Changing the schema (e.g., rename a property):
1. Update the relevant repository method
2. Update the relevant model dataclass
3. No other code changes needed

---

## Notes

- The old `db/builder.py` and `db/node_builder.py` can be kept alongside for backward compatibility, or removed once the new structure is validated.
- Swedish characters (å, ä, ö) are avoided in code identifiers but used in UI strings.
- The `Ellipsis` sentinel (`...`) is used in `ClaimRepo.update()` to distinguish "not provided" from "set to None/empty".
