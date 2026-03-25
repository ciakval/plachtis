# Crew Registration — Design Spec

**Date:** 2026-03-25
**Scope:** Crew registration for the race — `Person` MTI conversion, new `Crew`/`CrewMember` models, participant/boat lending, crew deadline, and CSV export.
**App:** `SkaRe` (existing Django app)
**Branch base:** `main`

---

## Overview

This spec covers two related changes:

1. **`Person` MTI conversion** — convert the existing abstract `Person` base class to a concrete model using Django multi-table inheritance, so that any participant subtype can be referenced by a single FK.
2. **Crew registration** — new `Crew` and `CrewMember` models linking a boat, a category, and up to five participants. Includes a lending mechanism, a separate registration deadline, and a CSV export.

---

## 1. `Person` MTI Conversion

### Current state

`Person` is an abstract model. Its fields (`first_name`, `last_name`, `nickname`, `date_of_birth`, `category`, `health_restrictions`, `dietary_restrictions`, `relevant_information`) are duplicated into each concrete subtype table (`RegularParticipant`, `IndividualParticipant`, `Organizer`).

### After conversion

`Person` becomes a concrete model with its own DB table. Each subtype retains only its subtype-specific fields plus a `person_ptr_id` PK/FK to `Person`.

```python
class Person(models.Model):
    # Common fields (same as before):
    first_name             = CharField(...)
    last_name              = CharField(...)
    nickname               = CharField(...)
    date_of_birth          = DateField(...)
    category               = CharField(...)   # auto-calculated scout category
    health_restrictions    = TextField(...)
    dietary_restrictions   = TextField(...)
    relevant_information   = TextField(...)

    # New field (moved here from RegularParticipant):
    visible_to = ManyToManyField(User, blank=True, related_name='borrowed_persons')

    class Meta:
        # validators and auto-category logic stay here

class RegularParticipant(Person):
    unit = FK(Unit, ...)
    # No longer has first_name, last_name, etc.

class IndividualParticipant(Person):
    entity     = OneToOneField(Entity, ...)
    boats_p550 = ...
    # etc.

class Organizer(Person):
    entity   = OneToOneField(Entity, ...)
    division = ...
    # etc.
```

### Data migration

A single data migration:
1. Create the `person` table.
2. For each existing row in `regularparticipant`, `individualparticipant`, `organizer`:
   - Insert a `Person` row with the common field values.
   - Set `person_ptr_id` on the subtype row to the new `Person` id.
3. Drop the common columns from each subtype table.

This migration must run before any crew-related migrations.

### Impact on existing code

- **Models:** Remove common field declarations from the three subtype classes; keep subtype-specific fields only.
- **Forms:** Field declarations that reference `first_name`, `last_name`, etc. now resolve through MTI — no form changes required as long as forms use `instance` correctly. Check `ModelForm` field lists to ensure common fields are still included.
- **Views:** Queries like `RegularParticipant.objects.all()` continue to work; Django MTI returns subtype instances with `person_ptr` populated. `select_related('person_ptr')` may be needed in performance-sensitive list views.
- **Admin:** `list_display` entries referencing common fields continue to work via MTI.

---

## 2. Data Model — Crew Registration

### New model: `Crew`

```python
class Crew(models.Model):
    CATEGORY_Q  = 'Q'
    CATEGORY_S  = 'S'
    CATEGORY_R  = 'R'
    CATEGORY_D  = 'D'
    CATEGORY_SN = 'SN'
    CATEGORY_DN = 'DN'
    CATEGORY_OZ = 'OZ'   # OŽ
    CATEGORY_OD = 'OD'
    CATEGORY_MS = 'MS'

    CATEGORY_CHOICES = [
        (CATEGORY_Q,  'Q – Žabičky a vlčata'),
        (CATEGORY_S,  'S – Skautky a skauti'),
        (CATEGORY_R,  'R – Rangers a roveři'),
        (CATEGORY_D,  'D – Dospělí'),
        (CATEGORY_SN, 'SN – Skautští námořníci'),
        (CATEGORY_DN, 'DN – Dospělí námořníci'),
        (CATEGORY_OZ, 'OŽ – Open Žáci'),
        (CATEGORY_OD, 'OD – Open Dospělí'),
        (CATEGORY_MS, 'MS – Modrá stuha'),
    ]

    boat       = FK(Boat, on_delete=PROTECT)
    category   = CharField(max_length=3, choices=CATEGORY_CHOICES)
    created_by = FK(User, on_delete=PROTECT)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('boat', 'category')
```

One boat can appear in at most one crew per category.

### New model: `CrewMember`

```python
class CrewMember(models.Model):
    ROLE_HELMSMAN = 'helmsman'
    ROLE_CREW     = 'crew'
    ROLE_CHOICES  = [
        (ROLE_HELMSMAN, 'Kormidelník'),
        (ROLE_CREW,     'Lodník'),
    ]

    crew        = FK(Crew, on_delete=CASCADE, related_name='members')
    role        = CharField(max_length=10, choices=ROLE_CHOICES)
    participant = FK(Person, on_delete=PROTECT)
```

Constraints enforced at the form/view level (not DB-level):
- Exactly one `ROLE_HELMSMAN` per crew.
- At most 4 `ROLE_CREW` members per crew (total max 5 including helmsman).
- A participant may not appear more than once in the same crew.
- A participant may appear in multiple crews (different boats or categories) — intentional, not restricted.

### Changes to `Boat`

Add two fields:

```python
willing_to_lend = BooleanField(default=False)
visible_to      = ManyToManyField(User, blank=True, related_name='borrowed_boats')
```

- `willing_to_lend`: public signal that the owner is open to lending; shown on the boat list.
- `visible_to`: users who can see and select this boat when registering a crew.

### Changes to `EventSettings`

```python
crew_registration_deadline = DateTimeField(null=True, blank=True)
```

Add `is_crew_registration_open()` and `get_crew_registration_deadline()` methods following the existing `is_registration_open()` / `is_editing_open()` pattern.

---

## 3. Permissions & Visibility

### Participants visible to a user

A `Person` is visible to a user if:
- The person is a `RegularParticipant` whose Unit's Entity the user owns or is an editor of, OR
- The person is an `IndividualParticipant` or `Organizer` whose Entity the user owns or is an editor of, OR
- The user is in `person.visible_to`.

### Boats visible to a user

A boat is visible to a user if:
- The user is `boat.created_by`, OR
- The user is in `boat.visible_to`.

InfoDesk group members can see all boats.

### Crew edit/delete

Only the crew's `created_by` or InfoDesk group members.

### Lending pages

- **`boats/<id>/lend/`**: accessible to `boat.created_by` or InfoDesk group members.
- **`persons/<id>/lend/`**: accessible to the owner/editors of the Person's underlying registration:
  - `RegularParticipant` → unit's Entity owner/editors
  - `IndividualParticipant` / `Organizer` → their own Entity owner/editors

---

## 4. Views & URLs

```
crews/register/          crew_register()        — create a new crew
crews/                   crew_list()            — list user's crews
crews/<id>/              crew_detail()          — view crew details
crews/<id>/edit/         crew_edit()            — edit crew (creator or InfoDesk)
crews/<id>/delete/       crew_delete()          — delete crew (creator or InfoDesk)

boats/<id>/lend/         boat_lend()            — manage boat.visible_to
persons/<id>/lend/       person_lend()          — manage person.visible_to

crews/export/csv/        crew_export_csv()      — staff-only CSV export
```

All crew views check `is_crew_registration_open()` before allowing create/edit. InfoDesk is exempt (matching boat behaviour).

---

## 5. Forms

### `CrewForm`

- `boat` — `ModelChoiceField` filtered to boats visible to the current user; `willing_to_lend=True` boats noted in the dropdown.
- `category` — `ChoiceField` using `Crew.CATEGORY_CHOICES`.

### `CrewMemberForm`

Used in an inline formset:
- `role` — `ChoiceField`; helmsman row renders role as read-only text.
- `participant` — `ModelChoiceField` over `Person`, filtered to persons visible to the current user; borrowed persons labeled "(zapůjčen)".

### Formset behaviour

- The helmsman row is always present and cannot be deleted.
- Up to 4 crew member rows, added via "+ Přidat lodníka" (JS-driven, same pattern as unit registration participant formset).
- Validation: exactly one helmsman, no duplicate participants, max 4 crew members.

### Language

All labels, help texts, and validation messages use `gettext_lazy()` / `{% trans %}`.

---

## 6. Templates

```
crews/register.html       — crew registration form
crews/list.html           — list of user's crews
crews/detail.html         — crew detail
crews/edit.html           — crew edit (same form, pre-filled)
crews/confirm_delete.html
boats/lend.html           — manage boat.visible_to (follows manage_editors.html pattern)
persons/lend.html         — manage person.visible_to (same pattern)
```

**Boat list (`boats/list.html`):** add "Willing to lend" column.

**Boat form (`boats/form.html`):** add `willing_to_lend` checkbox.

**Home page (`home.html`):** add "Register crew" and "My Crews" buttons. All strings use `{% trans %}` — unlike boat registration (intentionally Czech-only), crews follow the standard i18n pattern.

---

## 7. CSV Export

Staff-only, `crews/export/csv/`. One row per crew member. Exact columns to be confirmed with race organizers; minimum fields:

| Column | Source |
|---|---|
| Crew ID | `crew.id` |
| Category | `crew.category` |
| Boat sail number | `crew.boat.sail_number` |
| Boat name | `crew.boat.name` |
| Boat class | `crew.boat.boat_class.name` |
| Sail area | `crew.boat.sail_area` |
| Role | `crew_member.role` |
| Participant first name | `person.first_name` |
| Participant last name | `person.last_name` |
| Date of birth | `person.date_of_birth` |
| Scout category | `person.category` |
| Participant type | subtype name (RegularParticipant / IndividualParticipant / Organizer) |
| Unit name | unit name if RegularParticipant, else blank |

---

## 8. Admin

- `CrewAdmin`: list display shows boat, category, created_by, member count; inline `CrewMemberInline`.
- `Boat` admin: add `willing_to_lend` to `list_display` and fieldsets.
- `Person` admin (new): base admin for common fields; subtype admins inherit.

---

## 9. Migrations

| # | Content |
|---|---|
| N   | **Data migration:** convert `Person` abstract → concrete MTI; backfill `person` table from all three subtype tables; move `visible_to` M2M to `Person` |
| N+1 | Add `willing_to_lend`, `visible_to` to `Boat` |
| N+2 | Add `crew_registration_deadline` to `EventSettings` |
| N+3 | Create `Crew` and `CrewMember` tables |

Migration N is the critical one. It must be written and tested carefully against existing data.

---

## 10. Out of Scope

- Crew rule validation (sail area, participant age/count vs. category rules) — deferred.
- Lending beyond `visible_to` (time-limited loans, loan requests) — not needed.
- RFID / plavenky integration — separate module.
