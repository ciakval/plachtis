# InfoDesk Edit Registrations — Design

**Issue:** #128
**Date:** 2026-04-21

## Problem

InfoDesk members need to edit any registration at will — adding, removing, and modifying participants — regardless of ownership or deadlines. They also need a clear path from the registration list to the edit forms.

Currently:
- `Entity.can_be_edited(user)` already returns `True` for InfoDesk members (model layer is ready).
- But `edit_unit`, `edit_individual_participant`, and `edit_organizer` check ownership/editor status *before* calling `can_be_edited`, blocking InfoDesk members with a permission error.
- `infodesk_registrations.html` has no edit links.
- After saving, all edit views redirect to personal owner lists, which are empty/irrelevant for InfoDesk members.

## Approach

Patch the three existing edit views and the infodesk registrations template. No new views, URLs, or templates.

## Section 1 — Permission bypass in edit views

In `edit_unit`, `edit_individual_participant`, and `edit_organizer` (`SkaRe/views/registration.py`), add `is_infodesk(request.user)` to the ownership guard:

```python
# Before
if not (is_owner or is_editor):
    ...

# After
if not (is_owner or is_editor or is_infodesk(request.user)):
    ...
```

`is_infodesk` is already importable from `..permissions`. The subsequent `can_be_edited` call already returns `True` for InfoDesk, so no change is needed there. `edit_organizer` does not call `can_be_edited` (organizers are deadline-exempt per issue #124) — only its ownership check needs patching.

## Section 2 — Redirect after save for InfoDesk

In the success branch of all three edit views, redirect InfoDesk members to the infodesk registrations list instead of the owner's personal list:

```python
if is_infodesk(request.user):
    return redirect('SkaRe:infodesk_registrations')
return redirect('SkaRe:list_units')  # (or appropriate personal list)
```

## Section 3 — Edit links in infodesk registrations template

In `SkaRe/templates/SkaRe/infodesk/registrations.html`, add an Edit button per row in the Actions column. Resolve the correct edit URL using the reverse OneToOne profiles already loaded via `select_related`:

```html
{% if row.entity.unit_profile %}
  <a href="{% url 'SkaRe:edit_unit' row.entity.unit_profile.pk %}" class="btn btn-outline-primary btn-sm">
    <i class="bi bi-pencil"></i> {% trans "Edit" %}
  </a>
{% elif row.entity.individual_participant_profile %}
  <a href="{% url 'SkaRe:edit_individual_participant' row.entity.individual_participant_profile.pk %}" class="btn btn-outline-primary btn-sm">
    <i class="bi bi-pencil"></i> {% trans "Edit" %}
  </a>
{% elif row.entity.organizer_profile %}
  <a href="{% url 'SkaRe:edit_organizer' row.entity.organizer_profile.pk %}" class="btn btn-outline-primary btn-sm">
    <i class="bi bi-pencil"></i> {% trans "Edit" %}
  </a>
{% endif %}
```

No extra DB queries — `select_related` on all three profiles is already in `infodesk_registrations`.

## Files changed

| File | Change |
|------|--------|
| `SkaRe/views/registration.py` | Add `is_infodesk` import; patch ownership guard and success redirect in `edit_unit`, `edit_individual_participant`, `edit_organizer` |
| `SkaRe/templates/SkaRe/infodesk/registrations.html` | Add Edit button per row in Actions column |

## Out of scope

- No new views, URLs, or templates
- No changes to the permission model or `Entity.can_be_edited`
- No changes to the infodesk dashboard
