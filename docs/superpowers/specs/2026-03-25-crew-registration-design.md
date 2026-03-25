# Crew Registration — Design Spec

**Date:** 2026-03-25
**Scope:** Crew registration for the race — new `Crew`/`CrewMember` models, participant/boat lending, crew deadline, and CSV export.
**App:** `SkaRe` (existing Django app)
**Branch base:** `main`

---

## Overview

This spec covers the implementation of crew registration in PlachtIS. Crews link a registered boat, a race category, and up to five participants (one helmsman + up to four crew members). The feature also introduces a lending mechanism so that boat owners and unit leaders can make their boats and participants visible to other users for crew assembly.

---

## 1. Data Model

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

    boat       = models.ForeignKey(Boat, on_delete=models.PROTECT)
    category   = models.CharField(max_length=3, choices=CATEGORY_CHOICES)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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

    crew        = models.ForeignKey(Crew, on_delete=models.CASCADE, related_name='members')
    role        = models.CharField(max_length=10, choices=ROLE_CHOICES)
    participant = models.ForeignKey(RegularParticipant, on_delete=models.PROTECT)
```

Constraints enforced at the form/view level (not DB-level):
- Exactly one `ROLE_HELMSMAN` per crew.
- At most 4 `ROLE_CREW` members per crew (total max 5 including helmsman).
- A participant may not appear more than once in the same crew.
- A participant may appear in multiple crews (different boats or categories) — this is intentional and not restricted.

### Changes to `Boat`

Add two fields:

```python
willing_to_lend = models.BooleanField(default=False)
visible_to      = models.ManyToManyField(User, blank=True, related_name='borrowed_boats')
```

- `willing_to_lend`: public signal that the owner is open to lending; shown on the boat list.
- `visible_to`: users who can see and select this boat when registering a crew.

### Changes to `RegularParticipant`

```python
visible_to = models.ManyToManyField(User, blank=True, related_name='borrowed_participants')
```

Users in `visible_to` can see and select this participant when registering a crew.

### Changes to `EventSettings`

```python
crew_registration_deadline = models.DateTimeField(null=True, blank=True)
```

When set, crew registration and editing is closed after this datetime. The existing `is_registration_open()` / `is_editing_open()` pattern is followed: add `is_crew_registration_open()` and `get_crew_registration_deadline()` methods.

---

## 2. Permissions & Visibility

### What a user can see when registering a crew

**Boats visible to user:**
- Boats the user created (`boat.created_by == request.user`), OR
- Boats where the user is in `boat.visible_to`.

InfoDesk group members can see all boats (same as existing boat edit permission).

**Participants visible to user:**
- `RegularParticipant`s whose Unit's Entity the user owns or is an editor of, OR
- `RegularParticipant`s where the user is in `participant.visible_to`.

### Crew edit/delete
Only the crew's `created_by` or InfoDesk group members can edit or delete a crew.

### Lending pages
Access to the lending management pages is restricted to:
- **`boats/<id>/lend/`**: the boat's `created_by` or InfoDesk group members.
- **`participants/<id>/lend/`**: owners/editors of the participant's Unit's Entity.

---

## 3. Views & URLs

```
crews/register/          crew_register()        — create a new crew
crews/                   crew_list()            — list user's crews
crews/<id>/              crew_detail()          — view crew details
crews/<id>/edit/         crew_edit()            — edit crew (creator or InfoDesk)
crews/<id>/delete/       crew_delete()          — delete crew (creator or InfoDesk)

boats/<id>/lend/         boat_lend()            — manage boat.visible_to
participants/<id>/lend/  participant_lend()      — manage participant.visible_to

crews/export/csv/        crew_export_csv()      — staff-only CSV export
```

All crew views check `is_crew_registration_open()` before allowing create/edit (InfoDesk group is exempt from the deadline check, matching boat behaviour).

---

## 4. Forms

### `CrewForm`

Top-level form fields:
- `boat` — `ModelChoiceField` filtered to boats visible to the current user; `willing_to_lend=True` boats are visually grouped/noted in the dropdown.
- `category` — `ChoiceField` using `Crew.CATEGORY_CHOICES`.

### `CrewMemberForm`

Used in an inline formset (one form per member):
- `role` — `ChoiceField`; the helmsman row renders role as read-only text, not an editable dropdown.
- `participant` — `ModelChoiceField` filtered to participants visible to the current user; borrowed participants labeled "(zapůjčen)".

### Formset behaviour

- The helmsman row is always present and cannot be deleted.
- Up to 4 crew member rows can be added via "+ Přidat lodníka" (JS-driven extra form reveal, same pattern as participant formset in unit registration).
- Validation checks: exactly one helmsman, no duplicate participants, max 4 crew members.

### Language

All form labels, help texts, button labels, and validation messages are wrapped in `gettext_lazy()` / `{% trans %}`. Model `verbose_name` and `verbose_name_plural` use `gettext_lazy()`.

---

## 5. Templates

```
crews/register.html     — crew registration form
crews/list.html         — list of user's crews
crews/detail.html       — crew detail view
crews/edit.html         — crew edit form (same form as register, pre-filled)
crews/confirm_delete.html
boats/lend.html         — manage boat.visible_to (follows manage_editors.html pattern)
participants/lend.html  — manage participant.visible_to (same pattern)
```

**Boat list changes (`boats/list.html`):**
- Add a "Willing to lend" column showing a checkmark or icon for `willing_to_lend=True` boats.

**Boat form changes (`boats/form.html`):**
- Add `willing_to_lend` checkbox field to the existing boat form.

**Home page (`home.html`):**
- Add "Register crew" and "My Crews" buttons in the authenticated section. All strings use `{% trans %}` — unlike boat registration (which is intentionally Czech-only), crews follow the standard i18n pattern.

---

## 6. CSV Export

Staff-only view at `crews/export/csv/`. One row per crew member. Exact columns to be confirmed with race organizers; minimum fields:

| Column | Source |
|---|---|
| Crew ID | `crew.id` |
| Category | `crew.category` |
| Boat sail number | `crew.boat.sail_number` |
| Boat name | `crew.boat.name` |
| Boat class | `crew.boat.boat_class.name` |
| Sail area | `crew.boat.sail_area` |
| Role | `crew_member.role` |
| Participant first name | `participant.first_name` |
| Participant last name | `participant.last_name` |
| Date of birth | `participant.date_of_birth` |
| Scout category | `participant.category` |
| Unit name | `participant.unit.scout_unit_name` |

---

## 7. Admin

- `CrewAdmin`: list display shows boat, category, created_by, member count; inline `CrewMemberInline`.
- `Boat` admin: add `willing_to_lend` to `list_display` and fieldsets.

---

## 8. Migrations

| # | Content |
|---|---|
| N   | Add `willing_to_lend`, `visible_to` to `Boat` |
| N+1 | Add `visible_to` to `RegularParticipant` |
| N+2 | Add `crew_registration_deadline` to `EventSettings` |
| N+3 | Create `Crew` and `CrewMember` tables |

---

## 9. Out of Scope

- Crew rule validation (sail area, participant age/count vs. category rules) — deferred.
- IndividualParticipant and Organizer as crew members — RegularParticipant only for now.
- Lending for boats beyond `visible_to` (e.g., time-limited loans, loan requests) — not needed.
- RFID / plavenky integration — separate module.
