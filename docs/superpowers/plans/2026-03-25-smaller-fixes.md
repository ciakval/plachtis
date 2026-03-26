# Smaller Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** (A) Fix boat form field placement and convert sail registry lookup from blur-trigger to button; (B) split hat count into L/XL and S/M sizes across participant registration.

**Architecture:** Tasks A and B are fully independent — no shared files except `views.py`. A is purely JS + template + one view method. B is model + migration + 4 form classes + 4 templates + 1 view + 1 template + translations. Run tests after every commit.

**Tech Stack:** Django 6.0, Python 3.12, `uv` (all Python commands: `uv run python manage.py ...`), vanilla JS, Bootstrap 5, gettext (`.po`/`.mo` files in `locale/cs/LC_MESSAGES/`).

**Starting state:** 79 tests passing. Last migration: `0018_boat_phase_1_1_fields`.

**Spec:** `docs/superpowers/specs/2026-03-25-smaller-fixes.md`

---

## File Map

| File | Task | Change |
|------|------|--------|
| `SkaRe/templates/SkaRe/boats/form.html` | A1, A2 | Move two field blocks; add sail-lookup button + error div |
| `SkaRe/static/SkaRe/js/boat-form.js` | A2, A3 | Remove blur listener; add click handler; add contact_phone fill |
| `SkaRe/views.py` | A3, B7 | `boat_my_unit`: add contact_phone; `list_merchandise`: split hat totals |
| `SkaRe/tests/test_boat_views.py` | A3 | Add contact_phone assertion to `MyUnitViewTest` |
| `SkaRe/models.py` | B1 | Add `small_hat_count`; update `hat_count` verbose names |
| `SkaRe/migrations/0019_hat_size_split.py` | B2 | Auto-generated; adds `small_hat_count` to unit + individual_participant |
| `SkaRe/forms.py` | B3 | Add `small_hat_count` to `UnitRegistrationForm`, `IndividualParticipantRegistrationForm` |
| `SkaRe/views.py` (inline forms) | B3 | Add `small_hat_count` to `UnitEditForm`, `IndividualParticipantEditForm` |
| `SkaRe/templates/SkaRe/register_unit.html` | B4 | Add `small_hat_count` field |
| `SkaRe/templates/SkaRe/edit_unit.html` | B4 | Add `small_hat_count` field |
| `SkaRe/templates/SkaRe/register_individual_participant.html` | B4 | Add `small_hat_count` field |
| `SkaRe/templates/SkaRe/edit_individual_participant.html` | B4 | Add `small_hat_count` field |
| `SkaRe/templates/SkaRe/list_merchandise.html` | B5 | Split Hats column into L/XL + S/M |
| `SkaRe/tests/test_boat_views.py` | B5 | New `MerchandiseViewTest` class |
| `locale/cs/LC_MESSAGES/django.po` | B6 | Replace old hat msgids; add L/XL + S/M entries |

---

## Task 1: Move vessel_registry_number and engine_power_hp to the Boat card

**Files:**
- Modify: `SkaRe/templates/SkaRe/boats/form.html`

- [ ] **Step 1: Read form.html in full before editing**

Read `SkaRe/templates/SkaRe/boats/form.html`. Note that lines 163–183 hold the `vessel_registry_number` and `engine_power_hp` row inside the "Owner / Manager" card. The "Boat" card ends at approximately line 109 (closing `</div>` before the Owner card).

- [ ] **Step 2: Move the field row**

Cut the entire `<div class="row">` block containing `vessel_registry_number` and `engine_power_hp` (currently the last row inside the Owner card body). Paste it as the last row inside the Boat card body, after the hull/sail colour row (which ends around line 107).

After the move the Boat card should end with these three rows (in order):
1. sail_area row
2. hull_color / sail_color row
3. vessel_registry_number / engine_power_hp row ← moved here

The Owner card body should then contain only: harbor_number/harbor_name row + contact_person/contact_phone row.

- [ ] **Step 3: Verify the page renders**

```bash
uv run python manage.py check
```

Expected: `System check identified no issues (0 silenced)`.

- [ ] **Step 4: Commit**

```bash
git add SkaRe/templates/SkaRe/boats/form.html
git commit -m "fix: move vessel_registry_number and engine_power_hp to Boat card"
```

---

## Task 2: Sail registry lookup — blur → button

