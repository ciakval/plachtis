# Codebase Restructure — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the monolithic `models.py`, `views.py`, and `forms.py` into focused Python packages, and add a `permissions.py` helper module, without changing any behaviour.

**Architecture:** Each file becomes a package (`models/`, `views/`, `forms/`). A package-level `__init__.py` re-exports every public name so all existing imports — from tests, admin, urls, and migrations — continue to work without modification. The registration templates are moved into a `registration/` subdirectory to match the existing `boats/` and `crews/` layout.

**Tech Stack:** Django 6.0, Python 3.x, `uv run` for commands.

---

## File Map

### Created
- `SkaRe/models/__init__.py`
- `SkaRe/models/registration.py`
- `SkaRe/models/boats.py`
- `SkaRe/forms/__init__.py`
- `SkaRe/forms/registration.py`
- `SkaRe/forms/boats.py`
- `SkaRe/forms/crews.py`
- `SkaRe/views/__init__.py`
- `SkaRe/views/registration.py`
- `SkaRe/views/boats.py`
- `SkaRe/views/crews.py`
- `SkaRe/permissions.py`
- `SkaRe/templates/SkaRe/registration/` (directory with moved templates)

### Deleted
- `SkaRe/models.py`
- `SkaRe/forms.py`
- `SkaRe/views.py`

### Modified
- `SkaRe/urls.py` — no content change; verify it still works after `views/` split
- `SkaRe/admin.py` — no content change needed; re-exports handle it
- `SkaRe/views/registration.py` — render() paths updated after template move (Task 5)

---

## Task 1: Establish baseline

**Files:** none modified

- [ ] **Step 1: Run the full test suite and record the result**

```bash
uv run python manage.py test --verbosity=2 2>&1 | tail -20
```

Expected: all tests pass. Note the exact count (e.g. "Ran 47 tests in 3.2s OK"). This is your baseline — every subsequent task must end with the same result.

---

## Task 2: Split models.py into models/ package

**Files:**
- Create: `SkaRe/models/__init__.py`
- Create: `SkaRe/models/registration.py`
- Create: `SkaRe/models/boats.py`
- Delete: `SkaRe/models.py`

### Content mapping

`SkaRe/models/registration.py` contains (move verbatim from `models.py`):
- `validate_date_of_birth`
- `EventSettings`
- `Person`
- `Entity`
- `Unit`
- `RegularParticipant`
- `IndividualParticipant`
- `Organizer`

`SkaRe/models/boats.py` contains (move verbatim from `models.py`):
- `BoatClass`
- `Boat`
- `Crew`
- `CrewMember`

- [ ] **Step 2: Create `SkaRe/models/registration.py`**

Copy the following classes and functions verbatim from `SkaRe/models.py`. The imports at the top of the file are:

```python
from datetime import datetime, date
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from solo.models import SingletonModel
```

Then copy `validate_date_of_birth`, `EventSettings`, `Person`, `Entity`, `Unit`, `RegularParticipant`, `IndividualParticipant`, `Organizer` verbatim.

- [ ] **Step 3: Create `SkaRe/models/boats.py`**

This file imports `Person` from the sibling module (single dot = same package):

```python
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .registration import Person
```

Then copy `BoatClass`, `Boat`, `Crew`, `CrewMember` verbatim from `SkaRe/models.py`.

- [ ] **Step 4: Create `SkaRe/models/__init__.py`**

This file must re-export every name that anything outside this package imports. Check `SkaRe/admin.py`, `SkaRe/forms.py`, `SkaRe/views.py`, and all test files for `from SkaRe.models import ...` and `from .models import ...` to verify completeness.

```python
from .registration import (
    validate_date_of_birth,
    EventSettings,
    Person,
    Entity,
    Unit,
    RegularParticipant,
    IndividualParticipant,
    Organizer,
)
from .boats import BoatClass, Boat, Crew, CrewMember
```

- [ ] **Step 5: Delete `SkaRe/models.py`**

```bash
rm SkaRe/models.py
```

- [ ] **Step 6: Run the full test suite**

```bash
uv run python manage.py test --verbosity=2 2>&1 | tail -20
```

Expected: same count as baseline, all pass. If any fail, check that the `__init__.py` re-exports cover the missing names.

- [ ] **Step 7: Run Django system checks**

```bash
uv run python manage.py check
```

Expected: "System check identified no issues."

- [ ] **Step 8: Commit**

