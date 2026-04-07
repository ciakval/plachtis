# Sail Ticket Bulk Creation — Design Spec

**Date:** 2026-04-07
**Status:** Approved

## Overview

Replace the current incremental `ticket_create_bulk` flow with a full-reset bulk creation that:
- Deletes all existing SailTickets (and cascades to SailTicketLogs)
- Assigns ticket codes derived from each boat's sail number where possible
- Fills remaining slots with sequential unused numbers
- Requires an explicit confirmation step before any destructive action

This operation is expected to be performed once, after all boats have registered.

---

## Numbering Algorithm

Applies independently to each of the three boat categories: **P550**, **SAIL** (other sailboats), **OTHER** (other boats).

### Step 1 — Extract sail numbers

For each boat in the category:
- Strip all non-digit characters from `boat.sail_number`.
- If the result is non-empty, the boat is **numbered**; its ticket number is the extracted integer.
- If the result is empty (no digits, or `sail_number` is blank), the boat is **unnumbered**.

### Step 2 — Conflict resolution (first-come-first-served)

Iterate boats ordered by `pk` (registration order). If two boats produce the same numeric value:
- The first boat claims that number.
- Subsequent boats with the same number are demoted to unnumbered.

### Step 3 — Sequential fill for unnumbered boats and reserves

Count up from 1. Skip any number already claimed by a sail-numbered boat. Assign the next available number to each unnumbered boat in order, then to each reserve ticket, until all slots are filled.

### SPARE category

Completely independent of the above. Always generates `SPARE-1`, `SPARE-2`, …, `SPARE-N`. No boats are ever associated with SPARE tickets.

### Code format

```
{PREFIX}-{number}
```

No zero-padding. Examples:
- `P550-1234` (from sail number `CZE 1234`)
- `P550-1` (sequential fill)
- `SPARE-5`

Prefixes: `P550`, `SAIL`, `OTHER`, `SPARE` (unchanged from current `COLOR_PREFIX` mapping).

---

## View & Form Changes

### `BulkTicketCreateForm` (unchanged)

Four fields: `p550_reserves`, `sail_reserves`, `other_reserves`, `spare_count`.

### `ticket_create_bulk` view — three states

**GET**
Renders the form with a summary of registered boats per category (same as today).

**POST step 1** — `confirm` field absent
1. Validate the form.
2. Call `_build_ticket_plan(boats, reserve_counts, spare_count)` to compute the full plan.
3. Render the template in "preview mode" (plan in context). No DB changes.

**POST step 2** — `confirm=1` present
1. Re-validate the form.
2. Recompute the plan from current DB state (never use cached/session data).
3. Inside `transaction.atomic()`:
   - `SailTicket.objects.all().delete()` (SailTicketLog rows cascade).
   - `SailTicket.objects.bulk_create(plan_tickets)`.
4. Redirect to `ticket_list` with a success message.

### `_build_ticket_plan` helper

Extracted as a standalone function (not a view). Accepts:
- `boats`: queryset of **all** `Boat` objects with `boat_class` pre-fetched (no filtering by existing ticket assignment — this is a full reset)
- `reserve_counts`: dict mapping `SailTicket.Color` → int
- `spare_count`: int

Returns a list of unsaved `SailTicket` instances (no PKs yet), suitable for `bulk_create`.

This separation makes the logic independently testable without HTTP.

---

## Template & UX

### `create_bulk.html` — preview mode (when `plan` in context)

1. **Danger alert** (Bootstrap `alert-danger`):
   > "This will permanently delete all N existing tickets and their logs. This cannot be undone."
2. **Per-category tables** listing:
   - Ticket code
   - Boat assigned (or "Reserve — no boat")
   - Source of number ("From sail number" vs "Sequential")
3. **"Back" link** — returns to GET form (user re-enters values).
4. **"Confirm and create" button** — red (`btn-danger`), submits `confirm=1` with hidden form fields.

The existing "N tickets already exist" warning is superseded by the danger alert in preview mode.

---

## Testing

New tests in `SkaRe/tests/` (new file `test_ticket_bulk.py` to keep scope isolated):

### Unit tests for `_build_ticket_plan`

- Boat with sail number `CZE 1234` → code `P550-1234`
- Boat with no sail number → sequential code `P550-1`
- Two boats with same numeric sail number → first gets the number, second gets sequential
- Unnumbered boats + reserves share the sequential pool correctly
- Reserves fill in after unnumbered boats
- SPARE tickets are always `SPARE-1..N`, never have a boat

### Integration tests for `ticket_create_bulk` view

- GET renders form, no DB changes
- POST step 1 renders preview (plan visible in response, no DB changes)
- POST step 2 deletes existing tickets and creates new ones
- POST step 2 with zero existing tickets works (zero-delete path)
- POST step 2 conflict case: two boats same numeric sail number — one gets the number, other gets sequential

---

## What Is Not Changing

- `_boat_color()` helper — used as-is
- `COLOR_PREFIX` dict — used as-is
- All other ticket views (`ticket_list`, `ticket_detail`, `ticket_set_status`, etc.)
- URL routing — no new URLs added
- `BulkTicketCreateForm` fields
