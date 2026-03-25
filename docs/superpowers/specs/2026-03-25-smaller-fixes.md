# Smaller Fixes — Design Spec

**Date:** 2026-03-25
**Scope:** Two independent improvements: (A) boat form field placement and prefill behaviour, (B) hat size split in participant registration.

---

## A. Boat Form — Field Placement + Prefill Behaviour

### A1. Move vessel_registry_number and engine_power_hp to the Boat card

Both fields describe the physical vessel, not the owner. In `SkaRe/templates/SkaRe/boats/form.html`, move the two field blocks from the "Owner / Manager" card into the "Boat" card (after hull/sail colour).

### A2. Sail registry lookup — change from blur to button

**Current behaviour:** typing a sail number and blurring the field triggers an AJAX lookup that fill-if-empty: `name`, `class_supplement`, `sail_area`, `harbor_number`, `harbor_name`, `contact_person`.

**New behaviour:**
- Remove the `blur` event listener from `id_sail_number`.
- Add a button "Vyhledat v registru plachet" next to the sail number field in the template.
- On click: fetch `/boats/api/sail-lookup/?q=<sail_number>`.
  - **Success (200):** overwrite (regardless of current content) `name`, `class_supplement`, `sail_area`; match boat class via select. Do NOT fill `harbor_number`, `harbor_name`, or `contact_person` — these are owner fields.
  - **Not found (404):** show inline error: "Plachetní číslo nebylo v registru nalezeno."
  - **Unavailable (503) or network error:** show inline error: "Registr plachet je nedostupný."
  - Clear any previous error message on each new click before the fetch.

### A3. Unit prefill — add contact_phone

The "Fill from My Unit" button calls `/boats/api/my-unit/` and fill-if-empty: `harbor_number`, `harbor_name`, `contact_person`.

**Change:** also return and fill `contact_phone` (from `unit.entity.contact_phone`).

The fill-if-empty behaviour is intentional for the unit button (don't overwrite user-typed data).

---

## B. Hat Size Split

### B1. Model changes

Add `small_hat_count` field to both `Unit` and `IndividualParticipant`:

```python
small_hat_count = models.PositiveBigIntegerField(
    default=0,
    help_text=_("Number of small hats (S/M)"),
    verbose_name=_("Hat count (S/M)"),
)
```

Update `hat_count` verbose name on both models to `_("Hat count (L/XL)")`.

`Organizer.wants_hat` remains unchanged — organizers receive a large hat (L/XL) only.

### B2. Migration

One migration adding `small_hat_count` to `SkaRe_unit` and `SkaRe_individualparticipant`. Existing `hat_count` data is unchanged (it represents L/XL hats).

### B3. Form changes

Add `small_hat_count` to:
- `UnitRegistrationForm` Meta fields + widgets (NumberInput, min=0)
- `IndividualParticipantRegistrationForm` Meta fields + widgets (NumberInput, min=0)

### B4. Template changes

In each of the four templates (register_unit, edit_unit, register_individual_participant, edit_individual_participant): add `small_hat_count` field immediately after `hat_count`, in the same row.

### B5. Merchandise view + template

**View (`list_merchandise`):**
- Rename `total_hats` → `total_hats_large`
- Add `total_hats_small` aggregating `small_hat_count` across units and individual participants (organizers have no small hat)
- Pass both totals to template

**Template (`list_merchandise.html`):**
- Replace single "Hats" column with two: "Čepice L/XL" and "Čepice S/M"
- Organizer rows show 0 for S/M column
- Footer totals show both

### B6. Czech translations (django.po)

New strings:
- `"Hat count (L/XL)"` → `"Počet čepic L/XL"`
- `"Number of large hats (L/XL)"` → `"Počet čepic L/XL"`
- `"Hat count (S/M)"` → `"Počet čepic S/M"`
- `"Number of small hats (S/M)"` → `"Počet čepic S/M"`
- `"Scarves and Hats"` title remains; column header updates in template use `{% trans %}` blocks

---

## Out of scope

- Boat detail template (`detail.html`) already shows vessel_registry_number and engine_power_hp conditionally — no changes needed to its section assignment (labels describe the data adequately).
- No changes to organizer hat logic beyond keeping `wants_hat` = L/XL.