```bash
git add SkaRe/models/ && git rm SkaRe/models.py
git commit -m "refactor: split models.py into models/ package"
```

---

## Task 3: Split forms.py into forms/ package

**Files:**
- Create: `SkaRe/forms/__init__.py`
- Create: `SkaRe/forms/registration.py`
- Create: `SkaRe/forms/boats.py`
- Create: `SkaRe/forms/crews.py`
- Delete: `SkaRe/forms.py`

### Content mapping

`SkaRe/forms/registration.py` contains:
- `validate_czech_phone`
- `validate_event_phone`
- `UserRegistrationForm`
- `UnitRegistrationForm`
- `RegularParticipantForm`
- `get_participant_formset`
- `IndividualParticipantRegistrationForm`
- `OrganizerRegistrationForm`

`SkaRe/forms/boats.py` contains:
- `BoatForm`

`SkaRe/forms/crews.py` contains:
- `CrewRegistrationForm`

- [ ] **Step 1: Create `SkaRe/forms/registration.py`**

Imports (note `..models` — two dots to go up to `SkaRe/` then into `models/`):

```python
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from datetime import datetime
from django.utils import timezone
from ..models import Unit, RegularParticipant, IndividualParticipant, Organizer
```

Then copy `validate_czech_phone`, `validate_event_phone`, `UserRegistrationForm`, `UnitRegistrationForm`, `RegularParticipantForm`, `get_participant_formset`, `IndividualParticipantRegistrationForm`, `OrganizerRegistrationForm` verbatim from `SkaRe/forms.py`.

- [ ] **Step 2: Create `SkaRe/forms/boats.py`**

```python
from django import forms
from django.utils.translation import gettext_lazy as _
from ..models import BoatClass, Boat
```

Copy `BoatForm` verbatim from `SkaRe/forms.py`.

- [ ] **Step 3: Create `SkaRe/forms/crews.py`**

```python
from django import forms
from django.utils.translation import gettext_lazy as _
from ..models import Boat, Person, Crew
```

Copy `CrewRegistrationForm` verbatim from `SkaRe/forms.py`.

- [ ] **Step 4: Create `SkaRe/forms/__init__.py`**

```python
from .registration import (
    validate_czech_phone,
    validate_event_phone,
    UserRegistrationForm,
    UnitRegistrationForm,
    RegularParticipantForm,
    get_participant_formset,
    IndividualParticipantRegistrationForm,
    OrganizerRegistrationForm,
)
from .boats import BoatForm
from .crews import CrewRegistrationForm
```

- [ ] **Step 5: Delete `SkaRe/forms.py`**

```bash
rm SkaRe/forms.py
```

- [ ] **Step 6: Run the full test suite**

```bash
uv run python manage.py test --verbosity=2 2>&1 | tail -20
```

Expected: same count as baseline, all pass.

- [ ] **Step 7: Commit**

```bash
git add SkaRe/forms/ && git rm SkaRe/forms.py
git commit -m "refactor: split forms.py into forms/ package"
```

---

## Task 4: Split views.py into views/ package

**Files:**
- Create: `SkaRe/views/__init__.py`
- Create: `SkaRe/views/registration.py`
- Create: `SkaRe/views/boats.py`
- Create: `SkaRe/views/crews.py`
- Delete: `SkaRe/views.py`

### Content mapping

`SkaRe/views/registration.py` contains:
- Module-level constants: `ADMIN_RESULTS_LIMIT`, `MANAGE_ENTITIES_PAGE_SIZE`
- `home`, `user_login`, `user_logout`, `forgot_password`, `user_register`
- `register_unit`, `list_units`, `edit_unit`
- `register_individual_participant`, `list_individual_participants`, `edit_individual_participant`
- `register_organizer`, `list_organizers`, `edit_organizer`
- `list_all`, `list_merchandise`
- `manage_entities`
- `manage_unit_editors`, `manage_individual_participant_editors`, `manage_organizer_editors`

`SkaRe/views/boats.py` contains:
- Module-level constant: `_SAIL_REGISTRY_CACHE_KEY`
- `_fetch_sheet_csv`, `_get_registry_rows`
- `boat_sail_lookup`, `boat_my_unit`
- `boat_list`, `boat_detail`, `boat_register`, `boat_edit`, `boat_delete`, `boat_lend`

`SkaRe/views/crews.py` contains:
- `crew_register`, `crew_list`, `crew_detail`, `crew_edit`, `crew_delete`, `crew_export_csv`
- `person_lend`

