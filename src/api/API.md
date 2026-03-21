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

## POST /users/register

Register a new user account.

Request body:

- `username` (string, required, minimum 3 characters)
- `password` (string, required, minimum 3 characters)

Example request:

```json
{
  "username": "john_doe",
  "password": "secret123"
}
```

Example response:

```json
{
  "user_id": "user_2",
  "username": "john_doe"
}
```

Validation / error responses:

```json
{
  "detail": "username cannot be empty"
}
```

```json
{
  "detail": "password cannot be empty"
}
```

```json
{
  "detail": "username must be at least 3 characters"
}
```

```json
{
  "detail": "password must be at least 3 characters"
}
```

If username already exists:

```json
{
  "detail": "Username already exists"
}
```

## POST /users/login

Login with username and password.

Request body:

- `username` (string, required)
- `password` (string, required)

Example request:

```json
{
  "username": "john_doe",
  "password": "secret123"
}
```

Example response:

```json
{
  "user_id": "user_2",
  "username": "john_doe"
}
```

Validation / error responses:

```json
{
  "detail": "username cannot be empty"
}
```

```json
{
  "detail": "password cannot be empty"
}
```

If credentials are invalid:

```json
{
  "detail": "Invalid username or password"
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

## POST /chat_static_npc

Send a message to a scripted NPC with fixed menu choices.

Request body:

- `npc_id` (string, required)
- `message` (string, optional, defaults to empty string)
- `player_id` (string, optional)

Behavior:

- If `message` is empty, the API returns the scripted menu text.
- If `message` is a whole number such as `1`, `2`, or `3`, the API returns the response for that choice.
- If `message` is not a whole number, the API returns `400`.

Example request to show menu:

```json
{
  "npc_id": "npc_terminal_1",
  "message": "",
  "player_id": "player_1"
}
```

Example menu response:

```json
{
  "npc_id": "npc_terminal_1",
  "response": "1. Få ledtråd\n2. Jag vet vem mördaren är\n3. Avsluta"
}
```

Example choice request:

```json
{
  "npc_id": "npc_terminal_1",
  "message": "1",
  "player_id": "player_1"
}
```

Example choice response:

```json
{
  "npc_id": "npc_terminal_1",
  "response": "Placeholder: val 1 valt. Här kan du senare ge en ledtråd."
}
```

Validation / error response for non-integer input:

```json
{
  "detail": "Ogiltigt val. Skicka ett heltal, till exempel 1, 2 eller 3."
}
```

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

Request body:

- `name` (string, required)
- `appearance` (string, required)
- `user_id` (string, optional) - User who owns this player. If omitted, defaults to admin user (user_1)

Example request (create player with specific user):

```json
{
  "name": "Kalle",
  "appearance": "Lång, brun kappa",
  "user_id": "user_2"
}
```

Example request (create player with default admin user):

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

Return all players, or players owned by a specific user if `user_id` is provided.

Query parameters:

- `user_id` (string, optional) - If provided, only returns players owned by this user

Example request (all players):

```http
GET /players
```

Example request (players for a specific user):

```http
GET /players?user_id=user_1
```

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

Validation / error responses:

```json
{
  "detail": "user_id cannot be empty"
}
```

If a non-existent user_id is provided, an empty list is returned.

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

## GET /players/{player_id}/clues

Return all clues the player has discovered so far.

This includes:

- all claims the player is aware of via `AWARE_OF`
- all items the player has seen via `SEEN_OBJECT`
- all items the player has picked up via `HAS_ITEM`

Example request:

```http
GET /players/player_1/clues
```

Response:

```json
{
  "claims": [
    {
      "claim_id": "C3",
      "content": "Erik stal från butiken",
      "type": null,
      "created_at": "2026-03-16T14:30:00.000000000Z",
      "npc_ids": ["npc_01", "npc_03"]
    }
  ],
  "items": [
    {
      "object_id": "item_key",
      "name": "Nyckel",
      "inspect_text": "En tung jarnnyckel med slottets sigill.",
      "pickupable": true,
      "created_at": "2026-03-16T14:35:00.000000000Z",
      "seen": true,
      "picked_up": true
    },
    {
      "object_id": "item_brev",
      "name": "Brev",
      "inspect_text": "Ett vikt brev med bruten forsegling.",
      "pickupable": true,
      "created_at": null,
      "seen": true,
      "picked_up": false
    }
  ]
}
```

Notes:

- `claims` uses the same shape as `GET /players/{player_id}/claims`.
- `items` combines seen and picked-up items into one list.
- Both `claims` and `items` are ordered by `created_at`, with older timestamped entries first and older untimestamped data last.
- `picked_up: true` implies the item is also considered seen.
- `created_at` may be `null` for older relationship data created before timestamps were added.
- Returns empty arrays if the player has not discovered any clues yet.

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
