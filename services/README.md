Services CLI

Run from repository root.

Requirements
- Neo4j env vars in `.env`: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- Groq env var in `.env` for chat mode: `GROQ_API_KEY`
- Embedding model available in Ollama: `mxbai-embed-large`

Commands
- List NPCs:
  - `python -m services.cli --list-npcs`
- Build prompt/messages only (no Groq call):
  - `python -m services.cli --npc-id <NPC_ID> --question "..." --prompt-only`
- Full flow (RAG + Prompting + Groq):
  - `python -m services.cli --npc-id <NPC_ID> --question "..."`

Optional flags
- `--model llama-3.3-70b-versatile`
- `--top-k 3`
- `--min-refs 2`

Interactive mode
- If you omit `--npc-id` and/or `--question`, the CLI prompts for them.
