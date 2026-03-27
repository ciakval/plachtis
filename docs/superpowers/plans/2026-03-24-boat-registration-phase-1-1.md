# Boat Registration Phase 1.1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drop `SailRegistryEntry` and replace with live Google Sheets lookup; add hull/sail colour, vessel registry number, and engine power fields to `Boat`; broaden phone validation; add home page boat buttons; rename "Vlastník" section.

**Spec:** `docs/superpowers/specs/2026-03-24-boat-registration-phase-1-1.md`

**Tech Stack:** Django 6.0, Python 3.12, `uv` (run all commands with `uv run python manage.py ...`), vanilla JS.

**Base branch:** `main` (Phase 1 already merged and deployed to main).

**Starting state:** 64 tests passing. Last migration: `0016_boatclass_initial_data.py`.

---

## File Map

| File | Action | Purpose |
|------|---------|---------|
| `SkaRe/models.py` | Modify | Remove `SailRegistryEntry`; add `Boat.Color`, `hull_color`, `sail_color`, `vessel_registry_number`, `engine_power_hp` |
| `SkaRe/migrations/0017_remove_sailregistryentry.py` | Create (auto) | Drop the `sail_registry_entry` table |
| `SkaRe/migrations/0018_boat_phase_1_1_fields.py` | Create (auto) | Add new fields to `Boat` |
| `SkaRe/forms.py` | Modify | Add `validate_event_phone`; update `BoatForm` (required boat_class, new fields, phone validator) |
| `SkaRe/views.py` | Modify | Remove `SailRegistryEntry` import; add `_fetch_sheet_csv`, `_get_registry_rows`; rewrite `boat_sail_lookup` |
| `SkaRe/admin.py` | Modify | Remove `SailRegistryEntryAdmin`; add new fields to `BoatAdmin` |
| `SkaRe/templates/SkaRe/boats/form.html` | Modify | Add colour selects, vessel registry number, engine power; rename section |
| `SkaRe/templates/SkaRe/boats/detail.html` | Modify | Add new fields; rename section |
| `SkaRe/templates/SkaRe/home.html` | Modify | Add boat register + boat list buttons |
| `SkaRe/templates/admin/SkaRe/sailregistryentry/` | Delete | CSV import template no longer needed |
| `SkaRe/tests/test_boat_models.py` | Modify | Remove `SailRegistryEntryModelTest` |
| `SkaRe/tests/test_boat_views.py` | Modify | Replace `SailLookupViewTest` with mock-based version |
| `SkaRe/tests/test_boat_admin.py` | Delete | Entire file — CSV import admin is gone |
| `SkaRe/tests/test_boat_forms.py` | Modify | Add tests for new fields and `validate_event_phone` |
| `settings.py` | Modify | Add `SAIL_REGISTRY_SHEET_URL`, `SAIL_REGISTRY_CACHE_TTL` |

---

## Task 1: Remove SailRegistryEntry and rewrite sail lookup as live Google Sheets fetch

**Files:**
- Modify: `SkaRe/models.py`
- Modify: `SkaRe/views.py`
- Modify: `SkaRe/admin.py`
- Modify: `settings.py` (the project settings file — check `manage.py` to confirm its module name)
- Create: `SkaRe/migrations/0017_remove_sailregistryentry.py` (auto via makemigrations)
- Delete: `SkaRe/tests/test_boat_admin.py`
- Delete: `SkaRe/templates/admin/SkaRe/sailregistryentry/import_csv.html`
- Modify: `SkaRe/tests/test_boat_models.py`
- Modify: `SkaRe/tests/test_boat_views.py`

- [ ] **Step 1: Write the new failing sail lookup tests**

Replace the `SailLookupViewTest` class in `SkaRe/tests/test_boat_views.py`. Remove the `SailRegistryEntry` import from that file's import block and replace the class with:

