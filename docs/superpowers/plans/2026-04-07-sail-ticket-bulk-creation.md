# Sail Ticket Bulk Creation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the incremental ticket creation flow with a full-reset bulk creation that derives ticket codes from boat sail numbers, requires a confirmation step, and deletes all existing tickets before creating new ones.

**Architecture:** A standalone `_build_ticket_plan()` helper builds the full set of unsaved `SailTicket` instances (tested independently), the `ticket_create_bulk` view gains a two-step POST flow (preview → confirm), and the existing template gains a preview-mode block.

**Tech Stack:** Django 6.0, Python 3.x, Bootstrap 5 (existing), `uv run manage.py test`

---

## File Map

| Action | Path | Responsibility |
|--------|------|---------------|
| Modify | `SkaRe/views/tickets.py` | Add `_extract_numeric`, `_build_ticket_plan`; rewrite `ticket_create_bulk`; remove `_generate_codes` |
| Modify | `SkaRe/templates/SkaRe/tickets/create_bulk.html` | Add preview-mode block with per-category tables and confirm button |
| Create | `SkaRe/tests/test_ticket_bulk.py` | Unit tests for helpers + integration tests for the view |

No new URLs, models, forms, or migrations required.

---

## Task 1: Unit tests for `_extract_numeric` and `_build_ticket_plan`

**Files:**
- Create: `SkaRe/tests/test_ticket_bulk.py`

- [ ] **Step 1.1: Create the test file with unit tests**

Create `SkaRe/tests/test_ticket_bulk.py`:

