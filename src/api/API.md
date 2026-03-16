# Dynamic NPC Chat API

Base URL example: `http://localhost:8000`

## Authentication

All endpoints except `GET /health`, `/docs`, `/redoc`, and `/openapi.json` require:

```http
x-api-key: <API_KEY>
```

If the header is missing or wrong, the API returns:

```json
{
  "detail": "Forbidden"
}
```

## CORS

CORS is enabled with:

- `allow_origins=["*"]`
- `allow_methods=["*"]`
- `allow_headers=["*"]`
- `allow_credentials=false`

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

Request body:

- `npc_id` (string, required)
- `message` (string, required)
- `player_id` (string, optional)
- `conversation_id` (string, optional)

Behavior:

- If `conversation_id` is omitted, a new conversation may be created.
- If `player_id` is provided when a new conversation is created, that conversation is linked to the player.
- If `conversation_id` is provided, the API tries to continue that conversation.

Example request:

```json
{
  "npc_id": "npc_1",
  "message": "Vad vet du om torget?",
  "player_id": "player_1"
}
```

Example response:

```json
{
  "npc_id": "npc_1",
  "conversation_id": "conv_3",
  "response": "...",
  "used_claims": [
    "claim_12",
    "claim_19"
  ]
}
```

Notes:

- `conversation_id` may be `null` if no conversation id is returned.
- `used_claims` is always present and defaults to an empty list.
- If the service returns no result, the API responds with `response: "No response"`.

## POST /conversations/summarize

Generate or update a short summary for one conversation.

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

If the conversation does not exist, the API returns:

```json
{
  "detail": "Conversation not found"
}
```

## POST /players

Create a new player.

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

Validation errors:

```json
{
  "detail": "name cannot be empty"
}
```

```json
{
  "detail": "appearance cannot be empty"
}
```

## GET /players

Return all players.

Response:

```json
[
  {
    "player_id": "player_1",
    "name": "Anna",
    "appearance": "Röd kappa"
  },
  {
    "player_id": "player_2",
    "name": "Kalle",
    "appearance": "Lång, brun kappa"
  }
]
```

## DELETE /players/{player_id}

Delete one player by `player_id`.

Example request:

```http
DELETE /players/player_4
```

Response:

```json
{
  "player_id": "player_4",
  "deleted": true
}
```

Validation / not found responses:

```json
{
  "detail": "player_id cannot be empty"
}
```

```json
{
  "detail": "Player not found"
}
```

## GET /players/{player_id}/claims

Return all claims the player is aware of (connected via `AWARE_OF`).

Example request:

```http
GET /players/player_1/claims
```

Response:

```json
[
  {
    "claim_id": "C3",
    "content": "Erik stal från butiken",
    "type": null,
    "created_at": "2026-03-16T14:30:00.000000000Z",
    "npc_ids": ["npc_01", "npc_03"]
  },
  {
    "claim_id": "C7",
    "content": "Gudarna straffar syndare",
    "type": "relation",
    "created_at": "2026-03-16T15:12:00.000000000Z",
    "npc_ids": ["npc_02"]
  }
]
```

Notes:

- `type` may be `null` if the claim has no explicit type.
- `created_at` is the timestamp when the player first learned about the claim. May be `null` for older data.
- `npc_ids` lists all NPCs that have mentioned this claim to the player.
- Returns an empty list if the player has no `AWARE_OF` relationships.

Validation / not found responses:

```json
{
  "detail": "player_id cannot be empty"
}
```

```json
{
  "detail": "Player not found"
}
```

## POST /players/{player_id}/items/inspect

Inspect one item by `object_id` and mark it as seen for the player.

Request:

```json
{
  "object_id": "item_key"
}
```

Response:

```json
{
  "player_id": "player_1",
  "object_id": "item_key",
  "item_name": "Nyckel",
  "inspect_text": "En tung jarnnyckel med slottets sigill.",
  "pickupable": true,
  "seen": true
}
```

Validation / not found responses:

```json
{
  "detail": "player_id cannot be empty"
}
```

```json
{
  "detail": "object_id cannot be empty"
}
```

```json
{
  "detail": "Player not found"
}
```

```json
{
  "detail": "Item not found"
}
```

## POST /players/{player_id}/items/pickup

Try to pick up one item by `object_id`.

Request:

```json
{
  "object_id": "item_key"
}
```

Response when pickup succeeds:

```json
{
  "player_id": "player_1",
  "object_id": "item_key",
  "item_name": "Nyckel",
  "pickupable": true,
  "picked_up": true,
  "detail": "Item upplockat"
}
```

Response when the item exists but is not pickupable:

```json
{
  "player_id": "player_1",
  "object_id": "item_body",
  "item_name": "Kropp",
  "pickupable": false,
  "picked_up": false,
  "detail": "Det itemet kan inte plockas upp"
}
```

Validation / not found responses:

```json
{
  "detail": "player_id cannot be empty"
}
```

```json
{
  "detail": "object_id cannot be empty"
}
```

```json
{
  "detail": "Player not found"
}
```

```json
{
  "detail": "Item not found"
}
```

## Server errors

Unexpected backend errors are returned as `500` with:

```json
{
  "detail": "<error message>"
}
```
