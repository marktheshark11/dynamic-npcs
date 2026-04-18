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
- `locale` (string, optional, `sv` or `en`, defaults to `sv`)

Example request:

```json
{
  "username": "john_doe",
  "password": "secret123",
  "locale": "en"
}
```

Example response:

```json
{
  "user_id": "user_2",
  "username": "john_doe",
  "locale": "en",
  "created_at": "2026-04-17T10:15:00Z"
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

```json
{
  "detail": "locale must be 'sv' or 'en'"
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
  "username": "john_doe",
  "locale": "en",
  "created_at": "2026-04-17T10:15:00Z"
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

## PATCH /users/{user_id}/locale

Update a user's preferred locale.

Request body:

- `locale` (string, required, `sv` or `en`)

Example request:

```json
{
  "locale": "en"
}
```

Example response:

```json
{
  "user_id": "user_2",
  "locale": "en"
}
```

Validation / error responses:

```json
{
  "detail": "user_id cannot be empty"
}
```

```json
{
  "detail": "locale must be 'sv' or 'en'"
}
```

If the user does not exist:

```json
{
  "detail": "User not found"
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

## GET /forms/{form_id}

Return a form definition with all questions ordered by `order`.

Query parameters:

- `locale` (string, optional, `sv` or `en`, defaults to `sv`)

When `locale=en`, the API returns `name_en` / `question_en` when present, and falls back to Swedish text when English text is missing.

The response also includes optional localized form description text and optional scale metadata for numeric questions.

Example response:

```json
{
  "form_id": "player_profile",
  "name": "Player Profile",
  "description": "Answer the questions based on how you felt at the end of the game.",
  "questions": [
    {
      "question_id": "q_name",
      "question": "What is your name?",
      "value_type": "string",
      "order": 1
    },
    {
      "question_id": "q_age",
      "question": "How old are you?",
      "value_type": "int",
      "order": 2,
      "scale_min": 1,
      "scale_max": 7,
      "min_label": "Not at all",
      "max_label": "A lot"
    }
  ]
}
```

English example:

`GET /forms/player_profile?locale=en`

```json
{
  "form_id": "player_profile",
  "name": "Player Profile",
  "description": "Answer the questions based on how you felt at the end of the game.",
  "questions": [
    {
      "question_id": "q_name",
      "question": "What is your name?",
      "value_type": "string",
      "order": 1
    },
    {
      "question_id": "q_age",
      "question": "How old are you?",
      "value_type": "int",
      "order": 2
    }
  ]
}
```

If the form does not exist:

```json
{
  "detail": "Form not found"
}
```

## POST /players/{player_id}/forms/{form_id}

Save one current answer per question for a player. The request must contain answers for all questions in the form.

For `int` questions with `scale_min` / `scale_max`, submitted answers must fall within that range.

Request body:

- `answers` (array, required)
  - `question_id` (string, required)
  - `answer` (string, required)

Example request:

```json
{
  "answers": [
    {
      "question_id": "q_name",
      "answer": "Elin"
    },
    {
      "question_id": "q_age",
      "answer": "27"
    }
  ]
}
```

Example response:

```json
{
  "player_id": "player_1",
  "form_id": "player_profile",
  "saved_answers": [
    {
      "question_id": "q_name",
      "value_type": "string",
      "raw_answer": "Elin"
    },
    {
      "question_id": "q_age",
      "value_type": "int",
      "raw_answer": "27"
    }
  ]
}
```

Possible validation errors:

```json
{
  "detail": "All form questions must be answered; missing question_ids: q_age"
}
```

```json
{
  "detail": "answer for question_id 'q_age' must be an integer"
}
```

## GET /players/{player_id}/forms/{form_id}

Return a form definition together with the player's currently saved answers.

This endpoint uses the player's locale to choose Swedish or English text, with fallback to Swedish if English text is missing.

Example response:

```json
{
  "form_id": "player_profile",
  "name": "Player Profile",
  "description": "Answer the questions based on how you felt at the end of the game.",
  "questions": [
    {
      "question_id": "q_name",
      "question": "What is your name?",
      "value_type": "string",
      "order": 1,
      "answer": "Elin"
    },
    {
      "question_id": "q_age",
      "question": "How old are you?",
      "value_type": "int",
      "order": 2,
      "scale_min": 1,
      "scale_max": 7,
      "min_label": "Not at all",
      "max_label": "A lot",
      "answer": "27"
    }
  ]
}
```

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
- `1` returns the current hint text for the player.
- `2` returns a closing text string from the commissioner.
- `3` starts a multi-step accusation flow and returns a numbered list of hardcoded suspects.
- After the suspect list is shown, send another message with the suspect number to complete the accusation.
- When the accusation is completed, the backend marks the player as having finished the game and stores whether the accusation was correct.
- Players with completed games are blocked from future `/chat_static_npc` calls.
- If a number is expected but the input is invalid, the API returns `400`.

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
  "response": "1. Få ledtråd\n2. Avsluta\n3. Jag vet vem mördaren är, jag vill anklaga den och sedan avsluta spelet",
  "game_completed": false,
  "accused_correct_npc": null,
  "accused_npc_id": null,
  "completed_at": null
}
```

Example choice request:

```json
{
  "npc_id": "npc_terminal_1",
  "message": "3",
  "player_id": "player_1"
}
```

Example choice response:

```json
{
  "npc_id": "npc_terminal_1",
   "response": "Vem anklagar du?\n1. Beatrice Wolmarsson\n2. Wilhelm Wolmarsson\n3. Pamela Smith Wolmarsson\n4. Herr Bergström\n5. Mariana Martinsson\nSvara med siffran för den person du vill anklaga.",
  "game_completed": false,
  "accused_correct_npc": null,
  "accused_npc_id": null,
  "completed_at": null
}
```

Example follow-up request in the accusation flow:

```json
{
  "npc_id": "npc_terminal_1",
  "message": "1",
  "player_id": "player_1"
}
```

Example accusation result:

```json
{
  "npc_id": "npc_terminal_1",
  "response": "Ja. Det stämmer med det du har lagt fram.'",
  "game_completed": true,
  "accused_correct_npc": true,
  "accused_npc_id": "npc_beatrice",
  "completed_at": "2026-03-27T12:34:56Z"
}
```

Validation / error response for non-integer input:

```json
{
  "detail": "Ogiltigt val. Välj en kandidat genom att skicka en siffra mellan 1 och 5."
}
```

Validation / error response for a completed player:

```json
{
  "detail": "Spelet är redan avslutat för den här spelaren."
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

The backend stores `created_at` and initializes game state fields on the `PLAYER` node.

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

Return all active players, or active players owned by a specific user if `user_id` is provided.

Query parameters:

- `user_id` (string, optional) - If provided, only returns players owned by this user

Completed players are excluded from this list.

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

## GET /players/{player_id}/analytics

Return a structured analytics summary for one player.

This is the main read model for current player state and aggregates data from:

- owning user metadata (without password)
- player profile and completion state
- discovered clues
- saved form answers
- conversation counts and per-NPC counts

Example request:

```http
GET /players/player_1/analytics
```

Example response:

```json
{
  "player_id": "player_1",
  "locale": "sv",
  "user": {
    "user_id": "user_2",
    "username": "john_doe",
    "locale": "sv",
    "created_at": "2026-04-17T10:15:00Z"
  },
  "profile": {
    "name": "Kalle",
    "appearance": "Lång, brun kappa",
    "created_at": "2026-04-17T10:15:00Z",
    "completed_at": null
  },
  "game": {
    "has_completed_game": false,
    "accused_correct_npc": null,
    "accused_npc_id": null
  },
  "progress": {
    "claims_known": 3,
    "items_seen": 2,
    "items_picked_up": 1,
    "doors_seen": 1,
    "doors_opened": 0,
    "forms_answered": 1,
    "conversation_count": 2,
    "exchange_count": 7,
    "unique_npcs_spoken_to": 2
  },
  "clues": {
    "claims": [],
    "items": [],
    "doors": []
  },
  "forms": [
    {
      "form_id": "player_profile",
      "name": "Player Profile",
      "description": "Answer the questions based on how you felt at the end of the game.",
      "answers": [
        {
          "question_id": "q_name",
          "question": "What is your name?",
          "value_type": "string",
          "order": 1,
          "raw_answer": "Elin",
          "answer_text": "Elin",
          "answer_int": null
        }
      ]
    }
  ],
  "conversation_metrics": {
    "by_npc": [
      {
        "npc_id": "npc_1",
        "conversation_count": 2
      }
    ],
    "conversations": [
      {
        "conversation_id": "conv_3",
        "npc_id": "npc_1",
        "player_id": "player_1",
        "created_at": "2026-04-17T10:20:00Z",
        "ended_at": null,
        "summary": null,
        "summary_updated_at": null,
        "exchange_count": 4
      }
    ]
  }
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

## GET /players/{player_id}/analytics/timeline

Return a chronological event stream for one player.

This endpoint is intended for behavior analysis and export. It includes events such as:

- `player_created`
- `claim_learned`
- `item_seen`
- `item_picked_up`
- `door_seen`
- `door_opened`
- `door_entered`
- `conversation_started`
- `exchange_recorded`
- `form_answer_saved`
- `game_completed`

Example request:

```http
GET /players/player_1/analytics/timeline
```

Example response:

```json
{
  "player_id": "player_1",
  "locale": "sv",
  "event_count": 4,
  "events": [
    {
      "type": "player_created",
      "timestamp": "2026-04-17T10:15:00Z",
      "payload": {
        "player_id": "player_1"
      }
    },
    {
      "type": "conversation_started",
      "timestamp": "2026-04-17T10:20:00Z",
      "payload": {
        "conversation_id": "conv_3",
        "npc_id": "npc_1"
      }
    },
    {
      "type": "exchange_recorded",
      "timestamp": "2026-04-17T10:20:05Z",
      "payload": {
        "conversation_id": "conv_3",
        "exchange_id": "conv_3_ex_1",
        "npc_id": "npc_1",
        "turn_index": 1,
        "player_text": "Vad vet du om torget?",
        "npc_text": "..."
      }
    },
    {
      "type": "form_answer_saved",
      "timestamp": null,
      "payload": {
        "form_id": "player_profile",
        "form_name": "Player Profile",
        "question_id": "q_name",
        "question": "What is your name?",
        "raw_answer": "Elin",
        "answer_text": "Elin",
        "answer_int": null
      }
    }
  ]
}
```

Notes:

- Some events may have `timestamp: null` if the source data does not currently store timestamps.
- `exchange_recorded` currently includes both `player_text` and `npc_text` for each turn.

## GET /players/{player_id}/analytics/export

Return both the summary and timeline in one export-friendly JSON payload for a single player.

Example request:

```http
GET /players/player_1/analytics/export
```

Example response shape:

```json
{
  "exported_at": "2026-04-17T10:30:00Z",
  "user": {
    "user_id": "user_2",
    "username": "john_doe",
    "locale": "sv",
    "created_at": "2026-04-17T10:15:00Z"
  },
  "player_id": "player_1",
  "summary": {
    "player_id": "player_1"
  },
  "timeline": {
    "player_id": "player_1",
    "events": []
  }
}
```

This is the recommended endpoint if you want to download one player's analytics and process it elsewhere.

## GET /analytics/export

Return analytics exports grouped by owning user.

Query parameters:

- `user_id` (string, optional) - if provided, only exports players owned by that user

Example request:

```http
GET /analytics/export
```

Example request for one user's players:

```http
GET /analytics/export?user_id=user_2
```

Example response shape:

```json
{
  "exported_at": "2026-04-17T10:30:00Z",
  "user_count": 1,
  "users": [
    {
      "user": {
        "user_id": "user_2",
        "username": "john_doe",
        "locale": "sv",
        "created_at": "2026-04-17T10:15:00Z"
      },
      "player_count": 2,
      "players": [
        {
          "player_id": "player_1",
          "summary": {
            "player_id": "player_1"
          },
          "timeline": {
            "player_id": "player_1",
            "events": []
          }
        }
      ]
    }
  ]
}
```

This is the recommended endpoint for downloading JSON to analyze with pandas or other external tooling.

The `user` block intentionally excludes the user's password.

If `user_id` is provided but no players belong to that user, the endpoint returns an empty `users` list.

## GET /users/{user_id}/analytics/export

Return analytics exports grouped under one specific user.

Example request:

```http
GET /users/user_2/analytics/export
```

This returns the same grouped shape as `GET /analytics/export?user_id=user_2`.

Validation response:

```json
{
  "detail": "user_id cannot be empty"
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
    "important": true,
    "created_at": "2026-03-16T14:30:00.000000000Z",
    "npc_ids": ["npc_01", "npc_03"]
  },
  {
    "claim_id": "C7",
    "content": "Gudarna straffar syndare",
    "type": "relation",
    "important": false,
    "created_at": "2026-03-16T15:12:00.000000000Z",
    "npc_ids": ["npc_02"]
  }
]
```

Notes:

- `type` may be `null` if the claim has no explicit type.
- `important` indicates whether the claim is marked as an important clue.
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
- all doors the player has tried to open via `SEEN_DOOR`
- all doors the player has opened via `HAS_OPENED`

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
      "important": true,
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
  ],
  "doors": [
    {
      "object_id": "door_vault",
      "name": "Valvdörr",
      "inspect_text": "En tung järndörr med komplicerat lås.",
      "lock_type": "item",
      "created_at": "2026-03-16T14:40:00.000000000Z",
      "seen": true,
      "opened": false
    }
  ]
}
```

Notes:

- `claims` uses the same shape as `GET /players/{player_id}/claims`.
- `items` combines seen and picked-up items into one list.
- `doors` combines seen and opened doors into one list.
- Both `claims` and `items` are ordered by `created_at`, with older timestamped entries first and older untimestamped data last.
- `doors` is also ordered by `created_at` with the same fallback rules.
- `picked_up: true` implies the item is also considered seen.
- `opened: true` implies the door is also considered seen.
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

## POST /players/{player_id}/doors/open

Try to open one door by `object_id`.

For unlocked doors, opening always succeeds.
For locked doors:

- `lock_type: item` requires the player to already have the required item
- `lock_type: code` requires the request to include the correct `code`

Any open attempt also marks the door as seen for the player, even if the opening fails.

Request for a normal door or key-locked door:

```json
{
  "object_id": "door_vault"
}
```

Request for a code-locked door:

```json
{
  "object_id": "door_vault",
  "code": "1234"
}
```

Response when opening succeeds:

```json
{
  "player_id": "player_1",
  "object_id": "door_vault",
  "door_name": "Valvdörr",
  "opened": true,
  "already_open": false,
  "lock_type": "item",
  "required_item_id": "item_vault_key",
  "detail": "Dörren öppnades med nyckel."
}
```

Response when the player does not have the right key:

```json
{
  "player_id": "player_1",
  "object_id": "door_vault",
  "door_name": "Valvdörr",
  "opened": false,
  "already_open": false,
  "lock_type": "item",
  "required_item_id": "item_vault_key",
  "detail": "Du har inte rätt nyckel."
}
```

Response when the code is wrong:

```json
{
  "player_id": "player_1",
  "object_id": "door_panel",
  "door_name": "Kodpanel",
  "opened": false,
  "already_open": false,
  "lock_type": "code",
  "required_item_id": null,
  "detail": "Fel kod."
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
  "detail": "Door not found"
}
```

## Server errors

Unexpected backend errors are returned as `500` with:

```json
{
  "detail": "<error message>"
}
```