**Files:**
- Modify: `SkaRe/templates/SkaRe/boats/form.html`
- Modify: `SkaRe/static/SkaRe/js/boat-form.js`

No new tests — the sail-lookup API endpoint already has full coverage in `SkaRe/tests/test_boat_views.py::SailLookupViewTest`. The JS change is frontend-only.

- [ ] **Step 1: Read boat-form.js in full**

Read `SkaRe/static/SkaRe/js/boat-form.js`. Understand the existing structure: `fillIfEmpty`, `selectBoatClassByName`, the blur listener (lines 28–50), and the unit prefill button handler (lines 52–69).

- [ ] **Step 2: Update form.html — add button + error div**

In `SkaRe/templates/SkaRe/boats/form.html`, find the closing `</div>` of the sail_number/name row (the `<div class="row">` containing `sail_number` and `name`). Directly after it (still inside the Boat card body), insert:

```html
<div class="mb-3">
    <button type="button" id="btn-sail-lookup" class="btn btn-secondary">
        <i class="bi bi-search"></i> Vyhledat v registru plachet
    </button>
    <div id="sail-lookup-error" class="text-danger mt-1" style="display:none;"></div>
</div>
```

- [ ] **Step 3: Replace boat-form.js sail number handling**

In `SkaRe/static/SkaRe/js/boat-form.js`:

a) **Delete** the entire blur listener block (currently lines 28–50):
```js
// Sail number lookup on blur
const sailNumberField = document.getElementById('id_sail_number');
if (sailNumberField) {
    sailNumberField.addEventListener('blur', function () {
        ...
    });
}
```

b) **Replace it** with the following click handler. Place it where the blur listener was:

```js
// Sail number registry lookup button
const sailLookupBtn = document.getElementById('btn-sail-lookup');
const sailLookupError = document.getElementById('sail-lookup-error');

if (sailLookupBtn) {
    sailLookupBtn.addEventListener('click', function () {
        const q = document.getElementById('id_sail_number').value.trim();

        // Reset error state
        sailLookupError.textContent = '';
        sailLookupError.style.display = 'none';

        sailLookupBtn.disabled = true;

        fetch(`/boats/api/sail-lookup/?q=${encodeURIComponent(q)}`)
            .then(response => {
                if (response.status === 404) {
                    sailLookupError.textContent = 'Plachetní číslo nebylo v registru nalezeno.';
                    sailLookupError.style.display = '';
                    return null;
                }
                if (!response.ok) {
                    sailLookupError.textContent = 'Registr plachet je nedostupný.';
                    sailLookupError.style.display = '';
                    return null;
                }
                return response.json();
            })
            .then(data => {
                if (!data) return;

                // Overwrite boat fields regardless of current content
                document.getElementById('id_name').value = data.boat_name || '';
                document.getElementById('id_class_supplement').value = data.subtype || '';
                document.getElementById('id_sail_area').value = data.sail_area || '';

                // Overwrite boat class select
                const select = document.getElementById('id_boat_class');
                if (select && data.class_name) {
                    select.value = '';
                    const lower = data.class_name.toLowerCase();
                    for (const option of select.options) {
                        if (option.text.toLowerCase().includes(lower)) {
                            select.value = option.value;
                            break;
                        }
                    }
                }
                // Do NOT fill harbor_number, harbor_name, contact_person — owner fields
            })
            .catch(() => {
                sailLookupError.textContent = 'Registr plachet je nedostupný.';
                sailLookupError.style.display = '';
            })
            .finally(() => {
                sailLookupBtn.disabled = false;
            });
    });
}
```

- [ ] **Step 4: Run tests**

```bash
uv run python manage.py test SkaRe
```

Expected: 79 tests pass.

- [ ] **Step 5: Commit**

```bash
git add SkaRe/templates/SkaRe/boats/form.html SkaRe/static/SkaRe/js/boat-form.js
git commit -m "feat: convert sail registry lookup from blur to explicit button"
```

---

## Task 3: Unit prefill — add contact_phone

**Files:**
- Modify: `SkaRe/views.py`
- Modify: `SkaRe/static/SkaRe/js/boat-form.js`
- Modify: `SkaRe/tests/test_boat_views.py`

- [ ] **Step 1: Write the failing test**

In `SkaRe/tests/test_boat_views.py`, find `MyUnitViewTest.test_returns_unit_data` (around line 97). Add a new test method to the same class:

