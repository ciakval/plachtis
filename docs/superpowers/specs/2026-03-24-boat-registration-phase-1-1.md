# Boat Registration — Phase 1.1 Design Spec

**Date:** 2026-03-24
**Scope:** Iteration on Phase 1 boat registration — dynamic sail registry lookup, new boat fields, home page integration, and phone validation improvements.
**App:** `SkaRe` (existing Django app)
**Branch base:** `main` (Phase 1 already merged)

---

## Overview

Phase 1.1 makes four categories of change:

1. **Drop `SailRegistryEntry`** and replace the static CSV-backed lookup with a live fetch from the publicly published Google Sheet.
2. **Extend the `Boat` model** with hull/sail colour, vessel registry number, and engine power.
3. **Polish form and templates**: `boat_class` required, section label rename, home page buttons.
4. **Broaden phone validation** on boat `contact_phone` to accept Czech, Slovak, and common neighbouring-country formats.

---

## 1. Sail Registry — Live Google Sheets Lookup

### Rationale

The sail registry is a Google Sheet maintained externally. Storing a local copy (the `SailRegistryEntry` model) introduces a sync problem: the copy goes stale between imports and requires an admin action to refresh. Because the sheet is publicly published, we can fetch it on demand instead.

### What is removed

- `SailRegistryEntry` model (and its DB table)
- The auto migration that created `SailRegistryEntry`
- The admin `import-csv/` view and template (`admin/SkaRe/sailregistryentry/import_csv.html`)
- `SailRegistryEntryAdmin` registration in `admin.py`
- All tests that reference `SailRegistryEntry`

### Django setting

Add to `settings.py`:

```python
SAIL_REGISTRY_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vR3AYk5tYLbTke5J3yM8hhQHPSejpc7C9rCAsQ-ftmS-pTC2P2BN0xlGioeo_R8ttKMeQV_bbj_jC4m/"
    "pub?gid=1327431256&single=true&output=csv"
)
SAIL_REGISTRY_CACHE_TTL = 3600  # seconds; default 1 hour
```

### Caching

`boat_sail_lookup` must not make an outbound HTTP request on every call. Use Django's default cache:

```python
from django.core.cache import cache

CACHE_KEY = "sail_registry_csv"

rows = cache.get(CACHE_KEY)
if rows is None:
    rows = _fetch_registry_rows()   # HTTP + parse
    cache.set(CACHE_KEY, rows, settings.SAIL_REGISTRY_CACHE_TTL)
```

`_fetch_registry_rows()` fetches `settings.SAIL_REGISTRY_SHEET_URL` using `urllib.request` (standard library, no extra dependency), decodes as UTF-8, and parses with Python's `csv.reader`. Returns a list of dicts keyed by column name (from row 0).

If the fetch fails (network error, non-200 status), `_fetch_registry_rows()` raises an exception. The view catches it and returns HTTP 503. The existing JS already silently ignores non-OK responses (`if (!response.ok) return;`), so the user sees no error — the prefill simply does not happen.

### Column mapping

The published sheet has the following columns (row 0):

| Sheet column | Model field / JSON key | Notes |
|---|---|---|
| `plach. číslo` | `sail_number` | Lookup key |
| `Jméno` | `boat_name` | |
| `typ` | `class_name` + `subtype` | Compound: `"šalupa - P550 - Černá Eskadra"` — split on ` - `; index 0 → `subtype`, index 1 → `class_name`, remainder ignored |
| `oddíl` | `contact_person` | Scout unit name |
| `přístav` | `harbor_name` | |
| `ev. č.` | `harbor_number` | |
| `plocha dle Certifikátu (m2)` | `sail_area` | Replace comma with dot before converting to string |
| `datum měření` | *(ignored)* | Not stored or returned |

Sail number matching is case-insensitive (`str.lower()` comparison). The sail numbers in the sheet are plain integers, but `?q=` from the form may include leading zeros — strip and compare normalised integers if both parse, otherwise fall back to string comparison.

### `boat_sail_lookup` view (updated signature)

```
GET /boats/api/sail-lookup/?q=<sail_number>
```

Response on match (HTTP 200):
```json
{
  "sail_number": "14",
  "boat_name": "ALBATROS",
  "class_name": "P550",
  "subtype": "šalupa",
  "sail_area": "7.00",
  "harbor_number": "113.04",
  "harbor_name": "4. Jana Nerudy Praha",
  "contact_person": ""
}
```

Response codes:
- `400` — missing or empty `?q=`
- `404` — sail number not found in the sheet
- `503` — sheet fetch failed (network or parse error)

### Tests

Mock the HTTP fetch with `unittest.mock.patch` on `urllib.request.urlopen` (or on the `_fetch_registry_rows` helper). Test cases:
- Successful lookup returns correct JSON
- Sail number not in sheet → 404
- Missing `?q=` → 400
- Fetch failure → 503
- Cache hit: second call does not trigger another HTTP fetch

---

## 2. New `Boat` Fields

All four fields are added in a single migration.

### Colour choices

Defined as a nested class on `Boat` (reused for both hull and sail colour):

```python
class Color(models.TextChoices):
    WHITE  = 'bila',     'Bílá'
    BLACK  = 'cerna',    'Černá'
    RED    = 'cervena',  'Červená'
    BLUE   = 'modra',    'Modrá'
    GREEN  = 'zelena',   'Zelená'
    YELLOW = 'zluta',    'Žlutá'
    ORANGE = 'oranzova', 'Oranžová'
    GRAY   = 'seda',     'Šedá'
    BROWN  = 'hneda',    'Hnědá'
    OTHER  = 'jina',     'Jiná'
```

