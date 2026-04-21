# InfoDesk Edit Registrations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow InfoDesk members to edit any registration (unit, individual participant, organizer) regardless of ownership or deadlines, and add edit links to the infodesk registrations list.

**Architecture:** Three existing edit views in `SkaRe/views/registration.py` each need two small changes: (1) add `is_infodesk` to the ownership guard so InfoDesk members aren't blocked, and (2) redirect InfoDesk members to `infodesk_registrations` after a successful save instead of the owner's personal list. The infodesk registrations template gets an Edit button per row.

**Tech Stack:** Django 6.0, Python, Django test client

---

## Files changed

| File | Change |
|------|--------|
| `SkaRe/views/registration.py` | Add `is_infodesk` import; patch `edit_unit`, `edit_individual_participant`, `edit_organizer` |
| `SkaRe/templates/SkaRe/infodesk/registrations.html` | Add Edit button per row in the Actions column |
| `SkaRe/tests/test_infodesk_views.py` | New test class `InfodeskEditTest` covering all three entity types + template links |

---

### Task 1: InfoDesk can edit units

**Files:**
- Modify: `SkaRe/views/registration.py` (import line, `edit_unit` at ~205 and ~332)
- Test: `SkaRe/tests/test_infodesk_views.py`

- [ ] **Step 1: Write the failing tests**

Append to `SkaRe/tests/test_infodesk_views.py`:

```python
from SkaRe.models import Organizer  # Entity, Unit, IndividualParticipant already imported at top of file


def _make_infodesk_group_user(username='desk2'):
    user = User.objects.create_user(username=username, password='pw')
    group, _ = Group.objects.get_or_create(name='InfoDesk')
    user.groups.add(group)
    return user


class InfodeskEditUnitTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.infodesk = _make_infodesk_group_user()
        self.owner = User.objects.create_user(username='unitowner', password='pw')
        self.client.login(username='desk2', password='pw')

        entity = Entity.objects.create(
            created_by=self.owner,
            contact_email='u@example.com',
            contact_phone='+420123456789',
            scout_unit_name='Old Name',
        )
        self.unit = Unit.objects.create(entity=entity, contact_person_name='Leader')

    def _post_data(self, unit_name='New Name'):
        return {
            'scout_unit_name': unit_name,
            'scout_unit_evidence_id': '',
            'contact_email': 'u@example.com',
            'contact_phone': '+420123456789',
            'contact_person_name': 'Leader',
            'backup_contact_phone': '',
            'boats_p550': '0', 'boats_sail': '0',
            'boats_paddle': '0', 'boats_motor': '0',
            'scarf_count': '0', 'hat_count': '0', 'small_hat_count': '0',
            'accommodation_expectations': '',
            'estimated_accommodation_area': '',
            'participants-TOTAL_FORMS': '0',
            'participants-INITIAL_FORMS': '0',
            'participants-MIN_NUM_FORMS': '0',
            'participants-MAX_NUM_FORMS': '1000',
        }

    def test_infodesk_can_get_edit_unit(self):
        url = reverse('SkaRe:edit_unit', kwargs={'unit_id': self.unit.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_infodesk_edit_unit_redirects_to_infodesk_registrations(self):
        url = reverse('SkaRe:edit_unit', kwargs={'unit_id': self.unit.pk})
        response = self.client.post(url, self._post_data('Updated Name'))
        self.assertRedirects(response, reverse('SkaRe:infodesk_registrations'))

    def test_infodesk_edit_unit_saves_changes(self):
        url = reverse('SkaRe:edit_unit', kwargs={'unit_id': self.unit.pk})
        self.client.post(url, self._post_data('Updated Name'))
        self.unit.entity.refresh_from_db()
        self.assertEqual(self.unit.entity.scout_unit_name, 'Updated Name')
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run manage.py test SkaRe.tests.test_infodesk_views.InfodeskEditUnitTest --verbosity=2
```

Expected: all three tests FAIL — `test_infodesk_can_get_edit_unit` returns 302 (redirect to `list_units`), others also redirect with error message.

- [ ] **Step 3: Add `is_infodesk` import to `views/registration.py`**