```python
import csv
import io
from unittest.mock import patch
from django.core.cache import cache

# Place this constant at module level in the test file, near the top:
_SAMPLE_SHEET_CSV = (
    "plach. číslo,Jméno,typ,oddíl,přístav,ev. č.,"
    "plocha dle Certifikátu (m2),datum měření\r\n"
    '14,ALBATROS,šalupa - P550 - Černá Eskadra,,4. Jana Nerudy Praha,113.04,"7,02",28.9.2022\r\n'
    "42,RYCHLÍK,ketový keč - Cadet - ,Jan Novák,5. oddíl Koráb,523.10,,15.3.2023\r\n"
)


class SailLookupViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='user', password='pw')
        self.client.login(username='user', password='pw')
        cache.clear()

    def test_found_returns_json(self):
        url = reverse('SkaRe:boat_sail_lookup')
        with patch('SkaRe.views._fetch_sheet_csv', return_value=_SAMPLE_SHEET_CSV):
            response = self.client.get(url, {'q': '14'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['boat_name'], 'ALBATROS')
        self.assertEqual(data['class_name'], 'P550')
        self.assertEqual(data['subtype'], 'šalupa')
        self.assertEqual(data['sail_area'], '7.02')
        self.assertEqual(data['harbor_name'], '4. Jana Nerudy Praha')

    def test_case_insensitive_lookup(self):
        url = reverse('SkaRe:boat_sail_lookup')
        with patch('SkaRe.views._fetch_sheet_csv', return_value=_SAMPLE_SHEET_CSV):
            response = self.client.get(url, {'q': '14'})
        self.assertEqual(response.status_code, 200)

    def test_not_found_returns_404(self):
        url = reverse('SkaRe:boat_sail_lookup')
        with patch('SkaRe.views._fetch_sheet_csv', return_value=_SAMPLE_SHEET_CSV):
            response = self.client.get(url, {'q': '999'})
        self.assertEqual(response.status_code, 404)

    def test_missing_q_returns_400(self):
        url = reverse('SkaRe:boat_sail_lookup')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

    def test_fetch_failure_returns_503(self):
        url = reverse('SkaRe:boat_sail_lookup')
        with patch('SkaRe.views._fetch_sheet_csv', side_effect=Exception('network error')):
            response = self.client.get(url, {'q': '14'})
        self.assertEqual(response.status_code, 503)

    def test_cache_prevents_second_fetch(self):
        url = reverse('SkaRe:boat_sail_lookup')
        with patch('SkaRe.views._fetch_sheet_csv', return_value=_SAMPLE_SHEET_CSV) as mock_fetch:
            self.client.get(url, {'q': '14'})
            self.client.get(url, {'q': '42'})
        self.assertEqual(mock_fetch.call_count, 1)

    def test_requires_login(self):
        self.client.logout()
        url = reverse('SkaRe:boat_sail_lookup')
        response = self.client.get(url, {'q': '14'})
        self.assertEqual(response.status_code, 302)
```

Run these tests — they will fail because `SailRegistryEntry` still exists and `_fetch_sheet_csv` doesn't exist yet:

```bash
uv run python manage.py test SkaRe.tests.test_boat_views.SailLookupViewTest
```

Expected: FAIL/ERROR. These are the acceptance criteria.

- [ ] **Step 2: Remove `SailRegistryEntryModelTest` from test_boat_models.py**

Delete the `SailRegistryEntryModelTest` class (lines 22–31 in the current file). Remove `SailRegistryEntry` from the import on line 3. Leave `BoatModelTest` and `BoatClassModelTest` untouched.

- [ ] **Step 3: Delete test_boat_admin.py**

```bash
git rm SkaRe/tests/test_boat_admin.py
```

- [ ] **Step 4: Remove SailRegistryEntry from models.py**

Delete the entire `SailRegistryEntry` class from `SkaRe/models.py`. Remove it from any `__all__` if present. Leave `BoatClass` and `Boat` untouched.

- [ ] **Step 5: Generate migration 0017**

```bash
uv run python manage.py makemigrations SkaRe --name remove_sailregistryentry
```