- [ ] **Step 1: Create `SkaRe/views/registration.py`**

Imports:

```python
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django import forms
from django.utils.translation import gettext as _
from django.utils.http import url_has_allowed_host_and_scheme
from django.http import HttpResponse
from ..models import (
    Entity, Unit, RegularParticipant, EventSettings,
    IndividualParticipant, Organizer, Person,
)
from ..forms import (
    UserRegistrationForm, UnitRegistrationForm,
    IndividualParticipantRegistrationForm, OrganizerRegistrationForm,
    validate_czech_phone, get_participant_formset,
)
from ..form_utils import generate_form_token, is_duplicate_submission, consume_form_token
```

Copy the module-level constants and all listed functions verbatim.

- [ ] **Step 2: Create `SkaRe/views/boats.py`**

Imports:

```python
import csv
import io
import urllib.request

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.cache import cache
from django.conf import settings
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.db import transaction
from ..models import Entity, Unit, BoatClass, Boat
from ..forms import BoatForm
```

Copy `_SAIL_REGISTRY_CACHE_KEY` and all listed functions verbatim.

- [ ] **Step 3: Create `SkaRe/views/crews.py`**

Imports:

```python
import csv

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.utils.translation import gettext as _
from django.db import transaction
from ..models import Boat, Person, Crew, CrewMember, EventSettings
from ..forms import CrewRegistrationForm
```

Copy all listed functions verbatim.

- [ ] **Step 4: Create `SkaRe/views/__init__.py`**

`urls.py` does `from . import views` then accesses `views.home`, `views.boat_list`, etc. This `__init__.py` re-exports all view functions so that pattern continues to work:

```python
from .registration import (
    home,
    user_login,
    user_logout,
    forgot_password,
    user_register,
    register_unit,
    list_units,
    edit_unit,
    register_individual_participant,
    list_individual_participants,
    edit_individual_participant,
    register_organizer,
    list_organizers,
    edit_organizer,
    list_all,
    list_merchandise,
    manage_entities,
    manage_unit_editors,
    manage_individual_participant_editors,
    manage_organizer_editors,
)
from .boats import (
    boat_list,
    boat_detail,
    boat_register,
    boat_edit,
    boat_delete,
    boat_lend,
    boat_sail_lookup,
    boat_my_unit,
)
from .crews import (
    crew_register,
    crew_list,
    crew_detail,
    crew_edit,
    crew_delete,
    crew_export_csv,
    person_lend,
)
```

- [ ] **Step 5: Delete `SkaRe/views.py`**

```bash
rm SkaRe/views.py
```

- [ ] **Step 6: Run the full test suite**

```bash
uv run python manage.py test --verbosity=2 2>&1 | tail -20
```

Expected: same count as baseline, all pass.

- [ ] **Step 7: Run Django system checks**

```bash
uv run python manage.py check
```

Expected: "System check identified no issues."

- [ ] **Step 8: Commit**

```bash
git add SkaRe/views/ && git rm SkaRe/views.py
git commit -m "refactor: split views.py into views/ package"
```

---

## Task 5: Add permissions.py

**Files:**
- Create: `SkaRe/permissions.py`

- [ ] **Step 1: Create `SkaRe/permissions.py`**

```python
def is_infodesk(user) -> bool:
    """Return True if the user is a member of the InfoDesk group."""
    return user.groups.filter(name='InfoDesk').exists()


def is_race_management(user) -> bool:
    """Return True if the user is a member of the RaceManagement group."""
    return user.groups.filter(name='RaceManagement').exists()
```

- [ ] **Step 2: Write tests for permissions.py**

Create `SkaRe/tests/test_permissions.py`:

```python
from django.test import TestCase
from django.contrib.auth.models import User, Group
from SkaRe.permissions import is_infodesk, is_race_management


class IsInfodeskTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='pass')
        self.group = Group.objects.create(name='InfoDesk')

    def test_returns_false_for_user_without_group(self):
        self.assertFalse(is_infodesk(self.user))

    def test_returns_true_for_user_in_infodesk_group(self):
        self.user.groups.add(self.group)
        self.assertTrue(is_infodesk(self.user))

    def test_race_management_user_is_not_infodesk(self):
        rm_group = Group.objects.create(name='RaceManagement')
        self.user.groups.add(rm_group)
        self.assertFalse(is_infodesk(self.user))


class IsRaceManagementTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester2', password='pass')
        self.group = Group.objects.create(name='RaceManagement')

    def test_returns_false_for_user_without_group(self):
        self.assertFalse(is_race_management(self.user))

    def test_returns_true_for_user_in_race_management_group(self):
        self.user.groups.add(self.group)
        self.assertTrue(is_race_management(self.user))

    def test_infodesk_user_is_not_race_management(self):
        id_group = Group.objects.create(name='InfoDesk')
        self.user.groups.add(id_group)
        self.assertFalse(is_race_management(self.user))
```