```python
def test_returns_contact_phone(self):
    self._create_unit()
    url = reverse('SkaRe:boat_my_unit')
    response = self.client.get(url)
    self.assertEqual(response.status_code, 200)
    data = json.loads(response.content)
    self.assertIn('contact_phone', data)
    self.assertEqual(data['contact_phone'], '+420123456789')
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run python manage.py test SkaRe.tests.test_boat_views.MyUnitViewTest.test_returns_contact_phone
```

Expected: FAIL — `'contact_phone' not found in response data` (or KeyError).

- [ ] **Step 3: Update boat_my_unit view**

In `SkaRe/views.py`, find `boat_my_unit` (around line 1267). Add `contact_phone` to the `JsonResponse`:

```python
return JsonResponse({
    'harbor_number': unit.entity.scout_unit_evidence_id,
    'harbor_name': unit.entity.scout_unit_name,
    'contact_person': unit.contact_person_name,
    'contact_phone': unit.entity.contact_phone,
})
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run python manage.py test SkaRe.tests.test_boat_views.MyUnitViewTest
```

Expected: all `MyUnitViewTest` tests pass.

- [ ] **Step 5: Update boat-form.js unit prefill handler**

In `SkaRe/static/SkaRe/js/boat-form.js`, find the unit prefill handler (the `then(data => { ... })` block inside the `btn-fill-from-unit` click listener). Add one line after the three existing `fillIfEmpty` calls:

```js
fillIfEmpty('id_contact_phone', data.contact_phone);
```

- [ ] **Step 6: Run full test suite**

```bash
uv run python manage.py test SkaRe
```

Expected: 79 tests pass (+ the new one = 80).

- [ ] **Step 7: Commit**

```bash
git add SkaRe/views.py SkaRe/static/SkaRe/js/boat-form.js SkaRe/tests/test_boat_views.py
git commit -m "feat: include contact_phone in my-unit prefill response"
```

---

## Task 4: Hat size split — model + migration

**Files:**
- Modify: `SkaRe/models.py`
- Create: `SkaRe/migrations/0019_hat_size_split.py` (auto-generated)
- Modify: `SkaRe/tests/test_boat_models.py` (add hat field tests; no separate file exists for unit/participant models)

- [ ] **Step 1: Write failing tests**

In `SkaRe/tests/test_boat_models.py`, add a new test class at the bottom of the file:

```python
from django.contrib.auth.models import User
from SkaRe.models import Entity, Unit, IndividualParticipant


class HatSizeSplitTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='htest', password='pw')
        self.entity = Entity.objects.create(
            created_by=self.user,
            contact_email='h@test.cz',
            contact_phone='123456789',
        )
        self.unit = Unit.objects.create(entity=self.entity, contact_person_name='Test')

    def test_unit_small_hat_count_defaults_to_zero(self):
        self.assertEqual(self.unit.small_hat_count, 0)

    def test_unit_hat_count_verbose_name(self):
        field = Unit._meta.get_field('hat_count')
        self.assertIn('L/XL', str(field.verbose_name))

    def test_unit_small_hat_count_verbose_name(self):
        field = Unit._meta.get_field('small_hat_count')
        self.assertIn('S/M', str(field.verbose_name))

    def test_unit_small_hat_count_stores_value(self):
        self.unit.small_hat_count = 3
        self.unit.save()
        self.unit.refresh_from_db()
        self.assertEqual(self.unit.small_hat_count, 3)

    def test_individual_participant_small_hat_count_defaults_to_zero(self):
        ip = IndividualParticipant.objects.create(
            entity=Entity.objects.create(
                created_by=self.user,
                contact_email='ip@test.cz',
                contact_phone='123456789',
            ),
            first_name='A', last_name='B',
            date_of_birth='2000-01-01',
        )
        self.assertEqual(ip.small_hat_count, 0)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run python manage.py test SkaRe.tests.test_boat_models.HatSizeSplitTest
```

Expected: FAIL — `AttributeError: type object 'Unit' has no attribute 'small_hat_count'` (or similar).

- [ ] **Step 3: Update models.py**

In `SkaRe/models.py`:

**On `Unit` model** (around line 361–364), update `hat_count` and add `small_hat_count`:

```python
# Hat fields
hat_count = models.PositiveBigIntegerField(
    default=0,
    help_text=_("Number of large hats (L/XL)"),
    verbose_name=_("Hat count (L/XL)"),
)
small_hat_count = models.PositiveBigIntegerField(
    default=0,
    help_text=_("Number of small hats (S/M)"),
    verbose_name=_("Hat count (S/M)"),
)
```

**On `IndividualParticipant` model** (around line 437–440), make the same two changes:

```python
# Hat fields
hat_count = models.PositiveBigIntegerField(
    default=0,
    help_text=_("Number of large hats (L/XL)"),
    verbose_name=_("Hat count (L/XL)"),
)
small_hat_count = models.PositiveBigIntegerField(
    default=0,
    help_text=_("Number of small hats (S/M)"),
    verbose_name=_("Hat count (S/M)"),
)
```

Do **not** touch `Organizer.wants_hat`.

- [ ] **Step 4: Generate migration**

```bash
uv run python manage.py makemigrations SkaRe --name hat_size_split
```

Inspect the generated file. It must:
- Add `small_hat_count` to `SkaRe_unit`
- Add `small_hat_count` to `SkaRe_individualparticipant`
- Depend on `0018_boat_phase_1_1_fields`
- Not touch `hat_count` (verbose_name changes don't generate migrations)

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run python manage.py test SkaRe.tests.test_boat_models.HatSizeSplitTest
```

Expected: all pass.

- [ ] **Step 6: Run full test suite**

```bash
uv run python manage.py test SkaRe
```

Expected: all tests pass (count increases by 5).

- [ ] **Step 7: Commit**

```bash
git add SkaRe/models.py SkaRe/migrations/0019_hat_size_split.py SkaRe/tests/test_boat_models.py
git commit -m "feat: add small_hat_count (S/M) to Unit and IndividualParticipant; rename hat_count to L/XL"
```

---

## Task 5: Hat forms — add small_hat_count to all four form classes

**Files:**
- Modify: `SkaRe/forms.py`
- Modify: `SkaRe/views.py`

No new tests — the form field merely exposes the model field; model field tests in Task 4 are sufficient.

- [ ] **Step 1: Update UnitRegistrationForm in forms.py**

In `SkaRe/forms.py`, find `UnitRegistrationForm` Meta class (around line 152). In `Meta.fields`, add `'small_hat_count'` immediately after `'hat_count'`:

```python
fields = [
    'contact_person_name',
    'backup_contact_phone',
    'boats_p550',
    'boats_sail',
    'boats_paddle',
    'boats_motor',
    'scarf_count',
    'hat_count',
    'small_hat_count',
    'accommodation_expectations',
    'estimated_accommodation_area',
]
```

In `Meta.widgets`, add:

```python
'small_hat_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
```

- [ ] **Step 2: Update IndividualParticipantRegistrationForm in forms.py**

Same change in `IndividualParticipantRegistrationForm` (around line 312). Add `'small_hat_count'` after `'hat_count'` in `Meta.fields` and add the same widget.

- [ ] **Step 3: Update UnitEditForm in views.py**

In `SkaRe/views.py`, find `class UnitEditForm` (inside `edit_unit` view, around line 223). Add `'small_hat_count'` after `'hat_count'` in `Meta.fields` and add the same widget in `Meta.widgets`.

- [ ] **Step 4: Update IndividualParticipantEditForm in views.py**

In `SkaRe/views.py`, find `class IndividualParticipantEditForm` (inside the individual participant edit view, around line 457). Same change as Step 3.

- [ ] **Step 5: Run full test suite**

```bash
uv run python manage.py test SkaRe
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add SkaRe/forms.py SkaRe/views.py
git commit -m "feat: expose small_hat_count in unit and individual participant forms"
```

---

## Task 6: Hat templates — add small_hat_count field to all four templates

**Files:**
- Modify: `SkaRe/templates/SkaRe/register_unit.html`
- Modify: `SkaRe/templates/SkaRe/edit_unit.html`
- Modify: `SkaRe/templates/SkaRe/register_individual_participant.html`
- Modify: `SkaRe/templates/SkaRe/edit_individual_participant.html`

No new tests — template rendering is visual.

- [ ] **Step 1: Update register_unit.html**

Read the file. Find the `hat_count` field block (around line 181). It's inside a `<div class="row">` with `scarf_count`. The pattern will be something like:

```html
<div class="col-md-6 mb-3">
    <label ...>{{ unit_form.hat_count.label }}</label>
    {{ unit_form.hat_count }}
    ...
</div>
```

Add a sibling `<div class="col-md-6 mb-3">` for `small_hat_count` in the same row:

```html
<div class="col-md-6 mb-3">
    <label for="{{ unit_form.small_hat_count.id_for_label }}" class="form-label">
        {{ unit_form.small_hat_count.label }}
    </label>
    {{ unit_form.small_hat_count }}
    {% if unit_form.small_hat_count.errors %}
        <div class="text-danger">{{ unit_form.small_hat_count.errors }}</div>
    {% endif %}
</div>
```

If `hat_count` is currently alone in a `col-md-6` (leaving the other half of the row empty), place `small_hat_count` in that empty half. If `hat_count` is in a `col-md-6` alongside `scarf_count`, add a new `<div class="row">` for the hat pair.

- [ ] **Step 2: Update edit_unit.html**

Same change — find the `hat_count` block (around line 190) and add `small_hat_count` alongside it using `unit_form.small_hat_count` as the form field reference.

- [ ] **Step 3: Update register_individual_participant.html**

Same change — find `hat_count` (around line 180). Form field reference is `form.small_hat_count`.

- [ ] **Step 4: Update edit_individual_participant.html**

Same change — find `hat_count` (around line 172). Form field reference is `participant_form.small_hat_count`.

- [ ] **Step 5: Run system check**

```bash
uv run python manage.py check
```

Expected: no issues.

- [ ] **Step 6: Commit**

```bash
git add SkaRe/templates/SkaRe/register_unit.html \
        SkaRe/templates/SkaRe/edit_unit.html \
        SkaRe/templates/SkaRe/register_individual_participant.html \
        SkaRe/templates/SkaRe/edit_individual_participant.html
git commit -m "feat: add small_hat_count field to unit and individual participant registration/edit templates"
```

---

## Task 7: Merchandise view + template — split hat column

**Files:**
- Modify: `SkaRe/views.py`
- Modify: `SkaRe/templates/SkaRe/list_merchandise.html`
- Modify: `SkaRe/tests/test_boat_views.py`

- [ ] **Step 1: Write failing tests**

At the bottom of `SkaRe/tests/test_boat_views.py`, add:

```python
class MerchandiseViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user(username='staff', password='pw', is_staff=True)
        self.client.login(username='staff', password='pw')

    def _make_entity(self, user):
        return Entity.objects.create(
            created_by=user,
            contact_email='x@x.cz',
            contact_phone='123456789',
        )

    def test_total_hats_large_in_context(self):
        entity = self._make_entity(self.staff)
        Unit.objects.create(entity=entity, contact_person_name='A', hat_count=3, small_hat_count=1)
        url = reverse('SkaRe:list_merchandise')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_hats_large', response.context)
        self.assertNotIn('total_hats', response.context)

    def test_total_hats_small_in_context(self):
        entity = self._make_entity(self.staff)
        Unit.objects.create(entity=entity, contact_person_name='A', hat_count=3, small_hat_count=2)
        url = reverse('SkaRe:list_merchandise')
        response = self.client.get(url)
        self.assertEqual(response.context['total_hats_small'], 2)

    def test_total_hats_large_includes_organizer_wants_hat(self):
        entity = self._make_entity(self.staff)
        Organizer.objects.create(
            entity=entity,
            first_name='O', last_name='R',
            date_of_birth='1990-01-01',
            wants_hat=True,
        )
        url = reverse('SkaRe:list_merchandise')
        response = self.client.get(url)
        self.assertGreaterEqual(response.context['total_hats_large'], 1)

    def test_organizers_not_in_total_hats_small(self):
        entity = self._make_entity(self.staff)
        Organizer.objects.create(
            entity=entity,
            first_name='O', last_name='R',
            date_of_birth='1990-01-01',
            wants_hat=True,
        )
        url = reverse('SkaRe:list_merchandise')
        response = self.client.get(url)
        self.assertEqual(response.context['total_hats_small'], 0)
```

You will need to ensure `Entity`, `Unit`, `Organizer` are imported at the top of `test_boat_views.py`. Check existing imports — `Entity` and `Unit` may not be there yet. Add as needed from `SkaRe.models`.

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run python manage.py test SkaRe.tests.test_boat_views.MerchandiseViewTest
```

Expected: FAIL — `total_hats_large` not in context / `total_hats` still present.

- [ ] **Step 3: Update list_merchandise view in views.py**

Find the `total_hats` block (around line 719) and replace it:

```python
total_hats_large = sum(item or 0 for item in [
    units.aggregate(total=Sum('hat_count'))['total'],
    individual_participants.aggregate(total=Sum('hat_count'))['total'],
    organizers.filter(wants_hat=True).count(),
])
total_hats_small = sum(item or 0 for item in [
    units.aggregate(total=Sum('small_hat_count'))['total'],
    individual_participants.aggregate(total=Sum('small_hat_count'))['total'],
    # organizers intentionally excluded — no small hat for organizers
])
```

In the `context` dict (around line 736), replace `'total_hats': total_hats` with:

```python
'total_hats_large': total_hats_large,
'total_hats_small': total_hats_small,
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run python manage.py test SkaRe.tests.test_boat_views.MerchandiseViewTest
```

Expected: all 4 pass.

- [ ] **Step 5: Update list_merchandise.html**

Read `SkaRe/templates/SkaRe/list_merchandise.html` in full. Make these changes:

**Table header** — replace `<th>{% trans "Hats" %}</th>` with:
```html
<th>Čepice L/XL</th>
<th>Čepice S/M</th>
```

**Unit rows** — replace `<td><strong>{{ unit.hat_count }}</strong></td>` with:
```html
<td><strong>{{ unit.hat_count }}</strong></td>
<td><strong>{{ unit.small_hat_count }}</strong></td>
```

**Individual participant rows** — same pattern:
```html
<td><strong>{{ participant.hat_count }}</strong></td>
<td><strong>{{ participant.small_hat_count }}</strong></td>
```

**Organizer rows** — replace the single hats `<td>` with:
```html
<td><strong>{% if organizer.wants_hat %}1{% else %}0{% endif %}</strong></td>
<td><strong>0</strong></td>
```

**Footer** — replace `<th><strong>{{ total_hats }}</strong></th>` with:
```html
<th><strong>{{ total_hats_large }}</strong></th>
<th><strong>{{ total_hats_small }}</strong></th>
```

**Statistics alert** (the `<span id="totalCount">` line) — this counts registrations, not hats. Leave it unchanged.

- [ ] **Step 6: Run full test suite**

```bash
uv run python manage.py test SkaRe
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add SkaRe/views.py SkaRe/templates/SkaRe/list_merchandise.html SkaRe/tests/test_boat_views.py
git commit -m "feat: split merchandise hat column into L/XL and S/M"
```

---

## Task 8: Czech translations

**Files:**
- Modify: `locale/cs/LC_MESSAGES/django.po`

- [ ] **Step 1: Read the relevant section of django.po**

Read `locale/cs/LC_MESSAGES/django.po`. Find the two hat entries (around lines 415–421):

```po
msgid "Number of hats"
msgstr "Počet čepic"

msgid "Hat count"
msgstr "Počet čepic"
```

- [ ] **Step 2: Replace the old entries with four new ones**

Delete both old entries and replace with:

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

Keep the surrounding `#:` location comment lines accurate — they should point to the new msgid locations in `models.py`. If the location comments are present, update them; if it's easier, simply remove the `#:` lines (Django will regenerate them on the next `makemessages` run).

- [ ] **Step 3: Compile messages**

```bash
uv run python manage.py compilemessages
```

Expected: no errors. A `django.mo` file is updated in `locale/cs/LC_MESSAGES/`.

- [ ] **Step 4: Run full test suite**

```bash
uv run python manage.py test SkaRe
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add locale/cs/LC_MESSAGES/django.po locale/cs/LC_MESSAGES/django.mo
git commit -m "i18n: update Czech translations for hat size split (L/XL, S/M)"
```

---

## Task 9: Final verification

- [ ] **Step 1: Run the full test suite**

```bash
uv run python manage.py test SkaRe
```

Expected: all tests pass, zero warnings.

- [ ] **Step 2: Check migration chain**

```bash
uv run python manage.py migrate --run-syncdb 2>&1 | head -5
uv run python manage.py showmigrations SkaRe
```

All migrations should show `[X]`.

- [ ] **Step 3: Confirm no open issues**

Review the spec (`docs/superpowers/specs/2026-03-25-smaller-fixes.md`) and verify each requirement is implemented.
