# RFID Reader API Design

## Overview

A lightweight HTTP/JSON API allowing a physical RFID reader device to integrate with PlachtIS for on-water tracking. The reader has two card-reading modules and a display. All state lives in PlachtIS — the reader has no internal memory.

---

## Authentication

Every request must include:

```
Authorization: Bearer <key>
```

The key is configured via the `RFID_API_KEY` environment variable in `.env`. It is never stored in the database. If the header is missing or the key is wrong, PlachtIS returns HTTP 401 with a JSON error body.

All RFID API endpoints are CSRF-exempt (the reader is not a browser).

---

## Module IDs

The reader has two modules, identified by fixed string IDs:

| Module ID | State transition |
|---|---|
| `"departure"` | → `ON_WATER` |
| `"arrival"` | → `ASHORE` |

Any other module ID returns HTTP 400.

---

## Endpoints

### `GET api/rfid/alive/`

Heartbeat endpoint. The reader calls this repeatedly to update its display and detect connectivity loss.

**Response — scanning mode:**

```json
{
  "mode": "scanning",
  "boats_on_water": 12,
  "boats_ashore": 8,
  "timestamp": "2026-04-18T10:30:00Z"
}
```

**Response — pairing mode** (exactly one `SailTicket` has `pending_pairing=True`):

```json
{
  "mode": "pairing",
  "boats_on_water": 12,
  "boats_ashore": 8,
  "pairing_ticket": "P550-027",
  "timestamp": "2026-04-18T10:30:00Z"
}
```

`boats_on_water` and `boats_ashore` count only `SailTicket` records with a boat assigned (`boat__isnull=False`). Tickets with status `LOST` or no boat are excluded from both counts.

---

### `POST api/rfid/scan/`

Called whenever a card is scanned on either module.

**Request body:**

```json
{
  "module_id": "departure",
  "rfid_uid": "AABBCCDD"
}
```

#### Pairing mode responses

PlachtIS is in pairing mode when exactly one `SailTicket` has `pending_pairing=True`. In this mode, `module_id` is accepted but ignored — pairing always targets the pending ticket regardless of which module scanned the card.

**Success** — the scanned UID is not yet paired to any ticket; it is linked to the pending ticket, `pending_pairing` cleared:

```json
{
  "result": "ok",
  "ticket_code": "P550-027",
  "timestamp": "2026-04-18T10:30:00Z"
}
```

**Error** — the scanned UID is already paired to a (different) ticket:

```json
{
  "result": "error",
  "error": "already_paired",
  "timestamp": "2026-04-18T10:30:00Z"
}
```

#### Scanning mode responses

**Success** — UID found, state transition applied, `SailTicketLog` entry written:

```json
{
  "result": "ok",
  "ticket_code": "P550-027",
  "new_status": "on_water",
  "boat": {
    "name": "Rychlá Šipka",
    "sail_number": "123456",
    "class": "P550",
    "contact_person": "Jan Novák",
    "contact_phone": "+420 123 456 789",
    "harbor_number": "42",
    "harbor_name": "Přístav Sever"
  },
  "timestamp": "2026-04-18T10:30:00Z"
}
```

**Error responses** — all return HTTP 200 with `result: "error"`. The `ticket_code` and `boat` fields are included where available:

| `error` value | Meaning | `ticket_code` | `boat` |
|---|---|---|---|
| `"unknown_card"` | UUID not associated with any SailTicket | — | — |
| `"no_boat"` | Ticket exists but has no boat assigned | ✓ | — |
| `"already_on_water"` | Departure scanned but ticket already ON_WATER | ✓ | ✓ |
| `"already_ashore"` | Arrival scanned but ticket already ASHORE | ✓ | ✓ |
| `"lost"` | Ticket is marked as LOST | ✓ | ✓ (if assigned) |

Example error response:

```json
{
  "result": "error",
  "error": "already_on_water",
  "ticket_code": "P550-027",
  "boat": {
    "name": "Rychlá Šipka",
    "sail_number": "123456",
    "class": "P550",
    "contact_person": "Jan Novák",
    "contact_phone": "+420 123 456 789",
    "harbor_number": "42",
    "harbor_name": "Přístav Sever"
  },
  "timestamp": "2026-04-18T10:30:00Z"
}
```

Fields are omitted entirely when not available or blank (not set to `null`). This applies to both top-level response fields and boat sub-fields — e.g., `sail_number`, `harbor_number`, `harbor_name`, and `class` are omitted when the boat has no sail number, no harbor, or no boat class assigned.

---

## Logging

| Situation | Action |
|---|---|
| Successful state transition (ok scan) | `SailTicketLog` entry written (normal operation) |
| Duplicate/wrong-module scan (`already_on_water`, `already_ashore`) | `SailTicketLog` entry written with `note="Duplicate scan on <module_id> module"` |
| `unknown_card`, `no_boat`, `lost` | Response only — no log entry |
| Successful pairing | `rfid_uid` set, `pending_pairing` cleared — no separate log entry |
| Failed pairing (`already_paired`) | Response only — no log entry |

---

## HTTP Status Codes

| Code | When |
|---|---|
| `200` | All processed responses — both `ok` and `error` results. The reader always inspects the `result` field. |
| `400` | Malformed request: missing fields, invalid `module_id` |
| `401` | Missing or wrong API key |

---

## Code Structure

| Path | Purpose |
|---|---|
| `SkaRe/views/rfid_api.py` | Two views + `require_api_key` decorator |
| `SkaRe/urls.py` | Registers `api/rfid/alive/` and `api/rfid/scan/` |
| `.env` | `RFID_API_KEY=<key>` |
| `PlachtIS/settings.py` | Reads `RFID_API_KEY` from environment |

---

## Related

- UX gaps that must be addressed alongside this API: `2026-04-18-rfid-ux-gaps.md`
