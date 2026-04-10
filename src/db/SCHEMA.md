# Graph Database Schema

Reference for the node and relationship structure as implemented in the db builder code.

---

## Node Types

### USER
A user account that owns one or more player characters.

| Property | Type | Notes |
|----------|------|-------|
| `user_id` | string | Unique identifier (e.g. "user_1", "user_2") |
| `username` | string | Unique username for login |
| `password` | string | User password (should be hashed in production) |
| `locale` | string | Preferred language for the user. Currently `sv` or `en`; defaults to `sv` |

### NPC
A non-player character in the game world.

| Property | Type | Notes |
|----------|------|-------|
| `id` | string | Unique identifier (e.g. "npc_01") |
| `name` | string | Display name in Swedish (e.g. "Anna") |
| `name_en` | string? | English translation of `name` |
| `age` | int | |
| `personality` | string | Free-text personality description in Swedish |
| `personality_en` | string? | English translation of `personality` |
| `backstory` | string | Background/history of the character |
| `story_background` | string? | Story context in Swedish |
| `story_background_en` | string? | English translation of `story_background` |

### GROUP
A named group that NPCs can belong to (e.g. "Kyrkan", "Handelsgillet").

| Property | Type | Notes |
|----------|------|-------|
| `name` | string | Unique, capitalized (e.g. "Kyrkan") |

### CLAIM
A statement or piece of knowledge that exists in the world. CLAIMs are the central knowledge unit — NPCs and GROUPs form opinions about them.

| Property | Type | Notes |
|----------|------|-------|
| `claim_id` | string | Auto-generated: C1, C2, C3, ... |
| `content` | string | The statement in natural language in Swedish |
| `content_en` | string? | English translation of `content` |
| `type` | string? | Optional. Currently only value is `"relation"` (marks claims about relationships between entities) |
| `embedding` | float[] | Vector embedding of `content`, auto-generated on create/edit using mxbai-embed-large |
| `embedding_en` | float[]? | Vector embedding of `content_en`, auto-generated when English content exists |

### OBJECT
A thing in the world (e.g. "Svard", "Bok").

| Property | Type | Notes |
|----------|------|-------|
| `object_id` | string | Stable object identity, normally set explicitly when creating the object/item (e.g. `object_brev`, `item_key`) |
| `name` | string | Unique, capitalized |
| `name_en` | string? | English translation of `name` |

Some `OBJECT` nodes may also carry the `ITEM` label for gameplay interactions.

### ITEM
A gameplay-interactable object. Implemented as an extra label on `OBJECT` (`:OBJECT:ITEM`), so the same node can be referenced by claims and used in gameplay.

| Property | Type | Notes |
|----------|------|-------|
| `object_id` | string | Shared object identifier on the underlying `OBJECT` node |
| `name` | string | Shared with the underlying `OBJECT` node |
| `name_en` | string? | English translation of `name` |
| `inspect_text` | string | Text shown when the player inspects the item |
| `inspect_text_en` | string? | English translation of `inspect_text` |
| `pickupable` | bool | `true` if the player can pick it up |

### DOOR
A gameplay door represented as an `OBJECT` with the extra `DOOR` label.

| Property | Type | Notes |
|----------|------|-------|
| `object_id` | string | Stable door identifier |
| `name` | string | Door name |
| `name_en` | string? | English translation of `name` |
| `inspect_text` | string | Text shown when the player inspects the door |
| `inspect_text_en` | string? | English translation of `inspect_text` |
| `is_locked` | bool | Whether the door requires a condition before it can be opened |
| `lock_type` | string | `none`, `item`, or `code` |
| `unlock_code` | string? | Present only when `lock_type` is `code` |

### PLACE
A location in the world (e.g. "Torget", "Kyrkan").

| Property | Type | Notes |
|----------|------|-------|
| `name` | string | Unique, capitalized |
| `name_en` | string? | English translation of `name` |