- [ ] **Step 3: Run the permissions tests**

```bash
uv run python manage.py test SkaRe.tests.test_permissions --verbosity=2
```

Expected: 6 tests pass.

- [ ] **Step 4: Run the full test suite**

```bash
uv run python manage.py test --verbosity=2 2>&1 | tail -5
```

Expected: baseline count + 6, all pass.

- [ ] **Step 5: Commit**

```bash
git add SkaRe/permissions.py SkaRe/tests/test_permissions.py
git commit -m "feat: add permissions.py with is_infodesk and is_race_management helpers"
```

---

## Task 6: Reorganise registration templates

**Files:**
- Create: `SkaRe/templates/SkaRe/registration/` (directory)
- Move: 17 templates from `SkaRe/templates/SkaRe/` into `registration/`
- Modify: `SkaRe/views/registration.py` — update all `render()` template paths

The following templates move from `SkaRe/templates/SkaRe/` to `SkaRe/templates/SkaRe/registration/`:

| Old path | New path |
|----------|----------|
| `SkaRe/home.html` | `SkaRe/registration/home.html` |
| `SkaRe/login.html` | `SkaRe/registration/login.html` |
| `SkaRe/register.html` | `SkaRe/registration/register.html` |
| `SkaRe/forgot_password.html` | `SkaRe/registration/forgot_password.html` |
| `SkaRe/register_unit.html` | `SkaRe/registration/register_unit.html` |
| `SkaRe/list_units.html` | `SkaRe/registration/list_units.html` |
| `SkaRe/edit_unit.html` | `SkaRe/registration/edit_unit.html` |
| `SkaRe/register_individual_participant.html` | `SkaRe/registration/register_individual_participant.html` |
| `SkaRe/list_individual_participants.html` | `SkaRe/registration/list_individual_participants.html` |
| `SkaRe/edit_individual_participant.html` | `SkaRe/registration/edit_individual_participant.html` |
| `SkaRe/register_organizer.html` | `SkaRe/registration/register_organizer.html` |
| `SkaRe/list_organizers.html` | `SkaRe/registration/list_organizers.html` |
| `SkaRe/edit_organizer.html` | `SkaRe/registration/edit_organizer.html` |
| `SkaRe/list_all.html` | `SkaRe/registration/list_all.html` |
| `SkaRe/list_merchandise.html` | `SkaRe/registration/list_merchandise.html` |
| `SkaRe/manage_entities.html` | `SkaRe/registration/manage_entities.html` |
| `SkaRe/manage_editors.html` | `SkaRe/registration/manage_editors.html` |

`base.html` stays at `SkaRe/templates/SkaRe/base.html` — it is not a registration template.

- [ ] **Step 1: Move the templates**

```bash
mkdir -p SkaRe/templates/SkaRe/registration
git mv SkaRe/templates/SkaRe/home.html SkaRe/templates/SkaRe/registration/
git mv SkaRe/templates/SkaRe/login.html SkaRe/templates/SkaRe/registration/
git mv SkaRe/templates/SkaRe/register.html SkaRe/templates/SkaRe/registration/
git mv SkaRe/templates/SkaRe/forgot_password.html SkaRe/templates/SkaRe/registration/
git mv SkaRe/templates/SkaRe/register_unit.html SkaRe/templates/SkaRe/registration/
git mv SkaRe/templates/SkaRe/list_units.html SkaRe/templates/SkaRe/registration/
git mv SkaRe/templates/SkaRe/edit_unit.html SkaRe/templates/SkaRe/registration/
git mv SkaRe/templates/SkaRe/register_individual_participant.html SkaRe/templates/SkaRe/registration/
git mv SkaRe/templates/SkaRe/list_individual_participants.html SkaRe/templates/SkaRe/registration/
git mv SkaRe/templates/SkaRe/edit_individual_participant.html SkaRe/templates/SkaRe/registration/
git mv SkaRe/templates/SkaRe/register_organizer.html SkaRe/templates/SkaRe/registration/
git mv SkaRe/templates/SkaRe/list_organizers.html SkaRe/templates/SkaRe/registration/
git mv SkaRe/templates/SkaRe/edit_organizer.html SkaRe/templates/SkaRe/registration/
git mv SkaRe/templates/SkaRe/list_all.html SkaRe/templates/SkaRe/registration/
git mv SkaRe/templates/SkaRe/list_merchandise.html SkaRe/templates/SkaRe/registration/
git mv SkaRe/templates/SkaRe/manage_entities.html SkaRe/templates/SkaRe/registration/
git mv SkaRe/templates/SkaRe/manage_editors.html SkaRe/templates/SkaRe/registration/
```