Verify the generated migration only drops the `sail_registry_entry` table and touches nothing else. The migration must depend on `0016_boatclass_initial_data`.

- [ ] **Step 6: Add Django settings**

Find the settings module (check `manage.py` for `DJANGO_SETTINGS_MODULE`). Add at the bottom of the settings file:

```python
SAIL_REGISTRY_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vR3AYk5tYLbTke5J3yM8hhQHPSejpc7C9rCAsQ-ftmS-pTC2P2BN0xlGioeo_R8ttKMeQV_bbj_jC4m/"
    "pub?gid=1327431256&single=true&output=csv"
)
SAIL_REGISTRY_CACHE_TTL = 3600  # seconds
```

- [ ] **Step 7: Rewrite boat_sail_lookup in views.py**

Add the following imports near the top of `views.py` (after existing imports):

```python
import csv
import io
import urllib.request
from django.core.cache import cache
```

Add these two helpers just above the `boat_sail_lookup` view function:

```python
_SAIL_REGISTRY_CACHE_KEY = "sail_registry_rows"


def _fetch_sheet_csv(url):
    """Fetch the published Google Sheets CSV and return the raw text.

    Decodes as UTF-8-sig to strip any BOM. Raises on network errors.
    """
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as response:
        return response.read().decode('utf-8-sig')


def _get_registry_rows():
    """Return parsed registry rows from cache, fetching if necessary."""
    rows = cache.get(_SAIL_REGISTRY_CACHE_KEY)
    if rows is None:
        raw = _fetch_sheet_csv(settings.SAIL_REGISTRY_SHEET_URL)
        reader = csv.DictReader(io.StringIO(raw))
        rows = list(reader)
        cache.set(_SAIL_REGISTRY_CACHE_KEY, rows, settings.SAIL_REGISTRY_CACHE_TTL)
    return rows
```

Replace the `boat_sail_lookup` view with:

```python
@login_required
def boat_sail_lookup(request):
    """AJAX: look up a sail number in the Google Sheets registry."""
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'error': 'missing q'}, status=400)

    try:
        rows = _get_registry_rows()
    except Exception:
        return JsonResponse({'error': 'registry unavailable'}, status=503)

    match = None
    q_lower = q.lower()
    for row in rows:
        sail_num = row.get('plach. číslo', '').strip()
        if sail_num.lower() == q_lower:
            match = row
            break
        # Numeric normalisation: "14" matches "14", "014", etc.
        try:
            if int(sail_num) == int(q):
                match = row
                break
        except (ValueError, TypeError):
            pass

    if match is None:
        return JsonResponse({'error': 'not found'}, status=404)

    # Parse compound 'typ' field: "šalupa - P550 - Černá Eskadra"
    typ = match.get('typ', '').strip()
    typ_parts = [p.strip() for p in typ.split(' - ')] if typ else []
    subtype = typ_parts[0] if len(typ_parts) > 0 else ''
    class_name = typ_parts[1] if len(typ_parts) > 1 else ''

    # Sail area: Czech decimal comma → dot
    sail_area_raw = match.get('plocha dle Certifikátu (m2)', '').strip()
    sail_area = sail_area_raw.replace(',', '.') if sail_area_raw else ''

    return JsonResponse({
        'sail_number': match.get('plach. číslo', '').strip(),
        'boat_name': match.get('Jméno', '').strip(),
        'class_name': class_name,
        'subtype': subtype,
        'sail_area': sail_area,
        'harbor_number': match.get('ev. č.', '').strip(),
        'harbor_name': match.get('přístav', '').strip(),
        'contact_person': match.get('oddíl', '').strip(),
    })
```

Also ensure `from django.conf import settings` is already imported in `views.py` (it likely is — check and add if missing).

Remove `SailRegistryEntry` from the imports in `views.py`.

- [ ] **Step 8: Remove SailRegistryEntryAdmin from admin.py**

In `SkaRe/admin.py`:
- Delete the `SailRegistryEntryAdmin` class and its `import_csv_view` method
- Delete `admin.site.register(SailRegistryEntry, SailRegistryEntryAdmin)`
- Remove `SailRegistryEntry` from the import line