```python
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from SkaRe.models import SailTicket, SailTicketLog, Boat, BoatClass
from SkaRe.views.tickets import _extract_numeric, _build_ticket_plan


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_infodesk():
    user = User.objects.create_user(username='desk', password='pw')
    group, _ = Group.objects.get_or_create(name='InfoDesk')
    user.groups.add(group)
    return user


def _p550_class():
    bc, _ = BoatClass.objects.get_or_create(
        name='P550', defaults={'category': BoatClass.Category.SAIL, 'order': 1}
    )
    return bc


def _sail_class():
    bc, _ = BoatClass.objects.get_or_create(
        name='Laser', defaults={'category': BoatClass.Category.SAIL, 'order': 2}
    )
    return bc


def _other_class():
    bc, _ = BoatClass.objects.get_or_create(
        name='Motorboat', defaults={'category': BoatClass.Category.OTHER, 'order': 3}
    )
    return bc


def _make_boat(user, sail_number='', boat_class=None, name='Test Boat'):
    return Boat.objects.create(
        created_by=user,
        boat_class=boat_class or _p550_class(),
        sail_number=sail_number,
        name=name,
        contact_person='Leader',
        contact_phone='123456789',
    )


_NO_RESERVES = {
    SailTicket.Color.P550: 0,
    SailTicket.Color.SAIL: 0,
    SailTicket.Color.OTHER: 0,
}


# ── _extract_numeric ──────────────────────────────────────────────────────────

class ExtractNumericTest(TestCase):
    def test_digits_only(self):
        self.assertEqual(_extract_numeric('1234'), 1234)

    def test_country_code_prefix(self):
        self.assertEqual(_extract_numeric('CZE 1234'), 1234)

    def test_country_code_no_space(self):
        self.assertEqual(_extract_numeric('CZE1234'), 1234)

    def test_empty_string(self):
        self.assertIsNone(_extract_numeric(''))

    def test_no_digits(self):
        self.assertIsNone(_extract_numeric('CZE'))

    def test_zero_treated_as_none(self):
        self.assertIsNone(_extract_numeric('0'))

    def test_leading_zeros_still_zero(self):
        self.assertIsNone(_extract_numeric('00'))


# ── _build_ticket_plan ────────────────────────────────────────────────────────

class BuildTicketPlanTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('owner', password='pw')

    def test_boat_with_sail_number_gets_numeric_code(self):
        _make_boat(self.user, sail_number='CZE 1234')
        boats = Boat.objects.select_related('boat_class')
        plan = _build_ticket_plan(boats, _NO_RESERVES, 0)
        codes = [t.code for t in plan]
        self.assertIn('P550-1234', codes)

    def test_boat_without_sail_number_gets_sequential_code(self):
        _make_boat(self.user, sail_number='')
        boats = Boat.objects.select_related('boat_class')
        plan = _build_ticket_plan(boats, _NO_RESERVES, 0)
        codes = [t.code for t in plan]
        self.assertIn('P550-1', codes)

    def test_sail_numbered_boat_linked_to_ticket(self):
        boat = _make_boat(self.user, sail_number='CZE 5')
        boats = Boat.objects.select_related('boat_class')
        plan = _build_ticket_plan(boats, _NO_RESERVES, 0)
        ticket = next(t for t in plan if t.code == 'P550-5')
        self.assertEqual(ticket.boat, boat)

    def test_conflict_first_boat_keeps_number_second_gets_sequential(self):
        _make_boat(self.user, sail_number='CZE 1234', name='First')
        _make_boat(self.user, sail_number='1234', name='Second')
        boats = Boat.objects.select_related('boat_class').order_by('pk')
        plan = _build_ticket_plan(boats, _NO_RESERVES, 0)
        codes = [t.code for t in plan]
        self.assertIn('P550-1234', codes)
        self.assertIn('P550-1', codes)   # second boat → sequential (1 is first unused)
        self.assertEqual(len([c for c in codes if c.startswith('P550-')]), 2)

    def test_reserves_fill_unused_numbers_skipping_sail_numbers(self):
        _make_boat(self.user, sail_number='CZE 3')   # claims 3
        boats = Boat.objects.select_related('boat_class')
        plan = _build_ticket_plan(boats, {
            SailTicket.Color.P550: 2,
            SailTicket.Color.SAIL: 0,
            SailTicket.Color.OTHER: 0,
        }, 0)
        codes = [t.code for t in plan]
        self.assertIn('P550-3', codes)   # from sail number
        self.assertIn('P550-1', codes)   # reserve (skips nothing before 3 except 1,2 unused)
        self.assertIn('P550-2', codes)   # reserve
        self.assertNotIn('P550-4', codes)

    def test_reserve_tickets_have_no_boat(self):
        boats = Boat.objects.none()
        plan = _build_ticket_plan(boats, {
            SailTicket.Color.P550: 2,
            SailTicket.Color.SAIL: 0,
            SailTicket.Color.OTHER: 0,
        }, 0)
        for ticket in plan:
            self.assertIsNone(ticket.boat)

    def test_spare_tickets_sequential_from_1(self):
        boats = Boat.objects.none()
        plan = _build_ticket_plan(boats, _NO_RESERVES, 3)
        spare = [t for t in plan if t.color == SailTicket.Color.SPARE]
        self.assertEqual([t.code for t in spare], ['SPARE-1', 'SPARE-2', 'SPARE-3'])

    def test_spare_tickets_have_no_boat(self):
        boats = Boat.objects.none()
        plan = _build_ticket_plan(boats, _NO_RESERVES, 2)
        for ticket in plan:
            if ticket.color == SailTicket.Color.SPARE:
                self.assertIsNone(ticket.boat)

    def test_spare_independent_of_other_categories(self):
        _make_boat(self.user, sail_number='1')   # P550-1 claimed
        boats = Boat.objects.select_related('boat_class')
        plan = _build_ticket_plan(boats, _NO_RESERVES, 2)
        spare = [t for t in plan if t.color == SailTicket.Color.SPARE]
        self.assertEqual([t.code for t in spare], ['SPARE-1', 'SPARE-2'])

    def test_from_sail_number_annotation_true_for_numbered_boat(self):
        _make_boat(self.user, sail_number='CZE 7')
        boats = Boat.objects.select_related('boat_class')
        plan = _build_ticket_plan(boats, _NO_RESERVES, 0)
        ticket = next(t for t in plan if t.code == 'P550-7')
        self.assertTrue(ticket._from_sail_number)

    def test_from_sail_number_annotation_false_for_unnumbered_boat(self):
        _make_boat(self.user, sail_number='')
        boats = Boat.objects.select_related('boat_class')
        plan = _build_ticket_plan(boats, _NO_RESERVES, 0)
        self.assertFalse(plan[0]._from_sail_number)

    def test_from_sail_number_annotation_false_for_reserve(self):
        boats = Boat.objects.none()
        plan = _build_ticket_plan(boats, {
            SailTicket.Color.P550: 1,
            SailTicket.Color.SAIL: 0,
            SailTicket.Color.OTHER: 0,
        }, 0)
        self.assertFalse(plan[0]._from_sail_number)

    def test_categories_are_independent(self):
        """P550 and SAIL sail numbers don't conflict with each other."""
        _make_boat(self.user, sail_number='5', boat_class=_p550_class(), name='P550 Boat')
        _make_boat(self.user, sail_number='5', boat_class=_sail_class(), name='SAIL Boat')
        boats = Boat.objects.select_related('boat_class')
        plan = _build_ticket_plan(boats, _NO_RESERVES, 0)
        codes = [t.code for t in plan]
        self.assertIn('P550-5', codes)
        self.assertIn('SAIL-5', codes)
```

