# Dynamic NPC Chat API

All endpoints (except health/docs) require header:

`x-api-key: <API_KEY>`

Base URL example: `http://localhost:8000`

## GET /health

Simple health check.

Response:

```json
{
  "status": "ok"
}
```

## POST /chat

Send a message to an NPC.

Request body fields:

- `npc_id` (string, required)
- `message` (string, required)
- `player_id` (string, optional)
- `conversation_id` (string, optional)

Rules:

- If `conversation_id` is missing, a new conversation is created.
- If `player_id` is provided and a new conversation is created, that conversation is automatically linked to the player.
- If `conversation_id` is provided, the API tries to continue that conversation.

Example request (new conversation, linked to player):

```json
{
  "npc_id": "npc_1",
  "message": "Vad vet du om torget?",
  "player_id": "player_1"
}
```

Example request (continue existing conversation):

```json
{
  "npc_id": "npc_1",
  "message": "Berätta mer.",
  "player_id": "player_1",
  "conversation_id": "conv_3"
}
```

Response:

```json
{
  "npc_id": "npc_1",
  "conversation_id": "conv_3",
  "response": "..."
}
```

## POST /conversations/summarize

Generate/update a short summary for one conversation.

Request:

```json
{
  "conversation_id": "conv_3"
}
```

Response:

```json
{
  "conversation_id": "conv_3",
  "summary": "...",
  "exchange_count": 6
}
```

## POST /players

Create a new player node.

Request:

```json
{
  "name": "Kalle",
  "appearance": "Lång, brun kappa"
}
```

Response:

```json
{
  "player_id": "player_4",
  "name": "Kalle",
  "appearance": "Lång, brun kappa"
}
```