### MYSTERY
An organizational grouping for the database builder. Used to categorize claims by plot thread / storyline (e.g. "Mordet", "Otroheten"). Has no impact on the RAG pipeline — purely a structural aid for the person building the database.

| Property | Type | Notes |
|----------|------|-------|
| `name` | string | Unique, capitalized |

---

## Relationships (Edges)

### HAS_OPINION (NPC/GROUP --> CLAIM)

The core knowledge relationship. Represents that an NPC or GROUP holds a subjective position on a CLAIM. This is the primary way all NPC knowledge is encoded — facts, beliefs, feelings, and relationship knowledge all go through claims.

| Property | Type | Range | Meaning |
|----------|------|-------|---------|
| `belief_in` | float | -1.0 to 1.0 | How strongly the entity internally believes the claim. +1 = fully believes, -1 = fully disbelieves |
| `openness` | float | -1.0 to 1.0 | How willing the entity is to express this opinion. +1 = freely shares, -1 = keeps completely secret |
| `prefix` | string? | - | Swedish prefix text rendered before the claim |
| `prefix_en` | string? | - | English translation of `prefix` |
| `suffix` | string? | - | Swedish suffix text rendered after the claim |
| `suffix_en` | string? | - | English translation of `suffix` |
| `overwrite_suffix` | string? | - | Swedish suffix used when the player already knows the claim |
| `overwrite_suffix_en` | string? | - | English translation of `overwrite_suffix` |

```
(NPC:Anna) -[:HAS_OPINION {belief_in: 0.8, openness: -0.5}]-> (CLAIM:C3 "Erik stal fran butiken")
```
Anna strongly believes Erik stole, but keeps it mostly to herself.

```
(GROUP:Kyrkan) -[:HAS_OPINION {belief_in: 1.0, openness: 1.0}]-> (CLAIM:C7 "Gudarna straffar syndare")
```
The church fully believes and openly preaches this.

An NPC can inherit group opinions via MEMBER_OF (see below), but the traversal logic for that lives in the RAG/query layer, not in the builder.

#### How belief_in and openness are used at query time (render_claim in ragtest.py)

**belief_in** controls the prefix:
- |value| 0.7-1.0 -> no prefix modification
- |value| 0.3-0.6 -> prefix "Det ar mojligt att "
- |value| 0.0-0.2 -> prefix "Det ar oklart ifall "

**openness** (same sign as belief_in) controls the suffix:
- |value| 0.7-1.0 -> "vilket du ar bekvam att prata om"
- |value| 0.3-0.6 -> no suffix
- |value| 0.0-0.2 -> "vilket du undviker att prata om"

**openness** (opposite sign from belief_in) — NPC denies what they believe:
- |value| 0.7-1.0 -> "men det ar du oppen med att neka"
- |value| 0.3-0.6 -> "men det nekar du"
- |value| 0.0-0.2 -> "vilket du undviker att prata om"

---

### Structural Relations (NPC --> NPC)

Direct edges representing the **objective social/family structure** between two NPCs. These are ground-truth facts about the world, independent of what any NPC knows or believes. They are not used by the RAG pipeline directly — NPC knowledge about relationships is mediated through CLAIMs (see "How NPC-to-NPC Knowledge Works" below).

Created **bidirectionally** — when you create A PARENT_TO B, the code also creates B CHILD_TO A.

| Relation | Inverse | Symmetric? |
|----------|---------|------------|
| `SIBLING_WITH` | `SIBLING_WITH` | yes |
| `FRIENDS_WITH` | `FRIENDS_WITH` | yes |
| `DATING` | `DATING` | yes |
| `MARRIED_TO` | `MARRIED_TO` | yes |
| `DIVORCED_FROM` | `DIVORCED_FROM` | yes |
| `PARENT_TO` | `CHILD_TO` | no |
| `CHILD_TO` | `PARENT_TO` | no |

All structural relations have one property:

| Property | Type | Range | Meaning |
|----------|------|-------|---------|
| `secrecy` | float | 0.0 to 1.0 | How secret this relationship is. 0 = public knowledge, 1 = completely hidden |