At the top of `SkaRe/views/registration.py`, the existing imports end around line 22. Add the import:

```python
from ..permissions import is_infodesk
```

- [ ] **Step 4: Patch the ownership guard in `edit_unit`**

In `SkaRe/views/registration.py`, find the block inside `edit_unit` (around line 205):

```python
    # Check if user has permission to edit this unit (owner or editor)
    is_owner = unit.entity.created_by == request.user
    is_editor = unit.entity.editors.filter(id=request.user.id).exists()
    if not (is_owner or is_editor):
        messages.error(request, _('You do not have permission to edit this unit.'))
        return redirect('SkaRe:list_units')
```

Replace with:

```python
    # Check if user has permission to edit this unit (owner, editor, or InfoDesk)
    is_owner = unit.entity.created_by == request.user
    is_editor = unit.entity.editors.filter(id=request.user.id).exists()
    if not (is_owner or is_editor or is_infodesk(request.user)):
        messages.error(request, _('You do not have permission to edit this unit.'))
        return redirect('SkaRe:list_units')
```

- [ ] **Step 5: Patch the redirect after save in `edit_unit`**

Still in `edit_unit`, inside the `transaction.atomic()` success branch (around line 332), find:

```python
                    messages.success(
                        request,
                        _('Unit "{unit_name}" updated successfully with {count} participant(s)!').format(
                            unit_name=unit.entity.scout_unit_name,
                            count=participant_count
                        )
                    )
                    return redirect('SkaRe:list_units')
```

Replace with:

```python
                    messages.success(
                        request,
                        _('Unit "{unit_name}" updated successfully with {count} participant(s)!').format(
                            unit_name=unit.entity.scout_unit_name,
                            count=participant_count
                        )
                    )
                    if is_infodesk(request.user):
                        return redirect('SkaRe:infodesk_registrations')
                    return redirect('SkaRe:list_units')
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
uv run manage.py test SkaRe.tests.test_infodesk_views.InfodeskEditUnitTest --verbosity=2
```

Expected: all three tests PASS.

- [ ] **Step 7: Run the full test suite to check for regressions**

```bash
uv run manage.py test --failfast --verbosity=2
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add SkaRe/views/registration.py SkaRe/tests/test_infodesk_views.py
git commit -m "feat: allow InfoDesk to edit units, redirect to infodesk registrations (#128)"
```

---

### Task 2: InfoDesk can edit individual participants

**Files:**
- Modify: `SkaRe/views/registration.py` (`edit_individual_participant` at ~443 and ~554)
- Test: `SkaRe/tests/test_infodesk_views.py`

- [ ] **Step 1: Write the failing tests**

Append to `SkaRe/tests/test_infodesk_views.py`:

```python
class InfodeskEditIndividualParticipantTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.infodesk = _make_infodesk_group_user(username='desk3')
        self.owner = User.objects.create_user(username='indowner', password='pw')
        self.client.login(username='desk3', password='pw')

        entity = Entity.objects.create(
            created_by=self.owner,
            contact_email='i@example.com',
            contact_phone='+420123456789',
        )
        self.participant = IndividualParticipant.objects.create(
            entity=entity,
            first_name='Old',
            last_name='Name',
            date_of_birth=date(1990, 1, 1),
        )

    def _post_data(self, first_name='New'):
        return {
            'contact_email': 'i@example.com',
            'contact_phone': '+420123456789',
            'first_name': first_name,
            'last_name': 'Name',
            'nickname': '',
            'date_of_birth': '1990-01-01',
            'health_restrictions': '',
            'diet_vegetarian': '',
            'diet_vegan': '',
            'diet_no_soy': '',
            'diet_lactose_free': '',
            'diet_gluten_free': '',
            'diet_no_peanuts': '',
            'diet_no_eggs': '',
            'diet_no_fish': '',
            'diet_other': '',
            'relevant_information': '',
            'boats_p550': '0', 'boats_sail': '0',
            'boats_paddle': '0', 'boats_motor': '0',
            'scarf_count': '0', 'hat_count': '0', 'small_hat_count': '0',
            'accommodation_expectations': '',
            'estimated_accommodation_area': '',
        }

    def test_infodesk_can_get_edit_individual_participant(self):
        url = reverse('SkaRe:edit_individual_participant', kwargs={'participant_id': self.participant.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_infodesk_edit_individual_participant_redirects_to_infodesk_registrations(self):
        url = reverse('SkaRe:edit_individual_participant', kwargs={'participant_id': self.participant.pk})
        response = self.client.post(url, self._post_data('Updated'))
        self.assertRedirects(response, reverse('SkaRe:infodesk_registrations'))

    def test_infodesk_edit_individual_participant_saves_changes(self):
        url = reverse('SkaRe:edit_individual_participant', kwargs={'participant_id': self.participant.pk})
        self.client.post(url, self._post_data('Updated'))
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.first_name, 'Updated')
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run manage.py test SkaRe.tests.test_infodesk_views.InfodeskEditIndividualParticipantTest --verbosity=2
```

