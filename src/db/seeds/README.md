# Seeds

Seed-scripts for bulk-inserting plot data into the Neo4j graph database.

## Prerequisites

- Neo4j running (credentials in `.env`)
- Ollama running (for embedding generation)
- Python dependencies installed (`pip install -r requirements.txt`)

## How to run

Each seed is a standalone Python module. Run from the project root:

```bash
# Otrohetsmysteriet (24 claims, 7 NPCs, objects, places, opinions, references)
python -m db.seeds.otroheten
```

## How to re-run / reset

Seeds use `MERGE` for nodes (NPCs, objects, places, mystery) so they are
idempotent — running twice won't create duplicate nodes. However:

- **Claims** use `CREATE` (auto-incrementing IDs), so re-running will create
  duplicate claims. To start fresh, wipe the relevant data first:

```cypher
// Delete everything related to the Otroheten mystery
MATCH (c:CLAIM)-[:PART_OF]->(m:MYSTERY {name: "Otroheten"})
DETACH DELETE c;
MATCH (m:MYSTERY {name: "Otroheten"}) DELETE m;

// Or nuclear option: wipe the entire database
MATCH (n) DETACH DELETE n;
```

Then re-run the seed script.

## How to add a new mystery

1. Copy `otroheten.py` as a template
2. Replace the data (NPCs, claims, objects, places, opinions, references)
3. Change the mystery name
4. Run with `python -m db.seeds.<your_module_name>`

### Structure of a seed script

```python
# 1. Define NPCs (reuse existing ones or add new)
NPCS = [NPC(id="npc_xxx", name="...", age=30, personality="...", backstory="...")]

# 2. Define objects and places
OBJECTS = ["Kniv", "Dagbok"]
PLACES = ["Biblioteket", "Kallaren"]

# 3. Define claims: (key, content, type_or_none)
#    key is your local label (e.g. "M1"), mapped to real C-IDs at runtime
CLAIMS = [("M1", "Somebody did something.", "relation"), ...]

# 4. Define references: key -> [(target_name, target_type), ...]
REFERENCES = {"M1": [("Full NPC Name", "NPC"), ("Kniv", "OBJECT")]}

# 5. Define opinions: (npc_id, claim_key, belief_in, openness)
OPINIONS = [("npc_xxx", "M1", +1.0, -0.5), ...]
```

NPCs are matched by `id`, objects/places by `name`. Use full NPC names in
REFERENCES (e.g. "Lord Nils Wolmarsson", not "Nils").