- [ ] **Step 2: Update render() paths in `SkaRe/views/registration.py`**

Find every `render(request, 'SkaRe/` call and add `registration/` after `SkaRe/`. The full mapping (old → new string argument):

| Old | New |
|-----|-----|
| `'SkaRe/home.html'` | `'SkaRe/registration/home.html'` |
| `'SkaRe/login.html'` | `'SkaRe/registration/login.html'` |
| `'SkaRe/register.html'` | `'SkaRe/registration/register.html'` |
| `'SkaRe/forgot_password.html'` | `'SkaRe/registration/forgot_password.html'` |
| `'SkaRe/register_unit.html'` | `'SkaRe/registration/register_unit.html'` |
| `'SkaRe/list_units.html'` | `'SkaRe/registration/list_units.html'` |
| `'SkaRe/edit_unit.html'` | `'SkaRe/registration/edit_unit.html'` |
| `'SkaRe/register_individual_participant.html'` | `'SkaRe/registration/register_individual_participant.html'` |
| `'SkaRe/list_individual_participants.html'` | `'SkaRe/registration/list_individual_participants.html'` |
| `'SkaRe/edit_individual_participant.html'` | `'SkaRe/registration/edit_individual_participant.html'` |
| `'SkaRe/register_organizer.html'` | `'SkaRe/registration/register_organizer.html'` |
| `'SkaRe/list_organizers.html'` | `'SkaRe/registration/list_organizers.html'` |
| `'SkaRe/edit_organizer.html'` | `'SkaRe/registration/edit_organizer.html'` |
| `'SkaRe/list_all.html'` | `'SkaRe/registration/list_all.html'` |
| `'SkaRe/list_merchandise.html'` | `'SkaRe/registration/list_merchandise.html'` |
| `'SkaRe/manage_entities.html'` | `'SkaRe/registration/manage_entities.html'` |
| `'SkaRe/manage_editors.html'` | `'SkaRe/registration/manage_editors.html'` |

Tip: `grep -n "render(request, 'SkaRe/" SkaRe/views/registration.py` shows every line to update.

- [ ] **Step 3: Run the full test suite**

```bash
uv run python manage.py test --verbosity=2 2>&1 | tail -5
```

Expected: same count as after Task 5, all pass.

- [ ] **Step 4: Smoke-test the running server**

```bash
uv run python manage.py runserver 8000
```

Open http://localhost:8000/ in a browser and verify the home page loads. Check that login, unit list, and boat list pages also load without 500 errors. Stop the server with Ctrl-C.

- [ ] **Step 5: Commit**

```bash
git add SkaRe/templates/SkaRe/registration/ SkaRe/views/registration.py
git commit -m "refactor: move registration templates into registration/ subdirectory"
```

---

## Self-Review

**Spec coverage:**
- ✅ `models/` package with `registration.py` and `boats.py` — Tasks 2
- ✅ `forms/` package — Task 3
- ✅ `views/` package — Task 4
- ✅ `permissions.py` with `is_infodesk()` and `is_race_management()` — Task 5
- ✅ `templates/SkaRe/registration/` — Task 6
- ✅ `models/__init__.py` re-exports preserve backward compat — Task 2, Step 4
- ✅ `forms/__init__.py` re-exports preserve backward compat — Task 3, Step 4
- ✅ `views/__init__.py` re-exports preserve `urls.py` pattern — Task 4, Step 4
- ⬜ `models/attendance.py` and `models/tickets.py` — intentionally deferred (Plans 4 and 5)
- ⬜ `views/attendance.py`, `views/tickets.py`, `views/infodesk.py`, `views/exports.py` — intentionally deferred

**Placeholder scan:** No TBDs. Every step has explicit commands or code.

**Type consistency:** No new types introduced. All names in `__init__.py` re-exports match the exact class/function names in the source files.