```
(NPC:Anna) -[:SIBLING_WITH {secrecy: 0.0}]-> (NPC:Erik)
(NPC:Erik) -[:SIBLING_WITH {secrecy: 0.0}]-> (NPC:Anna)
```

```
(NPC:Anna) -[:PARENT_TO {secrecy: 0.9}]-> (NPC:Lilla_Erik)
(NPC:Lilla_Erik) -[:CHILD_TO {secrecy: 0.9}]-> (NPC:Anna)
```

---

### REFERENCE (CLAIM --> anything)

Links a CLAIM to the entities it **mentions or is about**. No properties. Also used to chain claims together — the RAG layer traverses `[:REFERENCE*0..5]` paths to follow reference chains between claims.

Valid targets:

| From | To | Example |
|------|----|---------|
| CLAIM | NPC | Claim "Anna hatar Erik" references both Anna and Erik |
| CLAIM | CLAIM | Claim C5 references Claim C3 (C5 builds on or relates to C3) |
| CLAIM | OBJECT | Claim "Svardet ar stulet" references the sword |
| CLAIM | PLACE | Claim "Torget ar farligt" references the square |

```
(CLAIM:C3 "Anna hatar Erik") -[:REFERENCE]-> (NPC:Anna)
(CLAIM:C3 "Anna hatar Erik") -[:REFERENCE]-> (NPC:Erik)
```

```
(CLAIM:C5 "Erik ar opålitlig") -[:REFERENCE]-> (CLAIM:C3 "Erik stal fran butiken")
```
C5 references C3 as supporting context. At query time, the RAG layer follows these chains to gather related information.

REFERENCE has no properties. It marks "this claim talks about / builds on that entity."

---

### MEMBER_OF (NPC --> GROUP)

Membership relation. No properties.

```
(NPC:Anna) -[:MEMBER_OF]-> (GROUP:Kyrkan)
```

At query time (RAG layer), this is used to let NPCs inherit group-level opinions:
```
(NPC) -[:MEMBER_OF]-> (GROUP) -[:HAS_OPINION]-> (CLAIM)
```

---

### HAS_CHARACTER (USER --> PLAYER)

Links a user to a player character they own. No properties.

```
(USER:user_1) -[:HAS_CHARACTER]-> (PLAYER:player_1)
```

A user can own multiple characters, and this relationship is used to manage character ownership and access control.

---

### HAS_ITEM (PLAYER --> OBJECT:ITEM)

Tracks that the player has picked up an item.

| Property | Type | Notes |
|----------|------|-------|
| `created_at` | datetime | When the player first picked up the item |

```
(PLAYER)-[:HAS_ITEM {created_at: datetime()}]->(OBJECT:ITEM)
```

### SEEN_OBJECT (PLAYER --> OBJECT:ITEM)

Tracks that the player has inspected or otherwise seen an item. This is intended for gameplay gating such as unlocking future interactions or clues.

| Property | Type | Notes |
|----------|------|-------|
| `created_at` | datetime | When the player first saw the item |

```
(PLAYER)-[:SEEN_OBJECT {created_at: datetime()}]->(OBJECT:ITEM)
```

### AWARE_OF (PLAYER --> CLAIM)

Tracks that the player has learned about a claim during gameplay (typically from a conversation with an NPC). Created automatically when an NPC references claims in a chat response.

| Property | Type | Notes |
|----------|------|-------|
| `created_at` | datetime | When the player first learned about the claim |
| `npc_ids` | string[] | List of NPC ids that have mentioned this claim to the player |

```
(PLAYER)-[:AWARE_OF {created_at: datetime(), npc_ids: ["npc_01", "npc_03"]}]->(CLAIM)
```

The `npc_ids` list grows over time — if multiple NPCs mention the same claim, each NPC id is appended (deduplicated). This enables the RAG pipeline to mark claims as "already mentioned" per-NPC, so NPCs avoid repeating information.

### REQUIRES_ITEM (DOOR --> ITEM)