- [ ] **Step 1.2: Run the tests — expect ImportError (functions not yet defined)**

```
uv run manage.py test SkaRe.tests.test_ticket_bulk --failfast
```

Expected: `ImportError: cannot import name '_extract_numeric' from 'SkaRe.views.tickets'`

- [ ] **Step 1.3: Implement `_extract_numeric` and `_build_ticket_plan` in `SkaRe/views/tickets.py`**

Open `SkaRe/views/tickets.py`. Remove the `_generate_codes` function entirely (lines 35–49). Add the following two functions in its place (after `_boat_color`, before `COLOR_PREFIX`):

```python
import re  # add to top-of-file imports

def _extract_numeric(sail_number):
    """Extract the integer from a sail number string, e.g. 'CZE 1234' → 1234.

    Returns None if no digits are present or the result is zero.
    """
    digits = re.sub(r'\D', '', sail_number)
    n = int(digits) if digits else 0
    return n if n > 0 else None


def _build_ticket_plan(boats, reserve_counts, spare_count):
    """Return a list of unsaved SailTicket instances representing the full plan.

    Each ticket is annotated with a ``_from_sail_number`` bool attribute.

    Args:
        boats: queryset of Boat objects, select_related('boat_class')
        reserve_counts: dict mapping SailTicket.Color → int (reserves per category)
        spare_count: int — number of SPARE tickets to generate
    """
    boat_groups = {
        SailTicket.Color.P550: [],
        SailTicket.Color.SAIL: [],
        SailTicket.Color.OTHER: [],
    }
    for boat in boats.order_by('pk'):
        color = _boat_color(boat)
        boat_groups[color].append(boat)

    tickets = []

    for color, color_boats in boat_groups.items():
        prefix = COLOR_PREFIX[color]
        claimed = {}    # int number → Boat
        unnumbered = []

        for boat in color_boats:
            num = _extract_numeric(boat.sail_number) if boat.sail_number else None
            if num is not None and num not in claimed:
                claimed[num] = boat
            else:
                unnumbered.append(boat)

        total_sequential = len(unnumbered) + reserve_counts.get(color, 0)
        sequential = []
        n = 1
        while len(sequential) < total_sequential:
            if n not in claimed:
                sequential.append(n)
            n += 1

        for num, boat in claimed.items():
            t = SailTicket(code=f'{prefix}-{num}', color=color, boat=boat)
            t._from_sail_number = True
            tickets.append(t)

        for i, boat in enumerate(unnumbered):
            t = SailTicket(code=f'{prefix}-{sequential[i]}', color=color, boat=boat)
            t._from_sail_number = False
            tickets.append(t)

        for i in range(len(unnumbered), total_sequential):
            t = SailTicket(code=f'{prefix}-{sequential[i]}', color=color)
            t._from_sail_number = False
            tickets.append(t)

    for i in range(1, spare_count + 1):
        t = SailTicket(code=f'SPARE-{i}', color=SailTicket.Color.SPARE)
        t._from_sail_number = False
        tickets.append(t)

    return tickets
```

Also add `import re` to the imports at the top of `SkaRe/views/tickets.py`.

- [ ] **Step 1.4: Run the unit tests — expect all to pass**

```
uv run manage.py test SkaRe.tests.test_ticket_bulk.ExtractNumericTest SkaRe.tests.test_ticket_bulk.BuildTicketPlanTest --verbosity=2
```

Expected: all tests PASS.

- [ ] **Step 1.5: Commit**

```bash
git add SkaRe/views/tickets.py SkaRe/tests/test_ticket_bulk.py
git commit -m "feat: add _extract_numeric and _build_ticket_plan helpers with tests"
```

---

## Task 2: Integration tests for the view, then update the view

**Files:**
- Modify: `SkaRe/tests/test_ticket_bulk.py` (add view tests)
- Modify: `SkaRe/views/tickets.py` (rewrite `ticket_create_bulk`)

- [ ] **Step 2.1: Add view integration tests to `SkaRe/tests/test_ticket_bulk.py`**

Append the following class to the end of `SkaRe/tests/test_ticket_bulk.py`:

```python
class TicketCreateBulkViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user('owner', password='pw')

    def _post(self, extra=None):
        data = {
            'p550_reserves': 0,
            'sail_reserves': 0,
            'other_reserves': 0,
            'spare_count': 0,
        }
        if extra:
            data.update(extra)
        return self.client.post(reverse('SkaRe:ticket_create_bulk'), data)

    def test_get_renders_form_no_plan(self):
        response = self.client.get(reverse('SkaRe:ticket_create_bulk'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertNotIn('plan', response.context)

    def test_post_step1_renders_preview_without_db_changes(self):
        response = self._post({'p550_reserves': 2})
        self.assertEqual(response.status_code, 200)
        self.assertIn('plan', response.context)
        self.assertEqual(SailTicket.objects.count(), 0)

    def test_post_step1_plan_in_context_matches_reserves(self):
        response = self._post({'p550_reserves': 3})
        plan = response.context['plan']
        p550_tickets = [t for t in plan if t.color == SailTicket.Color.P550]
        self.assertEqual(len(p550_tickets), 3)

    def test_post_step2_deletes_existing_tickets(self):
        SailTicket.objects.create(code='OLD-001', color=SailTicket.Color.SPARE)
        self._post({'confirm': '1', 'spare_count': 1})
        self.assertFalse(SailTicket.objects.filter(code='OLD-001').exists())

    def test_post_step2_deletes_logs_via_cascade(self):
        ticket = SailTicket.objects.create(code='OLD-001', color=SailTicket.Color.SPARE)
        SailTicketLog.objects.create(ticket=ticket, status=SailTicket.Status.ASHORE)
        self._post({'confirm': '1'})
        self.assertEqual(SailTicketLog.objects.count(), 0)

    def test_post_step2_creates_correct_tickets(self):
        response = self._post({'confirm': '1', 'p550_reserves': 2, 'spare_count': 1})
        self.assertRedirects(response, reverse('SkaRe:ticket_list'))
        self.assertEqual(SailTicket.objects.count(), 3)
        codes = set(SailTicket.objects.values_list('code', flat=True))
        self.assertIn('P550-1', codes)
        self.assertIn('P550-2', codes)
        self.assertIn('SPARE-1', codes)

    def test_post_step2_zero_existing_tickets_works(self):
        self.assertEqual(SailTicket.objects.count(), 0)
        self._post({'confirm': '1', 'spare_count': 2})
        self.assertEqual(SailTicket.objects.count(), 2)

    def test_post_step2_assigns_sail_number_as_code(self):
        _make_boat(self.owner, sail_number='CZE 99', boat_class=_p550_class())
        self._post({'confirm': '1'})
        self.assertTrue(SailTicket.objects.filter(code='P550-99').exists())

    def test_post_step2_conflict_one_gets_number_other_gets_sequential(self):
        _make_boat(self.owner, sail_number='CZE 1234', name='First', boat_class=_p550_class())
        _make_boat(self.owner, sail_number='1234', name='Second', boat_class=_p550_class())
        self._post({'confirm': '1'})
        codes = set(SailTicket.objects.values_list('code', flat=True))
        self.assertIn('P550-1234', codes)
        self.assertIn('P550-1', codes)
        self.assertEqual(SailTicket.objects.count(), 2)

    def test_post_step2_redirects_to_ticket_list(self):
        response = self._post({'confirm': '1'})
        self.assertRedirects(response, reverse('SkaRe:ticket_list'))

    def test_get_requires_infodesk(self):
        self.client.logout()
        response = self.client.get(reverse('SkaRe:ticket_create_bulk'))
        self.assertNotEqual(response.status_code, 200)
```

- [ ] **Step 2.2: Run the new view tests — expect failures**

```
uv run manage.py test SkaRe.tests.test_ticket_bulk.TicketCreateBulkViewTest --failfast --verbosity=2
```