### New fields on `Boat`

| Field | Type | Notes |
|---|---|---|
| `hull_color` | `CharField(max_length=20, choices=Color.choices, blank=True)` | Optional; important for on-water identification |
| `sail_color` | `CharField(max_length=20, choices=Color.choices, blank=True)` | Optional |
| `vessel_registry_number` | `CharField(max_length=50, blank=True)` | "Registrační číslo v rejstříku malých plavidel"; applicable to vessels subject to mandatory registration |
| `engine_power_hp` | `PositiveSmallIntegerField(null=True, blank=True)` | Engine power in HP; optional for all boat types |

`hull_color` and `sail_color` are optional at the DB and form level. They should be visually encouraged in the UI (helper text: "Barva je při identifikaci lodi na vodě zásadní.") but not enforced.

`engine_power_hp` is always shown in the form as a plain optional field. No JS-based conditional show/hide based on class — simpler to maintain and non-motor users will simply leave it blank.

### Form placement

In `BoatForm` (and the `form.html` template), group the new fields as follows:

**Card "Loď"** (existing section, append):
- `hull_color` (select)
- `sail_color` (select)

**Card "Vlastník / správce"** (renamed from "Vlastník", append after existing fields):
- `vessel_registry_number`
- `engine_power_hp`

---

## 3. Form and Template Changes

### `boat_class` required

Remove `self.fields['boat_class'].required = False` from `BoatForm.__init__`. The DB field remains `null=True` (for `SET_NULL` on `BoatClass` deletion), but the form now rejects submissions without a class.

Remove the `*`-less label treatment and any UI hint that the field is optional.

### Section label rename

In `form.html` and `detail.html`, rename the card header **"Vlastník"** → **"Vlastník / správce"**.

### Home page boat buttons

In `SkaRe/templates/SkaRe/home.html`, inside the `{% if user.is_authenticated %}` block:

**"Register" section** — add alongside the existing unit/participant/organizer buttons:
```html
<a class="btn btn-primary btn-lg me-2 mb-2" href="{% url 'SkaRe:boat_register' %}" role="button">
    <i class="bi bi-sailboat"></i> Registrovat loď
</a>
```

**"My Registrations" section** — add alongside the existing unit/participant/organiser buttons:
```html
<a class="btn btn-info btn-lg me-2 mb-2" href="{% url 'SkaRe:boat_list' %}" role="button">
    <i class="bi bi-sailboat"></i> Lodě
</a>
```

The home page uses `{% load i18n %}` and `{% trans %}` throughout. The new boat buttons should **not** wrap strings in `{% trans %}` — boats are a Czech-only feature and the home page will not be translated (consistent with the rest of the boat UI).

---

## 4. Phone Validation

### Existing situation

`validate_czech_phone` (in `forms.py`) accepts `+420 + 9 digits`, `+421 + 9 digits`, or bare 9 digits. It is already used on unit and participant contact phones. It is **not** currently applied to `Boat.contact_phone`.

### New validator: `validate_event_phone`

Add a second validator in `forms.py` that accepts the broader set of formats appropriate for a sailing event where participants may come from neighbouring countries:

**Accepted formats** (after stripping spaces and dashes):
- `+` followed by 7–14 digits — covers any well-formed international E.164 number (CZ `+420`, SK `+421`, DE `+49`, AT `+43`, PL `+48`, HU `+36`, and others)
- Exactly 9 digits with no prefix — Czech/Slovak local format

**Algorithm:**
```python
def validate_event_phone(value):
    clean = value.replace(' ', '').replace('-', '')
    if clean.startswith('+'):
        digits = clean[1:]
        if digits.isdigit() and 7 <= len(digits) <= 14:
            return value
    elif clean.isdigit() and len(clean) == 9:
        return value
    raise ValidationError(
        'Zadejte platné telefonní číslo '
        '(např. +420 123 456 789, +49 123 45678 nebo 123 456 789)'
    )
```

Apply `validate_event_phone` (not `validate_czech_phone`) to `BoatForm`'s `contact_phone` field. Do not change the existing validator or its usages elsewhere.

---

## 5. Migration Plan

Two new migrations (appended to the existing sequence):

| # | Type | Content |
|---|---|---|
| N | Auto | Drop `SailRegistryEntry` table (reverse of the migration that created it) |
| N+1 | Auto | Add `hull_color`, `sail_color`, `vessel_registry_number`, `engine_power_hp` to `Boat` |

No data migration needed. `SailRegistryEntry` has never been in production.

---

## 6. Admin Changes

Remove:
- `SailRegistryEntryAdmin` class
- The `get_urls()` override and `import_csv_view` method
- `admin.site.register(SailRegistryEntry, SailRegistryEntryAdmin)`

Add `hull_color`, `sail_color`, `vessel_registry_number`, `engine_power_hp` to `BoatAdmin.list_display` or `fieldsets` as appropriate.

---

## 7. Out of Scope

- Caching backend configuration (default `LocMemCache` is per-process; adequate for this event's scale).
- Cache invalidation UI (TTL expiry is sufficient).
- Adding `datum měření` (measurement date) to the data model.
- Conditional JS show/hide for `engine_power_hp` based on boat class.
- Translating boat UI strings (boat registration is Czech-only).