Used when a locked door requires a specific item to be opened. No properties.

```
(OBJECT:DOOR)-[:REQUIRES_ITEM]->(OBJECT:ITEM)
```

### HAS_OPENED (PLAYER --> DOOR)

Tracks that a specific player has opened a specific door.

| Property | Type | Notes |
|----------|------|-------|
| `created_at` | datetime | When the player first opened the door |

```
(PLAYER)-[:HAS_OPENED {created_at: datetime()}]->(OBJECT:DOOR)
```

### SEEN_DOOR (PLAYER --> DOOR)

Tracks that a player has encountered or attempted to open a door.

| Property | Type | Notes |
|----------|------|-------|
| `created_at` | datetime | When the player first saw or tried the door |

```
(PLAYER)-[:SEEN_DOOR {created_at: datetime()}]->(OBJECT:DOOR)
```

### DOOR_ENTERED (PLAYER --> DOOR)

Tracks each successful door passage for a player. Unlike `HAS_OPENED`, this is append-only and a new relationship is created every time the player goes through the door.

| Property | Type | Notes |
|----------|------|-------|
| `created_at` | datetime | When the player went through the door |

```
(PLAYER)-[:DOOR_ENTERED {created_at: datetime()}]->(OBJECT:DOOR)
```

---

### PART_OF (CLAIM --> MYSTERY)

Organizational relation for the database builder. Links a claim to a mystery / plot thread. No properties. Not used by the RAG pipeline.

```
(CLAIM:C3 "Erik stal fran butiken") -[:PART_OF]-> (MYSTERY:Mordet)
(CLAIM:C12 "Lilla Erik ar Annas son") -[:PART_OF]-> (MYSTERY:Otroheten)
```

A claim can be part of multiple mysteries, or none at all.

---

## How NPC-to-NPC Knowledge Works

Feelings and relationship knowledge about other NPCs are modeled **through claims**, not through direct edges. This means the same claim-mediated system handles everything: facts, beliefs, emotions, and relationships.

### Example: Anna hates Erik

