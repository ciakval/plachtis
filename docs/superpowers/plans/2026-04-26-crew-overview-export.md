# Crew Overview with CSV Export — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a staff-only all-crews overview page with filtering and statistics, a staff-accessible per-crew detail page, and CSV export at both the overview and single-crew levels.

**Architecture:** Four new view functions appended to `SkaRe/views/crews.py` (staff-only, `@login_required` + `is_staff` check); four new URL patterns in `SkaRe/urls.py`; two new templates under `SkaRe/templates/SkaRe/crews/`; one button added to the home page admin card. No model changes, no migrations.

**Tech Stack:** Django 6.0, Python `csv` module (already imported in `crews.py`), Bootstrap 5 + Bootstrap Icons (already used throughout), `uv run manage.py test` for tests.

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `SkaRe/views/crews.py` | Modify | Add `crew_all`, `crew_all_export_csv`, `crew_detail_staff`, `crew_export_single_csv` |
| `SkaRe/views/exports.py` | Read only | Source of `_csv_safe` helper (imported into crews.py) |
| `SkaRe/urls.py` | Modify | Register 4 new URL patterns |
| `SkaRe/templates/SkaRe/crews/all.html` | Create | Filterable overview table with stats bar |
| `SkaRe/templates/SkaRe/crews/detail_staff.html` | Create | Staff-facing crew detail with export button |
| `SkaRe/templates/SkaRe/registration/home.html` | Modify | Add "Crew Overview" button to admin card |
| `SkaRe/tests/test_crew_views.py` | Modify | Add `CrewAllViewTest` test class |

---

## Task 1: URLs, stub views, and access-control tests

**Files:**
- Modify: `SkaRe/urls.py`
- Modify: `SkaRe/views/crews.py`
- Modify: `SkaRe/tests/test_crew_views.py`

- [ ] **Step 1: Write failing access-control tests**

Append this class to `SkaRe/tests/test_crew_views.py` (after the last existing class):

```python
class CrewAllViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user('allstaff', password='pw', is_staff=True)
        self.regular = _make_user('allregular')
        self.user = _make_user('allowner')
        self.unit = _make_unit(self.user)
        self.helmsman = _make_person(self.unit)
        self.boat = _make_boat(self.user)
        self.crew = Crew.objects.create(
            boat=self.boat, category=Crew.CATEGORY_S, created_by=self.user
        )
        CrewMember.objects.create(
            crew=self.crew, role=CrewMember.ROLE_HELMSMAN,
            participant=Person.objects.get(pk=self.helmsman.pk),
        )

    # --- crew_all ---

    def test_crew_all_requires_login(self):
        url = reverse('SkaRe:crew_all')
        response = self.client.get(url)
        self.assertRedirects(response, f'/user/login/?next={url}', fetch_redirect_response=False)

    def test_crew_all_requires_staff(self):
        self.client.login(username='allregular', password='pw')
        response = self.client.get(reverse('SkaRe:crew_all'))
        self.assertEqual(response.status_code, 302)

    def test_crew_all_accessible_by_staff(self):
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(reverse('SkaRe:crew_all'))
        self.assertEqual(response.status_code, 200)

    # --- crew_all_export_csv ---

    def test_crew_all_export_requires_staff(self):
        self.client.login(username='allregular', password='pw')
        response = self.client.get(reverse('SkaRe:crew_all_export_csv'))
        self.assertEqual(response.status_code, 302)

    def test_crew_all_export_accessible_by_staff(self):
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(reverse('SkaRe:crew_all_export_csv'))
        self.assertEqual(response.status_code, 200)

    # --- crew_detail_staff ---

    def test_crew_detail_staff_requires_login(self):
        url = reverse('SkaRe:crew_detail_staff', kwargs={'crew_id': self.crew.pk})
        response = self.client.get(url)
        self.assertRedirects(response, f'/user/login/?next={url}', fetch_redirect_response=False)

    def test_crew_detail_staff_requires_staff(self):
        self.client.login(username='allregular', password='pw')
        response = self.client.get(
            reverse('SkaRe:crew_detail_staff', kwargs={'crew_id': self.crew.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_crew_detail_staff_accessible_by_staff(self):
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(
            reverse('SkaRe:crew_detail_staff', kwargs={'crew_id': self.crew.pk})
        )
        self.assertEqual(response.status_code, 200)

    # --- crew_export_single_csv ---

    def test_crew_export_single_requires_staff(self):
        self.client.login(username='allregular', password='pw')
        response = self.client.get(
            reverse('SkaRe:crew_export_single_csv', kwargs={'crew_id': self.crew.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_crew_export_single_accessible_by_staff(self):
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(
            reverse('SkaRe:crew_export_single_csv', kwargs={'crew_id': self.crew.pk})
        )
        self.assertEqual(response.status_code, 200)
```