Expected: all three tests FAIL — ownership check blocks InfoDesk member.

- [ ] **Step 3: Patch the ownership guard in `edit_individual_participant`**

In `SkaRe/views/registration.py`, find the block inside `edit_individual_participant` (around line 443):

```python
    # Check if user has permission to edit this participant (owner or editor)
    is_owner = participant.entity.created_by == request.user
    is_editor = participant.entity.editors.filter(id=request.user.id).exists()
    if not (is_owner or is_editor):
        messages.error(request, _('You do not have permission to edit this participant.'))
        return redirect('SkaRe:list_individual_participants')
```

Replace with:

```python
    # Check if user has permission to edit this participant (owner, editor, or InfoDesk)
    is_owner = participant.entity.created_by == request.user
    is_editor = participant.entity.editors.filter(id=request.user.id).exists()
    if not (is_owner or is_editor or is_infodesk(request.user)):
        messages.error(request, _('You do not have permission to edit this participant.'))
        return redirect('SkaRe:list_individual_participants')
```

- [ ] **Step 4: Patch the redirect after save in `edit_individual_participant`**

Still in `edit_individual_participant`, inside the `transaction.atomic()` success branch (around line 554), find:

```python
                    messages.success(request, _('Individual Participant "{name}" updated successfully!').format(name=str(participant)))
                    return redirect('SkaRe:list_individual_participants')
```

Replace with:

```python
                    messages.success(request, _('Individual Participant "{name}" updated successfully!').format(name=str(participant)))
                    if is_infodesk(request.user):
                        return redirect('SkaRe:infodesk_registrations')
                    return redirect('SkaRe:list_individual_participants')
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run manage.py test SkaRe.tests.test_infodesk_views.InfodeskEditIndividualParticipantTest --verbosity=2
```

Expected: all three tests PASS.

- [ ] **Step 6: Run the full test suite to check for regressions**

```bash
uv run manage.py test --failfast --verbosity=2
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add SkaRe/views/registration.py SkaRe/tests/test_infodesk_views.py
git commit -m "feat: allow InfoDesk to edit individual participants, redirect to infodesk registrations (#128)"
```

---

### Task 3: InfoDesk can edit organizers

**Files:**
- Modify: `SkaRe/views/registration.py` (`edit_organizer` at ~777 and ~882)
- Test: `SkaRe/tests/test_infodesk_views.py`

- [ ] **Step 1: Write the failing tests**

Append to `SkaRe/tests/test_infodesk_views.py`:

```python
class InfodeskEditOrganizerTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.infodesk = _make_infodesk_group_user(username='desk4')
        self.owner = User.objects.create_user(username='orgowner', password='pw')
        self.client.login(username='desk4', password='pw')

        entity = Entity.objects.create(
            created_by=self.owner,
            contact_email='o2@example.com',
            contact_phone='+420123456789',
        )
        self.organizer = Organizer.objects.create(
            entity=entity,
            first_name='Old',
            last_name='Org',
            date_of_birth=date(1980, 1, 1),
        )

    def _post_data(self, first_name='New'):
        return {
            'contact_email': 'o2@example.com',
            'contact_phone': '+420123456789',
            'first_name': first_name,
            'last_name': 'Org',
            'nickname': '',
            'date_of_birth': '1980-01-01',
            'health_restrictions': '',
            'diet_vegetarian': '',
            'diet_vegan': '',
            'diet_no_soy': '',
            'diet_lactose_free': '',
            'diet_gluten_free': '',
            'diet_no_peanuts': '',
            'diet_no_eggs': '',
            'diet_no_fish': '',
            'diet_other': '',
            'relevant_information': '',
            'division': 'OTHERS',
            'transport': 'PUBLIC',
            'need_lift': '',
            'want_travel_order': '',
            'accommodation': 'OWN_TENT',
            'wants_scarf': '',
            'wants_hat': '',
            'wants_small_hat': '',
        }

    def test_infodesk_can_get_edit_organizer(self):
        url = reverse('SkaRe:edit_organizer', kwargs={'organizer_id': self.organizer.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_infodesk_edit_organizer_redirects_to_infodesk_registrations(self):
        url = reverse('SkaRe:edit_organizer', kwargs={'organizer_id': self.organizer.pk})
        response = self.client.post(url, self._post_data('Updated'))
        self.assertRedirects(response, reverse('SkaRe:infodesk_registrations'))

    def test_infodesk_edit_organizer_saves_changes(self):
        url = reverse('SkaRe:edit_organizer', kwargs={'organizer_id': self.organizer.pk})
        self.client.post(url, self._post_data('Updated'))
        self.organizer.refresh_from_db()
        self.assertEqual(self.organizer.first_name, 'Updated')
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run manage.py test SkaRe.tests.test_infodesk_views.InfodeskEditOrganizerTest --verbosity=2
```

Expected: all three tests FAIL — ownership check blocks InfoDesk member.

- [ ] **Step 3: Patch the ownership guard in `edit_organizer`**

In `SkaRe/views/registration.py`, find the block inside `edit_organizer` (around line 777):

```python
    # Check if user has permission to edit this organizer (owner or editor)
    is_owner = organizer.entity.created_by == request.user
    is_editor = organizer.entity.editors.filter(id=request.user.id).exists()
    if not (is_owner or is_editor):
        messages.error(request, _('You do not have permission to edit this organizer.'))
        return redirect('SkaRe:list_organizers')
```

Replace with:

```python
    # Check if user has permission to edit this organizer (owner, editor, or InfoDesk)
    is_owner = organizer.entity.created_by == request.user
    is_editor = organizer.entity.editors.filter(id=request.user.id).exists()
    if not (is_owner or is_editor or is_infodesk(request.user)):
        messages.error(request, _('You do not have permission to edit this organizer.'))
        return redirect('SkaRe:list_organizers')
```

- [ ] **Step 4: Patch the redirect after save in `edit_organizer`**

Still in `edit_organizer`, inside the `transaction.atomic()` success branch (around line 882), find:

```python
                    messages.success(request, _('Organizer "{name}" updated successfully!').format(name=str(organizer)))
                    return redirect('SkaRe:list_organizers')
```

Replace with:

```python
                    messages.success(request, _('Organizer "{name}" updated successfully!').format(name=str(organizer)))
                    if is_infodesk(request.user):
                        return redirect('SkaRe:infodesk_registrations')
                    return redirect('SkaRe:list_organizers')
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run manage.py test SkaRe.tests.test_infodesk_views.InfodeskEditOrganizerTest --verbosity=2
```

Expected: all three tests PASS.

- [ ] **Step 6: Run the full test suite to check for regressions**

```bash
uv run manage.py test --failfast --verbosity=2
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add SkaRe/views/registration.py SkaRe/tests/test_infodesk_views.py
git commit -m "feat: allow InfoDesk to edit organizers, redirect to infodesk registrations (#128)"
```

---

### Task 4: Edit links in infodesk registrations template

**Files:**
- Modify: `SkaRe/templates/SkaRe/infodesk/registrations.html`
- Test: `SkaRe/tests/test_infodesk_views.py`

- [ ] **Step 1: Write the failing test**

Append to `SkaRe/tests/test_infodesk_views.py`:

```python
class InfodeskRegistrationsEditLinksTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.infodesk = _make_infodesk_group_user(username='desk5')
        self.owner = User.objects.create_user(username='linkowner', password='pw')
        self.client.login(username='desk5', password='pw')

    def test_edit_link_present_for_unit(self):
        entity = Entity.objects.create(
            created_by=self.owner,
            contact_email='e@example.com',
            contact_phone='+420123456789',
            scout_unit_name='Link Unit',
        )
        unit = Unit.objects.create(entity=entity, contact_person_name='Leader')
        url = reverse('SkaRe:infodesk_registrations')
        response = self.client.get(url)
        edit_url = reverse('SkaRe:edit_unit', kwargs={'unit_id': unit.pk})
        self.assertContains(response, edit_url)

    def test_edit_link_present_for_individual_participant(self):
        entity = Entity.objects.create(
            created_by=self.owner,
            contact_email='e2@example.com',
            contact_phone='+420123456789',
        )
        participant = IndividualParticipant.objects.create(
            entity=entity,
            first_name='Link',
            last_name='Person',
            date_of_birth=date(1990, 1, 1),
        )
        url = reverse('SkaRe:infodesk_registrations')
        response = self.client.get(url)
        edit_url = reverse('SkaRe:edit_individual_participant', kwargs={'participant_id': participant.pk})
        self.assertContains(response, edit_url)

    def test_edit_link_present_for_organizer(self):
        entity = Entity.objects.create(
            created_by=self.owner,
            contact_email='e3@example.com',
            contact_phone='+420123456789',
        )
        organizer = Organizer.objects.create(
            entity=entity,
            first_name='Link',
            last_name='Org',
            date_of_birth=date(1980, 1, 1),
        )
        url = reverse('SkaRe:infodesk_registrations')
        response = self.client.get(url)
        edit_url = reverse('SkaRe:edit_organizer', kwargs={'organizer_id': organizer.pk})
        self.assertContains(response, edit_url)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run manage.py test SkaRe.tests.test_infodesk_views.InfodeskRegistrationsEditLinksTest --verbosity=2
```

Expected: all three tests FAIL — no edit links in the template yet.

- [ ] **Step 3: Add Edit buttons to `registrations.html`**

In `SkaRe/templates/SkaRe/infodesk/registrations.html`, find the Actions `<td>` cell inside the `{% for row in rows %}` loop (around line 61):

```html
            <td>
              {% if not row.entity.confirmed %}
                <button type="submit"
                        class="btn btn-success btn-sm"
                        formaction="{% url 'SkaRe:infodesk_confirm_entity' row.entity.pk %}">
                  <i class="bi bi-check"></i> {% trans "Confirm" %}
                </button>
              {% else %}
                <button type="submit"
                        class="btn btn-outline-danger btn-sm"
                        formaction="{% url 'SkaRe:infodesk_reject_entity' row.entity.pk %}">
                  <i class="bi bi-x"></i> {% trans "Reject" %}
                </button>
              {% endif %}
            </td>
```

Replace with:

```html
            <td>
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
              {% if not row.entity.confirmed %}
                <button type="submit"
                        class="btn btn-success btn-sm"
                        formaction="{% url 'SkaRe:infodesk_confirm_entity' row.entity.pk %}">
                  <i class="bi bi-check"></i> {% trans "Confirm" %}
                </button>
              {% else %}
                <button type="submit"
                        class="btn btn-outline-danger btn-sm"
                        formaction="{% url 'SkaRe:infodesk_reject_entity' row.entity.pk %}">
                  <i class="bi bi-x"></i> {% trans "Reject" %}
                </button>
              {% endif %}
            </td>
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run manage.py test SkaRe.tests.test_infodesk_views.InfodeskRegistrationsEditLinksTest --verbosity=2
```

Expected: all three tests PASS.

- [ ] **Step 5: Run the full test suite to check for regressions**

```bash
uv run manage.py test --failfast --verbosity=2
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add SkaRe/templates/SkaRe/infodesk/registrations.html SkaRe/tests/test_infodesk_views.py
git commit -m "feat: add edit links per registration in infodesk registrations view (#128)"
```
