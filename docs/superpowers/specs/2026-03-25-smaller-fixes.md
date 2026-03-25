# Smaller Fixes — Design Spec

**Date:** 2026-03-25
**Scope:** Two independent improvements: (A) boat form field placement and prefill behaviour, (B) hat size split in participant registration.

---

## A. Boat Form — Field Placement + Prefill Behaviour

### A1. Move vessel_registry_number and engine_power_hp to the Boat card

`vessel_registry_number` and `engine_power_hp` describe the physical vessel, not the owner. This spec supersedes the Phase 1.1 spec's placement of these fields in the "Owner / Manager" card.

In `SkaRe/templates/SkaRe/boats/form.html`:
- Move the `vessel_registry_number` and `engine_power_hp` field row from the "Owner / Manager" card to the end of the "Boat" card (after the hull/sail colour row).

`detail.html` already displays these fields unconditionally in their own block — no section relabelling is needed there.

### A2. Sail registry lookup — change from blur to button

**Current behaviour (to remove):** the `blur` event listener on `id_sail_number` in `boat-form.js` triggers an AJAX lookup. Remove this listener entirely.

**New behaviour:**

In `form.html`, after the closing `</div>` of the sail_number/name row (i.e., as a new block-level element inside the Boat card, not inside any column), add:

```html
<div class="mb-3">
    <button type="button" id="btn-sail-lookup" class="btn btn-secondary">
        <i class="bi bi-search"></i> Vyhledat v registru plachet
    </button>
    <div id="sail-lookup-error" class="text-danger mt-1" style="display:none;"></div>
</div>
```

In `boat-form.js`, replace the blur-based listener with a click handler on `#btn-sail-lookup`:

1. Clear `#sail-lookup-error` text and set its `style.display = 'none'`.
2. Disable the button (`btn.disabled = true`).
3. Fetch `/boats/api/sail-lookup/?q=<id_sail_number.value.trim()>`.
4. In the `finally` block: re-enable the button (`btn.disabled = false`).
5. **Success (200):** directly set the `.value` property of `id_name`, `id_class_supplement`, `id_sail_area` (overwrite regardless of current content). For boat class: set `select.value = ''` first, then iterate options to find a case-insensitive `includes` match on `data.class_name` and set `select.value` — do not use a guard. Do **not** fill `harbor_number`, `harbor_name`, or `contact_person`.
6. **Not found (404):** set `#sail-lookup-error` `textContent` to "Plachetní číslo nebylo v registru nalezeno." and show it (`style.display = ''`).
7. **Any other error (503, network failure, JSON parse error):** set `#sail-lookup-error` `textContent` to "Registr plachet je nedostupný." and show it.

Note: `selectBoatClassByName` currently guards with `if (!select.value)` — the button handler must **not** call this existing function. Instead, implement the boat class overwrite inline in the new handler (as described in step 5), so that the existing fill-if-empty `selectBoatClassByName` used elsewhere (if any) is not affected.

### A3. Unit prefill — add contact_phone

`boat_my_unit` view currently returns `harbor_number`, `harbor_name`, `contact_person`.

**Changes:**
- In `boat_my_unit` view: add `'contact_phone': unit.entity.contact_phone` to the `JsonResponse`.
- In `boat-form.js`, unit prefill handler: add `fillIfEmpty('id_contact_phone', data.contact_phone)`.

Fill-if-empty behaviour is intentional for the unit button.

---

## B. Hat Size Split

### B1. Model changes

Add `small_hat_count` to both `Unit` and `IndividualParticipant`:

```python
small_hat_count = models.PositiveBigIntegerField(
    default=0,
    help_text=_("Number of small hats (S/M)"),
    verbose_name=_("Hat count (S/M)"),
)
```

(`PositiveBigIntegerField` matches the existing `hat_count` and `scarf_count` on the same models.)

Update `hat_count` on **both** `Unit` and `IndividualParticipant`:
- `verbose_name=_("Hat count (L/XL)")`
- `help_text=_("Number of large hats (L/XL)")`

`Organizer.wants_hat` is unchanged — it represents a large hat (L/XL). No `wants_small_hat` field for organizers.