- [ ] **Step 2: Run tests to confirm they fail with NoReverseMatch**

```bash
uv run manage.py test SkaRe.tests.test_crew_views.CrewAllViewTest --failfast
```

Expected: `NoReverseMatch` or `FAIL` — confirms the URLs don't exist yet.

- [ ] **Step 3: Add URL patterns to `SkaRe/urls.py`**

Insert after the existing `path('crews/<int:crew_id>/delete/', ...)` line (before the `# InfoDesk` comment):

```python
path('crews/all/', views.crew_all, name='crew_all'),
path('crews/all/export/csv/', views.crew_all_export_csv, name='crew_all_export_csv'),
path('crews/all/<int:crew_id>/', views.crew_detail_staff, name='crew_detail_staff'),
path('crews/all/<int:crew_id>/export/csv/', views.crew_export_single_csv, name='crew_export_single_csv'),
```

- [ ] **Step 4: Add stub views to `SkaRe/views/crews.py`**

Add this import at the top of `views/crews.py` (after the existing imports):

```python
from django.db.models import Count, Q
from .exports import _csv_safe
```

Then append these four stubs at the end of `views/crews.py`:

```python
@login_required
def crew_all(request):
    if not request.user.is_staff:
        messages.error(request, _('Staff access required.'))
        return redirect('SkaRe:home')
    return render(request, 'SkaRe/crews/all.html', {})


@login_required
def crew_all_export_csv(request):
    if not request.user.is_staff:
        messages.error(request, _('Staff access required.'))
        return redirect('SkaRe:home')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="crews.csv"'
    return response


@login_required
def crew_detail_staff(request, crew_id):
    if not request.user.is_staff:
        messages.error(request, _('Staff access required.'))
        return redirect('SkaRe:home')
    crew = get_object_or_404(Crew, id=crew_id)
    return render(request, 'SkaRe/crews/detail_staff.html', {'crew': crew})


@login_required
def crew_export_single_csv(request, crew_id):
    if not request.user.is_staff:
        messages.error(request, _('Staff access required.'))
        return redirect('SkaRe:home')
    crew = get_object_or_404(Crew, id=crew_id)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="crew_{crew_id}.csv"'
    return response
```

- [ ] **Step 5: Create minimal stub templates**

Create `SkaRe/templates/SkaRe/crews/all.html`:

```html
{% extends 'SkaRe/base.html' %}
{% block content %}stub{% endblock %}
```

Create `SkaRe/templates/SkaRe/crews/detail_staff.html`:

```html
{% extends 'SkaRe/base.html' %}
{% block content %}stub{% endblock %}
```

- [ ] **Step 6: Run access-control tests — all should pass**

```bash
uv run manage.py test SkaRe.tests.test_crew_views.CrewAllViewTest --failfast
```

Expected: All 10 tests pass.

- [ ] **Step 7: Commit**

```bash
git add SkaRe/urls.py SkaRe/views/crews.py \
        SkaRe/templates/SkaRe/crews/all.html \
        SkaRe/templates/SkaRe/crews/detail_staff.html \
        SkaRe/tests/test_crew_views.py
git commit -m "feat: add URL stubs and access-control for crew staff views"
```