Expected: several FAILs (old view logic doesn't match new behaviour — e.g. `plan` not in context, no deletion on confirm).

- [ ] **Step 2.3: Rewrite `ticket_create_bulk` in `SkaRe/views/tickets.py`**

Replace the existing `ticket_create_bulk` function (lines 144–211) with:

```python
@infodesk_required
def ticket_create_bulk(request):
    if request.method == 'POST':
        form = BulkTicketCreateForm(request.POST)
        if form.is_valid():
            reserve_counts = {
                SailTicket.Color.P550: form.cleaned_data['p550_reserves'],
                SailTicket.Color.SAIL: form.cleaned_data['sail_reserves'],
                SailTicket.Color.OTHER: form.cleaned_data['other_reserves'],
            }
            spare_count = form.cleaned_data['spare_count']
            boats = Boat.objects.select_related('boat_class')
            plan = _build_ticket_plan(boats, reserve_counts, spare_count)

            if request.POST.get('confirm') == '1':
                with transaction.atomic():
                    SailTicket.objects.all().delete()
                    SailTicket.objects.bulk_create(plan)
                messages.success(request, _('%(n)d tickets created.') % {'n': len(plan)})
                return redirect('SkaRe:ticket_list')

            # Step 1: show preview — group tickets by color for the template
            from collections import defaultdict
            groups = defaultdict(list)
            for ticket in plan:
                groups[ticket.color].append(ticket)
            color_order = [
                SailTicket.Color.P550,
                SailTicket.Color.SAIL,
                SailTicket.Color.OTHER,
                SailTicket.Color.SPARE,
            ]
            plan_by_color = [
                (SailTicket.Color(color).label, groups[color])
                for color in color_order
                if groups[color]
            ]
            return render(request, 'SkaRe/tickets/create_bulk.html', {
                'form': form,
                'plan': plan,
                'plan_by_color': plan_by_color,
                'existing_ticket_count': SailTicket.objects.count(),
            })
    else:
        form = BulkTicketCreateForm()

    all_boats = Boat.objects.select_related('boat_class')
    boat_preview = {}
    for boat in all_boats:
        color = _boat_color(boat)
        boat_preview[color] = boat_preview.get(color, 0) + 1

    return render(request, 'SkaRe/tickets/create_bulk.html', {
        'form': form,
        'boat_preview': boat_preview,
        'existing_ticket_count': SailTicket.objects.count(),
    })
```

Move the `from collections import defaultdict` import to the top of the file with the other imports.

- [ ] **Step 2.4: Run all ticket bulk tests — expect all to pass**

```
uv run manage.py test SkaRe.tests.test_ticket_bulk --verbosity=2
```

Expected: all tests PASS.

- [ ] **Step 2.5: Run the full test suite to check for regressions**

```
uv run manage.py test --failfast
```

Expected: all tests PASS.

- [ ] **Step 2.6: Commit**

```bash
git add SkaRe/views/tickets.py SkaRe/tests/test_ticket_bulk.py
git commit -m "feat: rewrite ticket_create_bulk with full-reset logic and preview step"
```

---

## Task 3: Update the template for preview mode

**Files:**
- Modify: `SkaRe/templates/SkaRe/tickets/create_bulk.html`

- [ ] **Step 3.1: Replace the template with the new version supporting preview mode**

Replace the entire content of `SkaRe/templates/SkaRe/tickets/create_bulk.html` with:

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{% trans "Bulk Create Tickets" %} - SkaRe{% endblock %}

{% block content %}
<h1 class="mb-3"><i class="bi bi-plus-circle"></i> {% trans "Bulk Create Sail Tickets" %}</h1>
<a href="{% url 'SkaRe:ticket_list' %}" class="btn btn-outline-secondary btn-sm mb-3">
  <i class="bi bi-arrow-left"></i> {% trans "All tickets" %}
</a>

{% if plan %}
{# ── Preview / confirmation mode ── #}
<div class="alert alert-danger">
  <i class="bi bi-exclamation-octagon-fill"></i>
  <strong>{% trans "Warning" %}</strong> —
  {% blocktrans with n=existing_ticket_count %}
    This will permanently delete all {{ n }} existing tickets and their logs. This cannot be undone.
  {% endblocktrans %}
</div>

{% for color_label, tickets in plan_by_color %}
<h5 class="mt-4">{{ color_label }} <span class="badge bg-secondary">{{ tickets|length }}</span></h5>
<table class="table table-sm table-bordered">
  <thead class="table-light">
    <tr>
      <th>{% trans "Code" %}</th>
      <th>{% trans "Boat" %}</th>
      <th>{% trans "Number source" %}</th>
    </tr>
  </thead>
  <tbody>
    {% for ticket in tickets %}
    <tr>
      <td><code>{{ ticket.code }}</code></td>
      <td>
        {% if ticket.boat %}
          {{ ticket.boat.name }}
          {% if ticket.boat.sail_number %}<span class="text-muted">({{ ticket.boat.sail_number }})</span>{% endif %}
        {% else %}
          <span class="text-muted">{% trans "Reserve — no boat" %}</span>
        {% endif %}
      </td>
      <td>
        {% if ticket._from_sail_number %}
          <span class="badge bg-primary">{% trans "From sail number" %}</span>
        {% else %}
          <span class="badge bg-secondary">{% trans "Sequential" %}</span>
        {% endif %}
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% endfor %}

<form method="post" class="mt-4">
  {% csrf_token %}
  {% for field in form %}<input type="hidden" name="{{ field.html_name }}" value="{{ field.value }}">{% endfor %}
  <input type="hidden" name="confirm" value="1">
  <a href="{% url 'SkaRe:ticket_create_bulk' %}" class="btn btn-outline-secondary me-2">
    <i class="bi bi-arrow-left"></i> {% trans "Back" %}
  </a>
  <button type="submit" class="btn btn-danger">
    <i class="bi bi-trash"></i> {% trans "Confirm and create tickets" %}
  </button>
</form>

{% else %}
{# ── Input form mode ── #}
{% if existing_ticket_count > 0 %}
<div class="alert alert-warning">
  <i class="bi bi-exclamation-triangle"></i>
  {% blocktrans with n=existing_ticket_count %}{{ n }} tickets already exist. Proceeding will delete them all.{% endblocktrans %}
</div>
{% endif %}

<div class="card mb-4">
  <div class="card-header">{% trans "Registered boats (all)" %}</div>
  <div class="card-body">
    <ul class="mb-0">
      {% for color, count in boat_preview.items %}<li>{{ color }}: {{ count }}</li>{% empty %}<li class="text-muted">{% trans "None" %}</li>{% endfor %}
    </ul>
  </div>
</div>

<form method="post">
  {% csrf_token %}
  {% for field in form %}
  <div class="mb-3">
    <label class="form-label fw-bold">{{ field.label }}</label>
    {{ field }}
    {% if field.help_text %}<div class="form-text">{{ field.help_text }}</div>{% endif %}
    {% for error in field.errors %}<div class="text-danger">{{ error }}</div>{% endfor %}
  </div>
  {% endfor %}
  <button type="submit" class="btn btn-warning">
    <i class="bi bi-eye"></i> {% trans "Preview tickets" %}
  </button>
</form>
{% endif %}
{% endblock %}
```

- [ ] **Step 3.2: Run the Django system check**

```
uv run manage.py check
```

Expected: no errors.

- [ ] **Step 3.3: Manually verify the two-step flow**

Start the dev server (`uv run manage.py runserver`) and:
1. Navigate to `/infodesk/tickets/create-bulk/` as an InfoDesk user.
2. Enter some reserve counts and click "Preview tickets" — confirm the plan table renders correctly with correct codes, boat names, and badges.
3. Click "Back" — confirm you return to the form.
4. Click "Preview tickets" again, then "Confirm and create tickets" — confirm redirect to the ticket list with a success message.
5. Check the ticket list to verify the correct codes appear.

- [ ] **Step 3.4: Run the full test suite one final time**

```
uv run manage.py test --failfast
```

Expected: all tests PASS.

- [ ] **Step 3.5: Commit**

```bash
git add SkaRe/templates/SkaRe/tickets/create_bulk.html
git commit -m "feat: add preview/confirmation mode to bulk ticket creation template"
```

---

## Self-Review Notes

**Spec coverage check:**

| Spec requirement | Covered by |
|-----------------|-----------|
| Delete all existing SailTickets + logs on confirm | Task 2 view, integration tests |
| Sail number → extract numeric part | Task 1 `_extract_numeric` |
| Zero sail number treated as unnumbered | Task 1 `test_zero_treated_as_none` |
| First-come-first-served conflict resolution (ordered by pk) | Task 1 `test_conflict_*`, `boats.order_by('pk')` in helper |
| Unnumbered boats + reserves share sequential pool | Task 1 `test_reserves_fill_unused_numbers_skipping_sail_numbers` |
| SPARE: always SPARE-1..N, independent | Task 1 `test_spare_*` |
| No zero-padding on codes | Code format `f'{prefix}-{num}'` with bare int |
| `_build_ticket_plan` receives all boats (not filtered) | Task 2 view passes full `Boat.objects.select_related(...)` |
| Confirmation step before deletion | Task 2 step1/step2 split, template back button |
| Danger alert with ticket count | Task 3 template |
| Per-category tables with source badge | Task 3 template |
| Back link + confirm button | Task 3 template |
| Categories independent (P550-5 and SAIL-5 can both exist) | Task 1 `test_categories_are_independent` |
| `_from_sail_number` annotation for template badges | Task 1 `test_from_sail_number_*`, Task 3 template |