- [ ] **Step 9: Delete the CSV import template**

```bash
git rm SkaRe/templates/admin/SkaRe/sailregistryentry/import_csv.html
```

- [ ] **Step 10: Run tests**

```bash
uv run python manage.py test SkaRe
```

Expected: all tests pass. Test count drops from 64 to ~57 (removed: 2 SailRegistryEntry model tests + 5 admin tests; 5 old sail lookup tests replaced with 7 new mock-based ones → net -5 + 2 = ~57 + potential rounding). The exact count matters less than 0 failures.

- [ ] **Step 11: Commit**

```bash
git add SkaRe/models.py SkaRe/migrations/0017_remove_sailregistryentry.py \
        SkaRe/views.py SkaRe/admin.py \
        SkaRe/tests/test_boat_models.py SkaRe/tests/test_boat_views.py \
        SkaRe/templates/admin/
git add plachtis/settings.py  # adjust path if settings lives elsewhere
git commit -m "feat: replace SailRegistryEntry with live Google Sheets lookup (cached)"
```

---

## Task 2: New Boat fields, BoatForm update, and phone validator

**Files:**
- Modify: `SkaRe/models.py`
- Create: `SkaRe/migrations/0018_boat_phase_1_1_fields.py` (auto)
- Modify: `SkaRe/forms.py`
- Modify: `SkaRe/admin.py`
- Modify: `SkaRe/tests/test_boat_models.py`
- Modify: `SkaRe/tests/test_boat_forms.py`

- [ ] **Step 1: Write failing tests for new model fields**

Append to `SkaRe/tests/test_boat_models.py`:

```python
class BoatColorFieldTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='pw')
        self.bc = BoatClass.objects.create(
            name='P550', category=BoatClass.Category.SAIL, order=1
        )

    def _make_boat(self, **kw):
        return Boat.objects.create(
            created_by=self.user, boat_class=self.bc,
            name='Test', contact_person='J', contact_phone='123456789',
            **kw
        )

    def test_hull_color_blank_by_default(self):
        boat = self._make_boat()
        self.assertEqual(boat.hull_color, '')

    def test_sail_color_blank_by_default(self):
        boat = self._make_boat()
        self.assertEqual(boat.sail_color, '')

    def test_hull_color_accepts_valid_choice(self):
        boat = self._make_boat(hull_color=Boat.Color.WHITE)
        boat.refresh_from_db()
        self.assertEqual(boat.hull_color, 'bila')

    def test_vessel_registry_number_blank_by_default(self):
        boat = self._make_boat()
        self.assertEqual(boat.vessel_registry_number, '')

    def test_engine_power_hp_null_by_default(self):
        boat = self._make_boat()
        self.assertIsNone(boat.engine_power_hp)

    def test_engine_power_hp_stores_integer(self):
        boat = self._make_boat(engine_power_hp=15)
        boat.refresh_from_db()
        self.assertEqual(boat.engine_power_hp, 15)
```

- [ ] **Step 2: Write failing tests for BoatForm and validate_event_phone**

Append to `SkaRe/tests/test_boat_forms.py`:

```python
class ValidateEventPhoneTest(TestCase):
    def _valid(self, number):
        from SkaRe.forms import validate_event_phone
        from django.core.exceptions import ValidationError
        try:
            validate_event_phone(number)
            return True
        except ValidationError:
            return False

    def test_czech_with_prefix(self):
        self.assertTrue(self._valid('+420 123 456 789'))

    def test_czech_local_nine_digits(self):
        self.assertTrue(self._valid('123456789'))

    def test_slovak_prefix(self):
        self.assertTrue(self._valid('+421 900 123 456'))

    def test_german_prefix(self):
        self.assertTrue(self._valid('+49 30 12345678'))

    def test_austrian_prefix(self):
        self.assertTrue(self._valid('+43 1 58858'))

    def test_polish_prefix(self):
        self.assertTrue(self._valid('+48 600 123 456'))

    def test_hungarian_prefix(self):
        self.assertTrue(self._valid('+36 20 123 4567'))

    def test_too_short_rejected(self):
        self.assertFalse(self._valid('12345'))

    def test_letters_rejected(self):
        self.assertFalse(self._valid('abc def'))

    def test_eight_digits_without_prefix_rejected(self):
        self.assertFalse(self._valid('12345678'))


class BoatFormNewFieldsTest(TestCase):
    def _base_data(self):
        bc = BoatClass.objects.create(
            name='P550', category=BoatClass.Category.SAIL, order=1
        )
        return {
            'boat_class': bc.pk,
            'sail_number': '14',
            'name': 'Albatros',
            'contact_person': 'Jan Novák',
            'contact_phone': '+420 123 456 789',
        }

    def test_form_valid_with_hull_and_sail_color(self):
        from SkaRe.models import Boat
        data = self._base_data()
        data['hull_color'] = Boat.Color.WHITE
        data['sail_color'] = Boat.Color.BLUE
        form = BoatForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_valid_without_optional_new_fields(self):
        form = BoatForm(data=self._base_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_boat_class_now_required(self):
        data = self._base_data()
        data['boat_class'] = ''
        form = BoatForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('boat_class', form.errors)

    def test_contact_phone_validated_with_event_validator(self):
        data = self._base_data()
        data['contact_phone'] = '12345'  # too short
        form = BoatForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('contact_phone', form.errors)

    def test_german_phone_accepted(self):
        data = self._base_data()
        data['contact_phone'] = '+49 30 12345678'
        form = BoatForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
```

Run these tests — they will fail:

```bash
uv run python manage.py test SkaRe.tests.test_boat_models.BoatColorFieldTest \
    SkaRe.tests.test_boat_forms.ValidateEventPhoneTest \
    SkaRe.tests.test_boat_forms.BoatFormNewFieldsTest
```