---

## Task 2: `crew_all` view — filtering and context

**Files:**
- Modify: `SkaRe/views/crews.py` (replace `crew_all` stub)
- Modify: `SkaRe/tests/test_crew_views.py` (add tests to `CrewAllViewTest`)

- [ ] **Step 1: Add filtering and context tests**

Append these methods inside `CrewAllViewTest` in `SkaRe/tests/test_crew_views.py`:

```python
    def test_crew_all_context_contains_all_crews(self):
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(reverse('SkaRe:crew_all'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('crew_rows', response.context)
        self.assertEqual(len(response.context['crew_rows']), 1)

    def test_crew_all_filter_by_category(self):
        # Add a second crew in a different category
        boat2 = _make_boat(self.user)
        Crew.objects.create(boat=boat2, category=Crew.CATEGORY_R, created_by=self.user)
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(
            reverse('SkaRe:crew_all'), {'category': Crew.CATEGORY_S}
        )
        self.assertEqual(len(response.context['crew_rows']), 1)
        self.assertEqual(response.context['crew_rows'][0]['crew'].category, Crew.CATEGORY_S)

    def test_crew_all_filter_by_name(self):
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(reverse('SkaRe:crew_all'), {'q': 'Jan'})
        self.assertEqual(len(response.context['crew_rows']), 1)

    def test_crew_all_filter_by_name_no_match(self):
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(reverse('SkaRe:crew_all'), {'q': 'zzznomatch'})
        self.assertEqual(len(response.context['crew_rows']), 0)

    def test_crew_all_filter_by_boat_name(self):
        self.client.login(username='allstaff', password='pw')
        # _make_boat creates a boat named 'ALBATROS'
        response = self.client.get(reverse('SkaRe:crew_all'), {'q': 'ALBATROS'})
        self.assertEqual(len(response.context['crew_rows']), 1)

    def test_crew_all_context_has_stats(self):
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(reverse('SkaRe:crew_all'))
        self.assertIn('total_crews', response.context)
        self.assertIn('filtered_count', response.context)
        self.assertIn('category_stats_list', response.context)
        self.assertEqual(response.context['total_crews'], 1)
```

- [ ] **Step 2: Run new tests to confirm they fail**

```bash
uv run manage.py test SkaRe.tests.test_crew_views.CrewAllViewTest --failfast
```

Expected: Failures on the new context/filter tests (stub returns empty context `{}`).

- [ ] **Step 3: Replace the `crew_all` stub with the full implementation**

Replace the `crew_all` function in `SkaRe/views/crews.py`:

```python
@login_required
def crew_all(request):
    if not request.user.is_staff:
        messages.error(request, _('Staff access required.'))
        return redirect('SkaRe:home')

    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()

    qs = Crew.objects.select_related(
        'boat', 'boat__boat_class'
    ).prefetch_related('members__participant')

    if category:
        qs = qs.filter(category=category)
    if q:
        qs = qs.filter(
            Q(boat__name__icontains=q) |
            Q(members__participant__first_name__icontains=q) |
            Q(members__participant__last_name__icontains=q)
        ).distinct()

    total_crews = Crew.objects.count()
    category_counts = {
        row['category']: row['count']
        for row in Crew.objects.values('category').annotate(count=Count('id'))
    }
    category_stats_list = [
        (code, label, category_counts.get(code, 0))
        for code, label in Crew.CATEGORY_CHOICES
    ]

    crew_rows = []
    for crew in qs:
        helmsman = next(
            (m.participant for m in crew.members.all() if m.role == CrewMember.ROLE_HELMSMAN),
            None,
        )
        crew_rows.append({
            'crew': crew,
            'helmsman': helmsman,
            'member_count': len(list(crew.members.all())),
        })

    return render(request, 'SkaRe/crews/all.html', {
        'crew_rows': crew_rows,
        'total_crews': total_crews,
        'filtered_count': len(crew_rows),
        'category_stats_list': category_stats_list,
        'category_choices': Crew.CATEGORY_CHOICES,
        'q': q,
        'selected_category': category,
    })
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run manage.py test SkaRe.tests.test_crew_views.CrewAllViewTest --failfast
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add SkaRe/views/crews.py SkaRe/tests/test_crew_views.py
git commit -m "feat: implement crew_all view with filtering and stats"
```