```
(Anna) -[:HAS_OPINION {belief_in: 0.9, openness: -0.8}]-> (CLAIM:C3 "Jag hatar Erik") -[:REFERENCE]-> (Erik)
```
- `belief_in: 0.9` — she strongly feels this way
- `openness: -0.8` — she keeps it secret (opposite sign = she'd deny it if asked)
- The CLAIM has `type: "relation"` to mark it as relational knowledge
- REFERENCE links the claim to Erik so the RAG layer can find it when queries involve Erik

### Example: Multiple NPCs, different views

```
(Anna) -[:HAS_OPINION {belief_in: 1.0, openness: 0.3}]-> (CLAIM:C12 "Lilla Erik ar Annas son")
(Sven) -[:HAS_OPINION {belief_in: 0.2, openness: 0.0}]-> (CLAIM:C12)
(CLAIM:C12) -[:REFERENCE]-> (Anna)
(CLAIM:C12) -[:REFERENCE]-> (Lilla_Erik)
```
Anna knows it's true but rarely mentions it. Sven barely believes the rumor and won't bring it up.

### Example: Claim chains via REFERENCE

```
(Anna) -[:HAS_OPINION]-> (CLAIM:C5 "Erik ar opålitlig")
(CLAIM:C5) -[:REFERENCE]-> (CLAIM:C3 "Erik stal fran butiken")
(CLAIM:C3) -[:REFERENCE]-> (NPC:Erik)
(CLAIM:C3) -[:REFERENCE]-> (OBJECT:Brod)
```
At query time, the RAG layer follows `[:REFERENCE*0..5]` from C5, finds C3, and includes both in the context. The `render_claim` function applies belief_in/openness rendering to each claim individually, then combines them.

### Structural relations vs claim-mediated knowledge

Structural relations (SIBLING_WITH, etc.) represent **ground truth** — the actual state of the world. They exist as a separate layer for world-building purposes. What NPCs actually know and communicate is always mediated through claims and HAS_OPINION.

```
GROUND TRUTH:   (Anna) -[:PARENT_TO {secrecy: 1.0}]-> (Lilla_Erik)
NPC KNOWLEDGE:  (Anna) -[:HAS_OPINION]-> (CLAIM "Lilla Erik ar min son") -[:REFERENCE]-> (Lilla_Erik)
```

---

## RAG Query Pipeline (ragtest.py)

The query pipeline uses only HAS_OPINION, MEMBER_OF, and REFERENCE. Here's how:

1. **Find accessible claims** — get all CLAIMs reachable via `(NPC)-[:HAS_OPINION]->(CLAIM)` or `(NPC)-[:MEMBER_OF]->(GROUP)-[:HAS_OPINION]->(CLAIM)`
2. **Semantic search** — vector similarity on CLAIM embeddings, filtered to accessible claims
3. **Find constants** — follow `[:REFERENCE]` from top claims to find referenced NPCs, OBJECTs, PLACEs
4. **Find relation claims** — find `type: "relation"` claims that reference 2+ of the discovered constants
5. **Build reference chains** — traverse `[:REFERENCE*0..5]` between claims
6. **Render** — apply `render_claim()` with belief_in/openness to generate text for LLM prompt
7. **Separate** — split into "DIN KUNSKAP OM FRAGAN" (non-relation) and "DINA RELATIONER" (relation claims)

---

## Design Decisions

- **No negative field on CLAIMs** — instead of storing a negated version of a claim and swapping text when `belief_in < 0`, we simply create a separate claim for the opposite belief. This keeps the data model simpler and more flexible.
- **No affective relations** (AFFECTION/DEMEANOUR) — feelings about other NPCs are modeled through claims. A claim like "Jag hatar Erik" with appropriate belief_in/openness values captures the same information, and the RAG pipeline already knows how to render it.
- **No BASED_ON** — REFERENCE (CLAIM -> CLAIM) covers claim-to-claim links. The RAG layer traverses reference chains, which serves the same purpose as logical dependency.
- **HAS_OPINION instead of BELIEF/STANCE** — Mark's schema used two separate edges. We use one edge with two properties (belief_in + openness), which is functionally equivalent and simpler.

---

## Visual Summary

```
                  ┌──────────────────────────────────────────────────┐
                  │              STRUCTURAL RELATIONS                │
                  │  SIBLING_WITH, FRIENDS_WITH, DATING,            │
                  │  MARRIED_TO, DIVORCED_FROM,                     │
                  │  PARENT_TO / CHILD_TO                           │
                  │  (bidirectional, secrecy property)              │
                  │  [ground truth only, not used by RAG]           │
   ┌─────┐       └────────────────────┬─────────────────────────────┘
   │ NPC │◄───────────────────────────┘
   └──┬──┘
      │
      ├──[:MEMBER_OF]──────────────────► ┌───────┐
      │                                  │ GROUP │
      │                                  └───┬───┘
      │                                      │
      │    ┌─────────────────────────────────┘
      │    │  [:HAS_OPINION {belief_in, openness}]
      │    │
      ├────┤
      │    │
      │    ▼
      │  ┌───────────────────────────────────┐
       │  │ CLAIM                             │
       │  │ claim_id, content, type,          │
       │  │ embedding                         │
       │  └──────────┬───────────────────┬────┘
       │             │                   │
       │        [:REFERENCE]        [:REFERENCE]
       │             │                   │
       │             ▼                   ▼
       │     ┌──────────────┐   ┌──────────────┐
       │     │ NPC / CLAIM  │   │ OBJECT/PLACE │
       │     └──────────────┘   └──────────────┘
       │
       └──[:HAS_OPINION {belief_in, openness}]──► CLAIM
                                                    │
                                               [:PART_OF]
                                               (optional)
                                                    │
                                                    ▼
                                              ┌───────────┐
                                              │  MYSTERY   │
                                              │ (builder   │
                                              │  only)     │
                                              └───────────┘
```
