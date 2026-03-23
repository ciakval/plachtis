# Boat Registration — Design Spec

**Date:** 2026-03-23
**Scope:** Phase 1 of BOATS.md — boat registration only (crews and sailing passes are separate phases)
**App:** `SkaRe` (existing Django app)

---

## Overview

Any authenticated PlachtIS user can register boats for the event. Info-desk organizers can edit any boat. All authenticated users can view all boats. A sail number registry (imported from CSV) enables prefilling boat details; the registering user's Unit details can also be used to prefill owner fields.

---

## Data Models

### `BoatClass`

Admin-managed list of boat classes. Stored in DB so administrators can update it without code changes.

| Field | Type | Notes |
|-------|------|-------|
| `name` | `CharField(100)` | e.g. "P550", "Cadet", "canoe" |
| `category` | `TextChoices(SAIL, OTHER)` | Groups sailing vs. non-sailing |
| `is_other` | `BooleanField` | Marks the catch-all "Other" per category |
| `order` | `PositiveIntegerField` | Controls display order in dropdowns |

Initial data loaded via a data migration with the following classes:
- **SAIL:** P550, 420, Cadet, Fireball, Evropa, Optimist, Finn, Other (sail)
- **OTHER:** paddleboard, windsurf, canoe, motorboat, seakayak, Other (other)

### `SailRegistryEntry`

Populated by CSV import via Django admin. Cleared and replaced on each re-import.

| Field | Type | Notes |
|-------|------|-------|
| `sail_number` | `CharField(50, unique)` | Lookup key |
| `boat_name` | `CharField(200, blank)` | |
| `class_name` | `CharField(100, blank)` | Raw string from CSV |
| `subtype` | `CharField(200, blank)` | Maps to `class_supplement` on prefill |
| `sail_area` | `DecimalField(null, blank)` | |
| `harbor_number` | `CharField(100, blank)` | |
| `harbor_name` | `CharField(200, blank)` | |
| `contact_person` | `CharField(200, blank)` | |

Exact CSV column mapping to be confirmed with Erik before implementation.

### `Boat`

| Field | Type | Notes |
|-------|------|-------|
| `created_by` | `FK(User, CASCADE)` | Owner |
| `boat_class` | `FK(BoatClass, SET_NULL, null)` | |
| `class_supplement` | `CharField(200, blank)` | Free text clarification |
| `sail_number` | `CharField(50, blank)` | Optional |
| `name` | `CharField(200)` | Boat name |
| `description` | `TextField(blank)` | Colours, notable features, etc. |
| `sail_area` | `DecimalField(null, blank)` | |
| `harbor_number` | `CharField(100, blank)` | Owner's club number |
| `harbor_name` | `CharField(200, blank)` | Owner's club name |
| `contact_person` | `CharField(200)` | |
| `contact_phone` | `CharField(50)` | |
| `created_at` | `DateTimeField(auto_now_add)` | |
| `updated_at` | `DateTimeField(auto_now)` | |

No deadline or editors field at this stage — deferred to the crew registration phase.

---

## Permissions & Access Control

| Action | Who |
|--------|-----|
| Register new boat | Any authenticated user |
| View boat list and detail | Any authenticated user |
| Edit boat | Creator **or** member of `InfoDesk` group |
| Delete boat | Creator only |
| AJAX sail lookup | Any authenticated user |
| AJAX unit prefill | Any authenticated user |

The `InfoDesk` Django group is created via a data migration and assigned to users manually by a superuser.

`Boat` has a helper method:

```python
def can_be_edited(self, user):
    return self.created_by == user or user.groups.filter(name='InfoDesk').exists()
```

---

## Views & URLs

All views require login (`@login_required`). URLs are registered under `/boats/`.

| URL | View | Access |
|-----|------|--------|
| `/boats/` | List all boats | Authenticated |
| `/boats/register/` | Register new boat | Authenticated |
| `/boats/<id>/` | Boat detail | Authenticated |
| `/boats/<id>/edit/` | Edit boat | Creator or InfoDesk |
| `/boats/<id>/delete/` | Delete boat (confirm page) | Creator only |
| `/boats/api/sail-lookup/<sail_number>/` | AJAX — sail registry lookup | Authenticated |
| `/boats/api/my-unit/` | AJAX — prefill from user's unit | Authenticated |

---

## Forms & Templates

### `BoatForm`

Used for both register and edit views. Fields:
- `boat_class` — dropdown, grouped by category (SAIL / OTHER), ordered by `BoatClass.order`
- `class_supplement`, `sail_number`, `name`, `description`, `sail_area`
- `harbor_number`, `harbor_name`, `contact_person`, `contact_phone`

### JavaScript interactions

**Sail number prefill:** On blur of the `sail_number` field, a request is sent to `/boats/api/sail-lookup/<sail_number>/`. If found, `boat_name`, `class_name`, `subtype` (→ `class_supplement`), `sail_area`, `harbor_number`, `harbor_name`, and `contact_person` are prefilled. If not found, nothing happens silently.

**Unit prefill:** A "Fill from my unit" button appears on the form. On click, a request is sent to `/boats/api/my-unit/`. If the user has a registered Unit, `harbor_number` (`scout_unit_evidence_id`), `harbor_name` (`scout_unit_name`), and `contact_person` (`contact_person_name`) are prefilled. The button is hidden if the user has no unit.

### Templates

All templates extend `base.html` and use Czech UI strings (following existing i18n pattern):

- `SkaRe/boats/list.html`
- `SkaRe/boats/detail.html`
- `SkaRe/boats/form.html` (shared register/edit)
- `SkaRe/boats/confirm_delete.html`

### Django Admin

- `BoatClass` — registered with list display and ordering
- `SailRegistryEntry` — registered with a custom admin action for CSV import (clears existing entries, bulk-creates from uploaded file)
- `Boat` — registered for InfoDesk/superuser oversight

---

## Out of Scope (this phase)

- Boat deadline enforcement
- Boat editors / sharing / lending (deferred to crew registration phase)
- Crew registration
- Sailing passes (Plavenky) module
- Race data export

