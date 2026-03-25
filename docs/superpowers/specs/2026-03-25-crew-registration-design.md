# Crew Registration — Design Spec

**Date:** 2026-03-25
**Scope:** Crew registration for the race — `Person.visible_to` field, new `Crew`/`CrewMember` models, participant/boat lending, crew deadline, and CSV export.
**App:** `SkaRe` (existing Django app)
**Branch base:** `main`

---

## Overview

`Person` is already a concrete model using Django MTI — `RegularParticipant`, `IndividualParticipant`, and `Organizer` all inherit from it. No model conversion is needed.

This spec covers:
1. **`visible_to` on `Person` and `Boat`** — lending mechanism allowing owners to make their boats/participants visible to other users for crew assembly.
2. **Crew registration** — new `Crew` and `CrewMember` models linking a boat, a category, and up to five participants (one helmsman + up to four crew members).
3. **Crew deadline** — new `crew_registration_deadline` on `EventSettings`.
4. **CSV export** — staff-only export of crew data.

---

## 1. Data Model

### Changes to `Person`

```python
visible_to = models.ManyToManyField(User, blank=True, related_name='borrowed_persons')
```

Users in `visible_to` can see and select this person when registering a crew.

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

```python
willing_to_lend = models.BooleanField(default=False)
visible_to      = models.ManyToManyField(User, blank=True, related_name='borrowed_boats')
```

- `willing_to_lend`: public signal shown on the boat list.
- `visible_to`: users who can see and select this boat when registering a crew.

### Changes to `EventSettings`

```python
crew_registration_deadline = models.DateTimeField(null=True, blank=True)
```

Add `is_crew_registration_open()` and `get_crew_registration_deadline()` methods following the existing pattern.

---

## 2. Permissions & Visibility

### Persons visible to a user

A `Person` is visible to a user if any of the following:
- The person is a `RegularParticipant` whose Unit's Entity the user owns or is an editor of.
- The person is an `IndividualParticipant` or `Organizer` whose Entity the user owns or is an editor of.
- The user is in `person.visible_to`.

### Boats visible to a user

A boat is visible to a user if:
- The user is `boat.created_by`, OR
- The user is in `boat.visible_to`.

InfoDesk group members can see all boats (existing behaviour).

### Crew edit/delete

Only `crew.created_by` or InfoDesk group members.

### Lending pages access

- **`boats/<id>/lend/`**: `boat.created_by` or InfoDesk group members.
- **`persons/<id>/lend/`**: owner/editors of the Person's underlying registration — Unit's Entity for `RegularParticipant`, own Entity for `IndividualParticipant`/`Organizer`.

---

## 3. Views & URLs

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

All crew create/edit views check `is_crew_registration_open()` before proceeding; InfoDesk is exempt.

---

## 4. Forms

### `CrewRegistrationForm`

A plain `Form` (not `ModelForm`) that handles the full crew in one POST:

- `boat` — `ModelChoiceField`, queryset filtered to boats visible to the current user.
- `category` — `ChoiceField` using `Crew.CATEGORY_CHOICES`.
- `helmsman` — `ModelChoiceField` over `Person`, required; filtered to persons visible to the user.
- `crew_member_1` … `crew_member_4` — `ModelChoiceField` over `Person`, all optional; same queryset.

`clean()` validates no duplicate participants across all five fields.

The view saves by creating one `Crew` + up to 5 `CrewMember` rows inside `transaction.atomic()`.

### Language

All labels, help texts, and validation messages use `gettext_lazy()` / `{% trans %}`.

---

## 5. Templates

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

**Home page (`home.html`):** add "Register crew" and "My Crews" buttons. All strings use `{% trans %}`.

---

## 6. CSV Export

Staff-only, `crews/export/csv/`. One row per crew member. Minimum fields:

| Column | Source |
|---|---|
| Crew ID | `crew.id` |
| Category | `crew.category` |
| Boat sail number | `crew.boat.sail_number` |
| Boat name | `crew.boat.name` |
| Boat class | `crew.boat.boat_class.name` |
| Sail area | `crew.boat.sail_area` |
| Role | `crew_member.role` |
| First name | `person.first_name` |
| Last name | `person.last_name` |
| Date of birth | `person.date_of_birth` |
| Scout category | `person.category` |
| Participant type | subtype name |
| Unit name | unit name if RegularParticipant, else blank |

---

## 7. Admin

- `CrewAdmin`: list display shows boat, category, created_by, member count; inline `CrewMemberInline`.
- `Boat` admin: add `willing_to_lend` to `list_display` and fieldsets.

---

## 8. Migrations

| # | Content |
|---|---|
| 0019 | Add `visible_to` M2M to `Person` |
| 0020 | Add `willing_to_lend`, `visible_to` M2M to `Boat` |
| 0021 | Add `crew_registration_deadline` to `EventSettings` |
| 0022 | Create `Crew` and `CrewMember` tables |

---

## 9. Out of Scope

- Crew rule validation (sail area, participant age/count vs. category rules) — deferred.
- Lending beyond `visible_to` (time-limited loans, loan requests) — not needed.
- RFID / plavenky integration — separate module.