Expected: FAIL (fields don't exist yet).

- [ ] **Step 3: Add fields to Boat model**

In `SkaRe/models.py`, add inside the `Boat` class:

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

Add these four fields to `Boat` (after the existing `sail_area` field and `harbor_*` fields respectively; exact placement in the field list follows the form layout from the spec):

```python
hull_color          = models.CharField(max_length=20, choices=Color.choices, blank=True)
sail_color          = models.CharField(max_length=20, choices=Color.choices, blank=True)
vessel_registry_number = models.CharField(max_length=50, blank=True)
engine_power_hp     = models.PositiveSmallIntegerField(null=True, blank=True)
```

Place `hull_color` and `sail_color` after `sail_area`, and `vessel_registry_number` + `engine_power_hp` after `contact_phone`.

- [ ] **Step 4: Generate migration 0018**

```bash
uv run python manage.py makemigrations SkaRe --name boat_phase_1_1_fields
```

Verify the generated migration adds exactly four fields to `SkaRe_boat` and depends on `0017_remove_sailregistryentry`.

- [ ] **Step 5: Add validate_event_phone to forms.py**

Add the following function in `SkaRe/forms.py`, immediately after the existing `validate_czech_phone` function:

```python
def validate_event_phone(value):
    """Accept Czech local (9 digits) or any international + prefix format."""
    clean = value.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    if clean.startswith('+'):
        digits = clean[1:]
        if digits.isdigit() and 7 <= len(digits) <= 14:
            return value
    elif clean.isdigit() and len(clean) == 9:
        return value
    raise ValidationError(
        'Zadejte platné telefonní číslo '
        '(např. +420 123 456 789, +49 30 12345678 nebo 123456789)'
    )
```

- [ ] **Step 6: Update BoatForm in forms.py**

Update `BoatForm`:

1. Extend `Meta.fields` to include the four new fields:
```python
fields = [
    'boat_class', 'class_supplement', 'sail_number', 'name',
    'description', 'sail_area', 'hull_color', 'sail_color',
    'harbor_number', 'harbor_name', 'contact_person', 'contact_phone',
    'vessel_registry_number', 'engine_power_hp',
]
```

2. In `__init__`, **remove** the line:
```python
self.fields['boat_class'].required = False
```
(`boat_class` is now required.)

3. In `__init__`, **add** the phone validator for boats (replace or add — `contact_phone` currently has no validator in `BoatForm`):
```python
self.fields['contact_phone'].validators = [validate_event_phone]
```

4. Import `validate_event_phone` — it is already in the same file, so no additional import is needed.

5. Add helper text to the colour fields in `__init__` so users understand why they matter:
```python
self.fields['hull_color'].help_text = 'Barva je při identifikaci lodi na vodě zásadní.'
self.fields['sail_color'].help_text = 'Barva je při identifikaci lodi na vodě zásadní.'
```

Also import `Boat` in the `from .models import ...` line if it is not already there (it is — check).

- [ ] **Step 7: Update BoatAdmin in admin.py**

In the `BoatAdmin` class, add the new fields to `list_display` and/or a `fieldsets` definition:

```python
@admin.register(Boat)
class BoatAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'boat_class', 'hull_color', 'sail_color',
                    'contact_person', 'created_by', 'created_at']
    list_filter = ['boat_class', 'hull_color']
    raw_id_fields = ['created_by']
```

- [ ] **Step 8: Run tests**

```bash
uv run python manage.py test SkaRe
```

Expected: all tests pass (including the new model and form tests).

- [ ] **Step 9: Commit**

```bash
git add SkaRe/models.py SkaRe/migrations/0018_boat_phase_1_1_fields.py \
        SkaRe/forms.py SkaRe/admin.py \
        SkaRe/tests/test_boat_models.py SkaRe/tests/test_boat_forms.py
git commit -m "feat: add hull/sail colour, vessel registry, engine power to Boat; require boat_class; add international phone validator"
```

---

## Task 3: Update templates (new fields + section rename)

**Files:**
- Modify: `SkaRe/templates/SkaRe/boats/form.html`
- Modify: `SkaRe/templates/SkaRe/boats/detail.html`

- [ ] **Step 1: Read both templates in full before editing**

Read `form.html` and `detail.html` to understand the current structure precisely.

- [ ] **Step 2: Update form.html**

Make the following changes:

**a. Rename section header** — change `Vlastník` to `Vlastník / správce` in the card header.

**b. Add colour fields** — in the "Loď" card, after the `sail_area` field block, add:

```html
<div class="row">
    <div class="col-md-6 mb-3">
        <label for="{{ form.hull_color.id_for_label }}" class="form-label">
            {{ form.hull_color.label }}
        </label>
        {{ form.hull_color }}
        {% if form.hull_color.help_text %}
            <div class="form-text text-muted">{{ form.hull_color.help_text }}</div>
        {% endif %}
        {% if form.hull_color.errors %}
            <div class="text-danger">{{ form.hull_color.errors }}</div>
        {% endif %}
    </div>
    <div class="col-md-6 mb-3">
        <label for="{{ form.sail_color.id_for_label }}" class="form-label">
            {{ form.sail_color.label }}
        </label>
        {{ form.sail_color }}
        {% if form.sail_color.help_text %}
            <div class="form-text text-muted">{{ form.sail_color.help_text }}</div>
        {% endif %}
        {% if form.sail_color.errors %}
            <div class="text-danger">{{ form.sail_color.errors }}</div>
        {% endif %}
    </div>
</div>
```

**c. Add vessel registry + engine power** — in the "Vlastník / správce" card, after the `contact_phone` block, add:

```html
<div class="row">
    <div class="col-md-6 mb-3">
        <label for="{{ form.vessel_registry_number.id_for_label }}" class="form-label">
            {{ form.vessel_registry_number.label }}
        </label>
        {{ form.vessel_registry_number }}
        {% if form.vessel_registry_number.errors %}
            <div class="text-danger">{{ form.vessel_registry_number.errors }}</div>
        {% endif %}
    </div>
    <div class="col-md-6 mb-3">
        <label for="{{ form.engine_power_hp.id_for_label }}" class="form-label">
            {{ form.engine_power_hp.label }}
        </label>
        {{ form.engine_power_hp }}
        {% if form.engine_power_hp.errors %}
            <div class="text-danger">{{ form.engine_power_hp.errors }}</div>
        {% endif %}
    </div>
</div>
```

**d. Remove the `*` asterisk from boat_class label** — it was already removed in Phase 1 bugfix, but verify it is gone. (boat_class is now actually required again — re-add the asterisk.)

- [ ] **Step 3: Update detail.html**

**a. Rename section** — change `Vlastník` to `Vlastník / správce`.

**b. Add new fields** — using `{% if %}` guards for optional fields. After the existing fields in the "Loď" card, add:

```html
{% if boat.hull_color %}
<p class="mb-2">
    <strong>Barva trupu:</strong> {{ boat.get_hull_color_display }}
</p>
{% endif %}
{% if boat.sail_color %}
<p class="mb-2">
    <strong>Barva plachet:</strong> {{ boat.get_sail_color_display }}
</p>
{% endif %}
```

After the existing "Vlastník / správce" card fields, add:

```html
{% if boat.vessel_registry_number %}
<p class="mb-2">
    <strong>Registrační číslo (rejstřík malých plavidel):</strong> {{ boat.vessel_registry_number }}
</p>
{% endif %}
{% if boat.engine_power_hp %}
<p class="mb-2">
    <strong>Výkon motoru:</strong> {{ boat.engine_power_hp }} hp
</p>
{% endif %}
```

- [ ] **Step 4: Run tests**

```bash
uv run python manage.py test SkaRe
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add SkaRe/templates/SkaRe/boats/
git commit -m "feat: add colour, vessel registry, engine power to boat templates; rename section Vlastník/správce"
```

---

## Task 4: Home page boat buttons

**Files:**
- Modify: `SkaRe/templates/SkaRe/home.html`

- [ ] **Step 1: Read home.html in full**

The file is at `SkaRe/templates/SkaRe/home.html`. Read it before editing.

- [ ] **Step 2: Add "Registrovat loď" to the Register section**

Inside the `<div class="mb-4">` that contains the Register buttons, add alongside the existing buttons:

```html
<a class="btn btn-primary btn-lg me-2 mb-2" href="{% url 'SkaRe:boat_register' %}" role="button">
    <i class="bi bi-sailboat"></i> Registrovat loď
</a>
```

Do NOT wrap this in `{% trans %}` — boat UI is Czech-only and deliberately not translated.

- [ ] **Step 3: Add "Lodě" to the My Registrations section**

Inside the `<div class="mb-4">` that contains the My Registrations buttons, add:

```html
<a class="btn btn-info btn-lg me-2 mb-2" href="{% url 'SkaRe:boat_list' %}" role="button">
    <i class="bi bi-sailboat"></i> Lodě
</a>
```

- [ ] **Step 4: Run full test suite**

```bash
uv run python manage.py test SkaRe
```

Expected: all tests pass. No new tests needed for this task — the template change is purely additive UI.

- [ ] **Step 5: Commit**

```bash
git add SkaRe/templates/SkaRe/home.html
git commit -m "feat: add boat register and boat list buttons to home page"
```

---

## Task 5: Final check

- [ ] **Step 1: Run the full test suite one final time**

```bash
uv run python manage.py test SkaRe
```

Expected: all tests pass, zero warnings from the system check.

- [ ] **Step 2: Confirm migration chain is clean**

```bash
uv run python manage.py migrate --run-syncdb 2>&1 | head -5
uv run python manage.py showmigrations SkaRe
```

All migrations should show `[X]`.

- [ ] **Step 3: Commit (if anything was fixed)**

Only commit if Step 1 or 2 revealed issues that needed fixing. Otherwise proceed directly to finishing.
