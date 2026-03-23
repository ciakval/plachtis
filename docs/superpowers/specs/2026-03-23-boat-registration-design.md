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

`is_other` is a convention: at most one entry per category should have `is_other=True`. No DB unique constraint is enforced — admins are trusted not to mark multiple classes as "other" within the same category. Future phases may add a `clean()` validation if needed.

`__str__` returns `name`.

Initial data loaded via a data migration in `SkaRe`'s migration sequence (exact numbers assigned at generation time) with the following classes:
- **SAIL:** P550, 420, Cadet, Fireball, Evropa, Optimist, Finn, Other (sail)
- **OTHER:** paddleboard, windsurf, canoe, motorboat, seakayak, Other (other)

### `SailRegistryEntry`

Populated by CSV import via Django admin. The import runs inside a single database transaction: existing entries are deleted and new entries are bulk-created within the same transaction, so a malformed or empty CSV aborts without data loss.

`__str__` returns `sail_number`.

Exact CSV column mapping to be confirmed with Erik before implementation.

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

### `Boat`

`__str__` returns `"{sail_number} {name}"` if a sail number exists, otherwise just `name`. Existence is checked by truthiness (not `None` check), since `sail_number` is a blank-allowed `CharField`.

| Field | Type | Notes |
|-------|------|-------|
| `created_by` | `FK(User, CASCADE)` | Owner. CASCADE is intentional and consistent with `Entity.created_by` in the existing codebase. Deleting a user removes their boats. |
| `boat_class` | `FK(BoatClass, SET_NULL, null)` | |
| `class_supplement` | `CharField(200, blank)` | Free text clarification |
| `sail_number` | `CharField(50, blank)` | Optional |
| `name` | `CharField(200)` | Boat name (required) |
| `description` | `TextField(blank)` | Colours, notable features, etc. |
| `sail_area` | `DecimalField(null, blank)` | |
| `harbor_number` | `CharField(100, blank)` | Owner's club number |
| `harbor_name` | `CharField(200, blank)` | Owner's club name |
| `contact_person` | `CharField(200)` | |
| `contact_phone` | `CharField(50)` | |
| `created_at` | `DateTimeField(auto_now_add)` | |
| `updated_at` | `DateTimeField(auto_now)` | |

No deadline or editors field at this stage — deferred to the crew registration phase. In Phase 1, there is **no editing deadline** for boats: `can_be_edited` checks only ownership and group membership, not any time constraint.

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

The `InfoDesk` Django group is created via a data migration in the `SkaRe` migration sequence (exact number assigned at generation time) and assigned to users manually by a superuser.

`Boat` has a helper method:

```python
def can_be_edited(self, user):
    return self.created_by == user or user.groups.filter(name='InfoDesk').exists()
```

---

## Views & URLs

All views require login (`@login_required`). URL names follow the existing `SkaRe` namespace (e.g. `SkaRe:boat_list`, `SkaRe:boat_register`). URLs are registered under `/boats/` within `SkaRe/urls.py`. Templates live in `SkaRe/templates/SkaRe/boats/`.

| URL | View | Access |
|-----|------|--------|
| `/boats/` | List all boats | Authenticated |
| `/boats/register/` | Register new boat | Authenticated |
| `/boats/<id>/` | Boat detail | Authenticated |
| `/boats/<id>/edit/` | Edit boat | Creator or InfoDesk |
| `/boats/<id>/delete/` | Delete boat (confirm page) | Creator only |
| `/boats/api/sail-lookup/` | AJAX — sail registry lookup (`?q=<sail_number>`) | Authenticated |
| `/boats/api/my-unit/` | AJAX — prefill from user's unit | Authenticated |

The sail lookup endpoint accepts a query parameter `?q=` (not a URL path segment) to avoid routing issues with special characters in sail numbers. Lookup is case-insensitive (`iexact`).

---

## Forms & Templates

### `BoatForm`

Used for both register and edit views. Fields:
- `boat_class` — dropdown, grouped by category (SAIL / OTHER), ordered by `BoatClass.order`
- `class_supplement`, `sail_number`, `name`, `description`, `sail_area`
- `harbor_number`, `harbor_name`, `contact_person`, `contact_phone`

### JavaScript interactions

**Sail number prefill:** On blur of the `sail_number` field, a request is sent to `/boats/api/sail-lookup/?q=<sail_number>`. If found, the following fields are prefilled — but **only if the target field is currently empty** (prefill must never overwrite user-entered data, and must never inject an empty string into a required field):
- `boat_name` → `name`
- `class_name` → used to select the matching `boat_class` in the dropdown (best-effort match by name)
- `subtype` → `class_supplement`
- `sail_area` → `sail_area`
- `harbor_number` → `harbor_number`
- `harbor_name` → `harbor_name`
- `contact_person` → `contact_person`

If the sail number is not found in the registry, nothing happens silently.

**Unit prefill:** A "Fill from my unit" button appears on the form. On click, a request is sent to `/boats/api/my-unit/`. The endpoint returns the **most recently created** Unit registered by the current user (ordered by `entity.created_at` descending), or a 404 if the user has no registered Units. If found, the following fields are prefilled (only if currently empty):
- `scout_unit_evidence_id` → `harbor_number`
- `scout_unit_name` → `harbor_name`
- `contact_person_name` → `contact_person`

`contact_phone` has no prefill source from either the sail registry or the unit — users must always enter it manually.

The button is rendered conditionally in the template: the view passes a `has_unit` boolean context variable (True if the user has at least one registered Unit). This avoids an AJAX-on-load approach that would cause a visible flash.

### Templates

All templates extend `base.html`, use Czech UI strings (following existing i18n pattern), and live in `SkaRe/templates/SkaRe/boats/`:

- `SkaRe/templates/SkaRe/boats/list.html`
- `SkaRe/templates/SkaRe/boats/detail.html`
- `SkaRe/templates/SkaRe/boats/form.html` (shared register/edit)
- `SkaRe/templates/SkaRe/boats/confirm_delete.html`

### Django Admin

- `BoatClass` — registered with list display and ordering
- `SailRegistryEntry` — registered with a custom admin action for CSV import (atomic: clears and bulk-creates in one transaction; shows row count imported on success, error message on failure)
- `Boat` — registered for InfoDesk/superuser oversight

---

## Out of Scope (this phase)

- Boat deadline enforcement
- Boat editors / sharing / lending (deferred to crew registration phase)
- Crew registration
- Sailing passes (Plavenky) module
- Race data export