---

## Task 3: `crews/all.html` template

**Files:**
- Modify: `SkaRe/templates/SkaRe/crews/all.html` (replace stub)

- [ ] **Step 1: Replace the stub template with the full implementation**

Replace the entire content of `SkaRe/templates/SkaRe/crews/all.html`:

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{% trans "All Crews" %} - SkaRe{% endblock %}

{% block content %}
<h1 class="mb-4"><i class="bi bi-people-fill"></i> {% trans "All Crews" %}</h1>

{# Stats bar #}
<div class="alert alert-info mb-4">
    <i class="bi bi-info-circle"></i>
    <strong>{% trans "Total" %}:</strong>
    {% if filtered_count != total_crews %}
        {{ filtered_count }} / {{ total_crews }} {% trans "crews" %}
    {% else %}
        {{ total_crews }} {% trans "crews" %}
    {% endif %}
    &nbsp;|&nbsp;
    {% for code, label, count in category_stats_list %}
        <span class="text-muted">{{ code }}: <strong>{{ count }}</strong></span>{% if not forloop.last %} &nbsp;{% endif %}
    {% endfor %}
</div>

{# Filter form #}
<form method="get" class="mb-3">
    <div class="row g-2 align-items-end">
        <div class="col-md-4">
            <label class="form-label fw-semibold"><i class="bi bi-search"></i> {% trans "Search" %}</label>
            <input type="text" name="q" value="{{ q }}" class="form-control"
                   placeholder="{% trans 'Member name or boat name...' %}">
        </div>
        <div class="col-md-3">
            <label class="form-label fw-semibold"><i class="bi bi-funnel"></i> {% trans "Category" %}</label>
            <select name="category" class="form-select">
                <option value="">{% trans "All categories" %}</option>
                {% for code, label in category_choices %}
                <option value="{{ code }}"{% if selected_category == code %} selected{% endif %}>{{ label }}</option>
                {% endfor %}
            </select>
        </div>
        <div class="col-md-auto d-flex gap-2 align-items-end">
            <button type="submit" class="btn btn-primary">
                <i class="bi bi-search"></i> {% trans "Search" %}
            </button>
            <a href="{% url 'SkaRe:crew_all' %}" class="btn btn-outline-secondary">{% trans "Clear" %}</a>
        </div>
    </div>
</form>

{# Export button #}
<div class="mb-3">
    <a href="{% url 'SkaRe:crew_all_export_csv' %}?q={{ q|urlencode }}&category={{ selected_category|urlencode }}"
       class="btn btn-outline-dark btn-sm">
        <i class="bi bi-download"></i> {% trans "Export CSV" %}
    </a>
</div>

{# Table #}
{% if crew_rows %}
<div class="table-responsive">
    <table class="table table-striped table-hover">
        <thead class="table-dark">
            <tr>
                <th>{% trans "Category" %}</th>
                <th>{% trans "Boat" %}</th>
                <th>{% trans "Helmsman" %}</th>
                <th>{% trans "Members" %}</th>
                <th></th>
            </tr>
        </thead>
        <tbody>
            {% for row in crew_rows %}
            <tr>
                <td><span class="badge bg-secondary">{{ row.crew.get_category_display }}</span></td>
                <td>{{ row.crew.boat }}</td>
                <td>{{ row.helmsman|default:"–" }}</td>
                <td>{{ row.member_count }}</td>
                <td>
                    <a href="{% url 'SkaRe:crew_detail_staff' crew_id=row.crew.pk %}"
                       class="btn btn-sm btn-outline-primary">
                        <i class="bi bi-eye"></i> {% trans "Detail" %}
                    </a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% else %}
<div class="alert alert-warning">
    <i class="bi bi-exclamation-triangle"></i> {% trans "No crews found." %}
</div>
{% endif %}

<div class="mt-4">
    <a class="btn btn-secondary" href="{% url 'SkaRe:home' %}">
        <i class="bi bi-house"></i> {% trans "Back to Home" %}
    </a>
</div>
{% endblock %}
```

- [ ] **Step 2: Verify the page renders without template errors**

```bash
uv run manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 3: Run full crew test suite**

```bash
uv run manage.py test SkaRe.tests.test_crew_views --failfast
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add SkaRe/templates/SkaRe/crews/all.html
git commit -m "feat: add crews/all.html overview template"
```

---

## Task 4: `crew_all_export_csv` — filtered CSV export

**Files:**
- Modify: `SkaRe/views/crews.py` (replace `crew_all_export_csv` stub)
- Modify: `SkaRe/tests/test_crew_views.py` (add tests to `CrewAllViewTest`)

- [ ] **Step 1: Add CSV export tests**

Append these methods inside `CrewAllViewTest` in `SkaRe/tests/test_crew_views.py`:

```python
    def test_crew_all_export_returns_csv(self):
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(reverse('SkaRe:crew_all_export_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_crew_all_export_contains_helmsman(self):
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(reverse('SkaRe:crew_all_export_csv'))
        content = response.content.decode('utf-8-sig')
        self.assertIn('Jan', content)
        self.assertIn(Crew.CATEGORY_S, content)

    def test_crew_all_export_filtered_by_category(self):
        # Add a second crew in category R — should not appear in S-filtered export
        boat2 = _make_boat(self.user)
        crew2 = Crew.objects.create(boat=boat2, category=Crew.CATEGORY_R, created_by=self.user)
        person2 = _make_person(self.unit, 'Petr', 'Druhý')
        CrewMember.objects.create(
            crew=crew2, role=CrewMember.ROLE_HELMSMAN,
            participant=Person.objects.get(pk=person2.pk),
        )
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(
            reverse('SkaRe:crew_all_export_csv'), {'category': Crew.CATEGORY_S}
        )
        content = response.content.decode('utf-8-sig')
        self.assertIn('Jan', content)
        self.assertNotIn('Petr', content)

    def test_crew_all_export_filename_with_category_filter(self):
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(
            reverse('SkaRe:crew_all_export_csv'), {'category': Crew.CATEGORY_S}
        )
        self.assertIn(f'crews_{Crew.CATEGORY_S}.csv', response['Content-Disposition'])

    def test_crew_all_export_filename_with_search_filter(self):
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(
            reverse('SkaRe:crew_all_export_csv'), {'q': 'Jan'}
        )
        self.assertIn('crews_search.csv', response['Content-Disposition'])
```

- [ ] **Step 2: Run tests to confirm new ones fail**

```bash
uv run manage.py test SkaRe.tests.test_crew_views.CrewAllViewTest --failfast
```

Expected: New CSV tests fail (stub returns empty CSV with no content).

- [ ] **Step 3: Replace `crew_all_export_csv` stub with full implementation**

Replace the `crew_all_export_csv` function in `SkaRe/views/crews.py`:

```python
@login_required
def crew_all_export_csv(request):
    if not request.user.is_staff:
        messages.error(request, _('Staff access required.'))
        return redirect('SkaRe:home')

    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()

    qs = Crew.objects.select_related('boat', 'boat__boat_class').prefetch_related('members__participant')
    if category:
        qs = qs.filter(category=category)
    if q:
        qs = qs.filter(
            Q(boat__name__icontains=q) |
            Q(members__participant__first_name__icontains=q) |
            Q(members__participant__last_name__icontains=q)
        ).distinct()

    if category:
        filename = f'crews_{category}.csv'
    elif q:
        filename = 'crews_search.csv'
    else:
        filename = 'crews.csv'

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow([
        'crew_id', 'category', 'boat_sail_number', 'boat_name',
        'boat_class', 'sail_area', 'role',
        'first_name', 'last_name', 'date_of_birth', 'scout_category',
        'participant_type', 'unit_name',
    ])

    members = (
        CrewMember.objects
        .filter(crew__in=qs)
        .select_related('crew', 'crew__boat', 'crew__boat__boat_class', 'participant')
        .order_by('crew__id', '-role')
    )

    for m in members:
        crew = m.crew
        person = m.participant
        participant_type = ''
        unit_name = ''
        if hasattr(person, 'regularparticipant'):
            participant_type = 'RegularParticipant'
            unit_name = person.regularparticipant.unit.entity.scout_unit_name
        elif hasattr(person, 'individualparticipant'):
            participant_type = 'IndividualParticipant'
        elif hasattr(person, 'organizer'):
            participant_type = 'Organizer'

        writer.writerow([
            crew.id,
            crew.category,
            _csv_safe(crew.boat.sail_number),
            _csv_safe(crew.boat.name),
            crew.boat.boat_class.name if crew.boat.boat_class else '',
            crew.boat.sail_area or '',
            m.role,
            _csv_safe(person.first_name),
            _csv_safe(person.last_name),
            person.date_of_birth,
            person.category or '',
            participant_type,
            _csv_safe(unit_name),
        ])

    return response
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run manage.py test SkaRe.tests.test_crew_views.CrewAllViewTest --failfast
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add SkaRe/views/crews.py SkaRe/tests/test_crew_views.py
git commit -m "feat: implement crew_all_export_csv with category and search filtering"
```

---

## Task 5: `crew_detail_staff` view and template

**Files:**
- Modify: `SkaRe/views/crews.py` (replace `crew_detail_staff` stub)
- Modify: `SkaRe/templates/SkaRe/crews/detail_staff.html` (replace stub)
- Modify: `SkaRe/tests/test_crew_views.py` (add tests to `CrewAllViewTest`)

- [ ] **Step 1: Add detail view tests**

Append these methods inside `CrewAllViewTest` in `SkaRe/tests/test_crew_views.py`:

```python
    def test_crew_detail_staff_shows_correct_crew(self):
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(
            reverse('SkaRe:crew_detail_staff', kwargs={'crew_id': self.crew.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['crew'], self.crew)

    def test_crew_detail_staff_shows_members(self):
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(
            reverse('SkaRe:crew_detail_staff', kwargs={'crew_id': self.crew.pk})
        )
        self.assertIn('members', response.context)
        self.assertEqual(response.context['members'].count(), 1)

    def test_crew_detail_staff_accessible_for_non_owner(self):
        # Staff can view any crew, not just their own
        other_user = _make_user('allother')
        other_unit = _make_unit(other_user)
        other_helm = _make_person(other_unit, 'Marie', 'Cizí')
        other_boat = _make_boat(other_user)
        other_crew = Crew.objects.create(
            boat=other_boat, category=Crew.CATEGORY_D, created_by=other_user
        )
        CrewMember.objects.create(
            crew=other_crew, role=CrewMember.ROLE_HELMSMAN,
            participant=Person.objects.get(pk=other_helm.pk),
        )
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(
            reverse('SkaRe:crew_detail_staff', kwargs={'crew_id': other_crew.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_crew_detail_staff_404_for_missing_crew(self):
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(
            reverse('SkaRe:crew_detail_staff', kwargs={'crew_id': 99999})
        )
        self.assertEqual(response.status_code, 404)
```

- [ ] **Step 2: Run tests to confirm new ones fail**

```bash
uv run manage.py test SkaRe.tests.test_crew_views.CrewAllViewTest --failfast
```

Expected: New detail tests fail (stub returns empty context).

- [ ] **Step 3: Replace `crew_detail_staff` stub with full implementation**

Replace the `crew_detail_staff` function in `SkaRe/views/crews.py`:

```python
@login_required
def crew_detail_staff(request, crew_id):
    if not request.user.is_staff:
        messages.error(request, _('Staff access required.'))
        return redirect('SkaRe:home')
    crew = get_object_or_404(Crew, id=crew_id)
    members = crew.members.select_related('participant').order_by('-role')
    return render(request, 'SkaRe/crews/detail_staff.html', {
        'crew': crew,
        'members': members,
    })
```

- [ ] **Step 4: Replace `detail_staff.html` stub with full template**

Replace the entire content of `SkaRe/templates/SkaRe/crews/detail_staff.html`:

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{% trans "Crew" %} – {{ crew }} - SkaRe{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-8 offset-md-2">
        <h1 class="mb-4"><i class="bi bi-people-fill"></i> {{ crew }}</h1>

        <div class="card mb-4">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">{% trans "Crew details" %}</h5>
            </div>
            <div class="card-body">
                <dl class="row mb-0">
                    <dt class="col-sm-4">{% trans "Boat" %}</dt>
                    <dd class="col-sm-8">
                        <a href="{% url 'SkaRe:boat_detail' boat_id=crew.boat.pk %}">{{ crew.boat }}</a>
                    </dd>
                    <dt class="col-sm-4">{% trans "Category" %}</dt>
                    <dd class="col-sm-8">{{ crew.get_category_display }}</dd>
                </dl>
            </div>
        </div>

        <div class="card mb-4">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">{% trans "Members" %}</h5>
            </div>
            <div class="card-body p-0">
                <table class="table mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>{% trans "Role" %}</th>
                            <th>{% trans "Name" %}</th>
                            <th>{% trans "Date of birth" %}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for member in members %}
                        <tr>
                            <td>{{ member.get_role_display }}</td>
                            <td>{{ member.participant }}</td>
                            <td>{{ member.participant.date_of_birth }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="d-flex gap-2 mb-3">
            <a href="{% url 'SkaRe:crew_export_single_csv' crew_id=crew.pk %}"
               class="btn btn-outline-dark">
                <i class="bi bi-download"></i> {% trans "Export CSV" %}
            </a>
        </div>

        <a href="{% url 'SkaRe:crew_all' %}" class="btn btn-secondary">
            <i class="bi bi-arrow-left"></i> {% trans "Back to Crew Overview" %}
        </a>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
uv run manage.py test SkaRe.tests.test_crew_views.CrewAllViewTest --failfast
```

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add SkaRe/views/crews.py \
        SkaRe/templates/SkaRe/crews/detail_staff.html \
        SkaRe/tests/test_crew_views.py
git commit -m "feat: implement crew_detail_staff view and template"
```

---

## Task 6: `crew_export_single_csv` — single-crew CSV export

**Files:**
- Modify: `SkaRe/views/crews.py` (replace `crew_export_single_csv` stub)
- Modify: `SkaRe/tests/test_crew_views.py` (add tests to `CrewAllViewTest`)

- [ ] **Step 1: Add single-crew CSV tests**

Append these methods inside `CrewAllViewTest` in `SkaRe/tests/test_crew_views.py`:

```python
    def test_crew_export_single_returns_csv(self):
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(
            reverse('SkaRe:crew_export_single_csv', kwargs={'crew_id': self.crew.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_crew_export_single_filename(self):
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(
            reverse('SkaRe:crew_export_single_csv', kwargs={'crew_id': self.crew.pk})
        )
        self.assertIn(f'crew_{self.crew.pk}.csv', response['Content-Disposition'])

    def test_crew_export_single_contains_member(self):
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(
            reverse('SkaRe:crew_export_single_csv', kwargs={'crew_id': self.crew.pk})
        )
        content = response.content.decode('utf-8-sig')
        self.assertIn('Jan', content)
        self.assertIn(Crew.CATEGORY_S, content)

    def test_crew_export_single_404_for_missing_crew(self):
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(
            reverse('SkaRe:crew_export_single_csv', kwargs={'crew_id': 99999})
        )
        self.assertEqual(response.status_code, 404)

    def test_crew_export_single_only_contains_this_crew(self):
        # Add a second crew — its members must NOT appear in the first crew's export
        other_unit = _make_unit(self.user)
        other_person = _make_person(other_unit, 'Karel', 'Jiný')
        other_boat = _make_boat(self.user)
        other_crew = Crew.objects.create(
            boat=other_boat, category=Crew.CATEGORY_R, created_by=self.user
        )
        CrewMember.objects.create(
            crew=other_crew, role=CrewMember.ROLE_HELMSMAN,
            participant=Person.objects.get(pk=other_person.pk),
        )
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(
            reverse('SkaRe:crew_export_single_csv', kwargs={'crew_id': self.crew.pk})
        )
        content = response.content.decode('utf-8-sig')
        self.assertIn('Jan', content)
        self.assertNotIn('Karel', content)
```

- [ ] **Step 2: Run tests to confirm new ones fail**

```bash
uv run manage.py test SkaRe.tests.test_crew_views.CrewAllViewTest --failfast
```

Expected: New single-export tests fail (stub returns empty CSV).

- [ ] **Step 3: Replace `crew_export_single_csv` stub with full implementation**

Replace the `crew_export_single_csv` function in `SkaRe/views/crews.py`:

```python
@login_required
def crew_export_single_csv(request, crew_id):
    if not request.user.is_staff:
        messages.error(request, _('Staff access required.'))
        return redirect('SkaRe:home')
    crew = get_object_or_404(Crew, id=crew_id)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="crew_{crew_id}.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow([
        'crew_id', 'category', 'boat_sail_number', 'boat_name',
        'boat_class', 'sail_area', 'role',
        'first_name', 'last_name', 'date_of_birth', 'scout_category',
        'participant_type', 'unit_name',
    ])

    members = (
        crew.members
        .select_related('crew__boat', 'crew__boat__boat_class', 'participant')
        .order_by('-role')
    )

    for m in members:
        person = m.participant
        participant_type = ''
        unit_name = ''
        if hasattr(person, 'regularparticipant'):
            participant_type = 'RegularParticipant'
            unit_name = person.regularparticipant.unit.entity.scout_unit_name
        elif hasattr(person, 'individualparticipant'):
            participant_type = 'IndividualParticipant'
        elif hasattr(person, 'organizer'):
            participant_type = 'Organizer'

        writer.writerow([
            crew.id,
            crew.category,
            _csv_safe(crew.boat.sail_number),
            _csv_safe(crew.boat.name),
            crew.boat.boat_class.name if crew.boat.boat_class else '',
            crew.boat.sail_area or '',
            m.role,
            _csv_safe(person.first_name),
            _csv_safe(person.last_name),
            person.date_of_birth,
            person.category or '',
            participant_type,
            _csv_safe(unit_name),
        ])

    return response
```

- [ ] **Step 4: Run all crew tests**

```bash
uv run manage.py test SkaRe.tests.test_crew_views --failfast
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add SkaRe/views/crews.py SkaRe/tests/test_crew_views.py
git commit -m "feat: implement crew_export_single_csv"
```

---

## Task 7: Home page navigation link

**Files:**
- Modify: `SkaRe/templates/SkaRe/registration/home.html`

- [ ] **Step 1: Add "Crew Overview" button to the admin card**

In `SkaRe/templates/SkaRe/registration/home.html`, find the "Administrator options" card body (around line 99). It currently ends with:

```html
                    <a class="btn btn-warning" href="{% url 'SkaRe:exports_organizer_units_csv' %}">
                        <i class="bi bi-file-earmark-spreadsheet"></i> {% trans "Download units overview (CSV)" %}
                    </a>
```

Add the following immediately after that `</a>` tag, before the closing `</div>`:

```html
                    <a class="btn btn-warning" href="{% url 'SkaRe:crew_all' %}">
                        <i class="bi bi-people-fill"></i> {% trans "Crew Overview" %}
                    </a>
```

- [ ] **Step 2: Run Django system checks**

```bash
uv run manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 3: Run the full test suite**

```bash
uv run manage.py test --failfast
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add SkaRe/templates/SkaRe/registration/home.html
git commit -m "feat: add Crew Overview link to home page admin card"
```