### B2. Migration

One migration adding `small_hat_count` to `SkaRe_unit` and `SkaRe_individualparticipant` with `default=0`. No data migration needed (existing `hat_count` values represent L/XL hats).

### B3. Form changes — all four hat-bearing form classes

Add `small_hat_count` (after `hat_count`) + widget `NumberInput(attrs={'class': 'form-control', 'min': '0'})` to:

1. `UnitRegistrationForm` in `forms.py` (Meta.fields + Meta.widgets)
2. `IndividualParticipantRegistrationForm` in `forms.py` (Meta.fields + Meta.widgets)
3. `UnitEditForm` (inline class inside `edit_unit` view in `views.py`) — Meta.fields + Meta.widgets
4. `IndividualParticipantEditForm` (inline class inside `edit_individual_participant` view in `views.py`) — Meta.fields + Meta.widgets

### B4. Template changes

In all four templates, place `small_hat_count` in the **same `<div class="row">`** as `hat_count`, as a second `col-md-6` column (mirror the `hat_count` block exactly):

- `register_unit.html`
- `edit_unit.html`
- `register_individual_participant.html`
- `edit_individual_participant.html`

### B5. Merchandise view + template

**View (`list_merchandise` in `views.py`):**

The existing statistics alert (which counts registrations, not hat quantities) is **not affected**. Only the hat-count aggregation variables change.

Replace:
```python
total_hats = sum(item or 0 for item in [
    units.aggregate(total=Sum('hat_count'))['total'],
    individual_participants.aggregate(total=Sum('hat_count'))['total'],
    organizers.filter(wants_hat=True).count(),
])
```

With:
```python
total_hats_large = sum(item or 0 for item in [
    units.aggregate(total=Sum('hat_count'))['total'],
    individual_participants.aggregate(total=Sum('hat_count'))['total'],
    organizers.filter(wants_hat=True).count(),
])
total_hats_small = sum(item or 0 for item in [
    units.aggregate(total=Sum('small_hat_count'))['total'],
    individual_participants.aggregate(total=Sum('small_hat_count'))['total'],
    # organizers have no small hat — intentionally omitted
])
```

Pass `total_hats_large` and `total_hats_small` in context (remove `total_hats`).

**Template (`list_merchandise.html`):**

- Table header: replace single `<th>{% trans "Hats" %}</th>` with two: `<th>Čepice L/XL</th><th>Čepice S/M</th>` (Czech-only, no `{% trans %}` needed — this is an admin-only view).
- Unit rows: two `<td>` — `{{ unit.hat_count }}` / `{{ unit.small_hat_count }}`.
- Individual participant rows: `{{ participant.hat_count }}` / `{{ participant.small_hat_count }}`.
- Organizer rows: `{% if organizer.wants_hat %}1{% else %}0{% endif %}` / `0`.
- Footer `<tfoot>`: replace single `{{ total_hats }}` cell with two cells `{{ total_hats_large }}` / `{{ total_hats_small }}`.
- Statistics alert: unchanged (counts registrations, not hats).

### B6. Czech translations (django.po)

The current `.po` file has two entries to update. **Delete** the old entries and **add** new ones (this is the correct `.po` workflow — msgid values cannot be renamed in-place):

**Remove:**
```po
msgid "Number of hats"
msgstr "Počet čepic"

msgid "Hat count"
msgstr "Počet čepic"
```

**Add:**
```po
msgid "Number of large hats (L/XL)"
msgstr "Počet čepic L/XL"

msgid "Hat count (L/XL)"
msgstr "Počet čepic L/XL"

msgid "Number of small hats (S/M)"
msgstr "Počet čepic S/M"

msgid "Hat count (S/M)"
msgstr "Počet čepic S/M"
```

The `"Hats"` table column header in the template is **not** wrapped in `{% trans %}` in the new design (see B5) — no translation entry needed for it.

After editing `django.po`, run:
```bash
uv run python manage.py compilemessages
```

---

## Out of scope

- Boat `detail.html`: no section relabelling needed.
- No small hat option for organizers.
