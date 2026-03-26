# PlachtIS Overhaul — Design Spec

**Date:** 2026-03-26
**Scope:** Full system overhaul — codebase restructure, role model, dietary restrictions, attendance tracking, sail ticket management, InfoDesk UX, exports.
**App:** `SkaRe` (existing Django app)
**Constraint:** System is live with real data. No breaking migrations. English naming throughout.

---

## Overview

PlachtIS serves three use-cases:
1. **People management** — information about attendees for kitchen, health, and safety.
2. **Logistics** — unit/group information for space planning, transport, merchandise.
3. **Sail ticket management** — tracking which boats are on the water at any time, using physical RFID-enabled sail tickets.

This overhaul adds the missing subsystems (sail tickets, attendance tracking, exports), formalises the role model, restructures the codebase for maintainability, and addresses several open issues.

---

## Section 1 — Codebase Structure

The monolithic `models.py`, `views.py`, and `forms.py` are converted to Python packages. This is a pure Python rename — no migrations, no URL changes, no template changes required.

`models/__init__.py` re-exports every model class by name so existing migrations and admin imports continue working without changes.

```
SkaRe/
  models/
    __init__.py        # re-exports everything for backward compat
    registration.py    # EventSettings, Person, Entity, Unit,
                       # RegularParticipant, IndividualParticipant, Organizer
    boats.py           # BoatClass, Boat, Crew, CrewMember
    tickets.py         # SailTicket, SailTicketLog
    attendance.py      # AttendanceLog (status lives on Person)

  views/
    __init__.py
    registration.py    # existing registration views
    boats.py           # existing boat views
    crews.py           # existing crew views
    tickets.py         # sail ticket management views
    attendance.py      # InfoDesk attendance views
    exports.py         # kitchen + medical exports
    infodesk.py        # InfoDesk dashboard + validation queue

  forms/
    __init__.py
    registration.py
    boats.py
    crews.py
    tickets.py
    attendance.py

  permissions.py       # is_infodesk(), is_race_management() helpers

  tests/
    test_registration_views.py
    test_registration_forms.py
    test_registration_models.py
    test_boat_views.py       # existing, unchanged
    test_boat_forms.py       # existing, unchanged
    test_boat_models.py      # existing, unchanged
    test_boat_migrations.py  # existing, unchanged
    test_crew_forms.py       # existing, unchanged
    test_crew_views.py       # existing, unchanged
    test_crew_models.py      # existing, unchanged
    test_ticket_views.py
    test_ticket_models.py
    test_attendance_views.py
    test_exports.py

  templates/SkaRe/
    registration/   # existing templates, reorganised
    boats/          # existing
    crews/          # existing
    tickets/        # new
    attendance/     # new
    exports/        # new
    infodesk/       # new
```

---

## Section 2 — Roles & Permissions

### Groups

| Group | Created via | Capabilities |
|-------|-------------|--------------|
| `InfoDesk` | existing data migration | Edit any entity/boat/crew; manage sail tickets; mark attendance; generate exports; confirm/reject registrations |
| `RaceManagement` | new data migration (0024) | Edit `EventSettings` (deadlines only); read-only on everything else |
| *(none)* | default | Self-service: own registrations, own boats/crews, within deadlines |

Django superuser is the "main admin" — full access.

### Permission helpers (`SkaRe/permissions.py`)

```python
def is_infodesk(user) -> bool:
    return user.groups.filter(name='InfoDesk').exists()

def is_race_management(user) -> bool:
    return user.groups.filter(name='RaceManagement').exists()
```

An `@infodesk_required` decorator (wrapping `@login_required`) is used on all InfoDesk views.

### `Entity.can_be_edited()` update

InfoDesk members bypass deadline checks:

```python
def can_be_edited(self, user):
    if is_infodesk(user):
        return True
    is_owner = self.created_by == user
    is_editor = self.editors.filter(id=user.id).exists()
    if not (is_owner or is_editor):
        return False
    return EventSettings.is_editing_open() or self.unlocked_for_editing
```

`Boat.can_be_edited()` and `Crew.can_be_edited()` already check `InfoDesk` — no change needed.

### `RaceManagement` access

Handled via a customised `EventSettingsAdmin` in Django admin that restricts write access to `RaceManagement` members and superusers. No custom view needed.

---

## Section 3 — Data Model Changes

### 3a. Dietary restrictions (replaces `dietary_restrictions` TextField on `Person`)

```python
# Dietary preferences
diet_vegan           = models.BooleanField(default=False, verbose_name=_('Vegan'))
diet_vegetarian      = models.BooleanField(default=False, verbose_name=_('Vegetarian'))

# Major allergens
diet_gluten_free     = models.BooleanField(default=False, verbose_name=_('Gluten-free'))
diet_lactose_free    = models.BooleanField(default=False, verbose_name=_('Lactose/dairy-free'))
diet_no_eggs         = models.BooleanField(default=False, verbose_name=_('No eggs'))
diet_no_peanuts      = models.BooleanField(default=False, verbose_name=_('No peanuts'))
diet_no_tree_nuts    = models.BooleanField(default=False, verbose_name=_('No tree nuts'))
diet_no_soy          = models.BooleanField(default=False, verbose_name=_('No soy'))
diet_no_fish         = models.BooleanField(default=False, verbose_name=_('No fish'))
diet_no_fruits       = models.BooleanField(default=False, verbose_name=_('No fruits'))

# Catch-all
diet_other           = models.TextField(blank=True, verbose_name=_('Other dietary restrictions'))
```

**Migration (0025):** add the 10 boolean fields and `diet_other`; data migration copies existing `dietary_restrictions` → `diet_other`; remove `dietary_restrictions`.

### 3b. Attendance

Added to `Person`:

```python
class AttendanceStatus(models.TextChoices):
    EXPECTED   = 'expected',   _('Expected')
    ARRIVED    = 'arrived',    _('Arrived')
    DEPARTED   = 'departed',   _('Departed')
    NOT_COMING = 'not_coming', _('Not coming')

attendance_status = models.CharField(
    max_length=20,
    choices=AttendanceStatus.choices,
    default=AttendanceStatus.EXPECTED,
)
arrived_at  = models.DateTimeField(null=True, blank=True)
departed_at = models.DateTimeField(null=True, blank=True)
```

New model `AttendanceLog` (in `models/attendance.py`):

```python
class AttendanceLog(models.Model):
    person     = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='attendance_logs')
    status     = models.CharField(max_length=20, choices=Person.AttendanceStatus.choices)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    note       = models.TextField(blank=True)
```

When InfoDesk changes a person's status, the view writes an `AttendanceLog` row and updates `arrived_at`/`departed_at` on `Person` accordingly.

**Migration (0026):** add attendance fields to `Person`; create `AttendanceLog` table.

### 3c. Sail Ticket models (in `models/tickets.py`)

```python
class SailTicket(models.Model):
    class Color(models.TextChoices):
        P550  = 'p550',  _('P550')
        SAIL  = 'sail',  _('Sailboat')
        OTHER = 'other', _('Other boat')
        SPARE = 'spare', _('Spare')

    class Status(models.TextChoices):
        ASHORE   = 'ashore',   _('Ashore')
        ON_WATER = 'on_water', _('On water')
        LOST     = 'lost',     _('Lost')

    code            = models.CharField(max_length=50, unique=True)
    color           = models.CharField(max_length=10, choices=Color.choices)
    rfid_uid        = models.CharField(max_length=100, blank=True)
    boat            = models.ForeignKey(
                          Boat, null=True, blank=True,
                          on_delete=models.SET_NULL, related_name='sail_tickets'
                      )
    status          = models.CharField(
                          max_length=20, choices=Status.choices,
                          default=Status.ASHORE
                      )
    pending_pairing = models.BooleanField(default=False)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)


class SailTicketLog(models.Model):
    ticket     = models.ForeignKey(SailTicket, on_delete=models.CASCADE, related_name='logs')
    status     = models.CharField(max_length=20, choices=SailTicket.Status.choices)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    note       = models.TextField(blank=True)
```

`pending_pairing`: when True, the next RFID scan of this card sets `rfid_uid` and clears the flag instead of changing status. At most one ticket should be in this state at a time — enforced at the view level.

**Migration (0027):** create `SailTicket` and `SailTicketLog` tables.

### 3d. Bug fix: stable `RegularParticipant` IDs (issue #34)

The formset currently deletes and recreates participants on every Unit save, changing their PKs. Fix: pass existing participant instances to the formset and update in place. Participants are only created for genuinely new rows. Deletions are explicit (checkbox-triggered), not implicit. No migration needed.

### 3e. Evidence ID optional for non-Junák units (issue #44)

`scout_unit_evidence_id` is already `blank=True`. Fix is UX only: mark the field explicitly as optional in the form with help text clarifying that non-Junák units can leave it blank or use their own identifier.

---

## Section 4 — InfoDesk Views & UX

All views behind `@infodesk_required`. Templates live in `templates/SkaRe/infodesk/`.

### InfoDesk dashboard (`/infodesk/`)

Landing page showing:
- Count of unconfirmed registrations (link to validation queue)
- Count of people: arrived / expected / not coming
- Count of sail tickets on water
- Quick links to all InfoDesk operations

### Registration validation queue (`/infodesk/registrations/`)

Table of all registrations (units, individual participants, organizers): name, type, confirmed status, created date. Inline confirm/reject buttons per row. Bulk confirm action for a selection. Rejection leaves `confirmed=False` with no additional state — this is purely a spam filter, not a workflow.

### Attendance — units (`/infodesk/attendance/units/`)

List of all units with arrival status summary (e.g. "Bobři — 12/15 arrived"). Clicking opens the unit detail.

**Unit attendance detail (`/infodesk/attendance/units/<id>/`):**

Table of all participants with columns: name, status, arrived_at, action buttons (Arrived / Departed / Not coming). Top of page has a **"Mark all as arrived"** bulk button. Supports all six arrival workflows:
1. Whole unit arrives, no changes → bulk mark arrived
2. Unit arrives with stragglers → mark individuals
3. Unit arrives with registration changes → edit registration, then mark
4. Individual unit members arrive separately
5. Individually registered participant arrives
6. Organizer arrives

### Attendance — individuals (`/infodesk/attendance/individuals/`)

Same table layout, one row per individual participant. No bulk action.

### Attendance — organizers (`/infodesk/attendance/organizers/`)

Same table layout, one row per organizer. No bulk action.

### Sail ticket management (`/infodesk/tickets/`)

**Ticket list:** all tickets with columns: code, color, boat (if assigned), status, RFID paired (yes/no). Filterable by status and color.

**Ticket detail (`/infodesk/tickets/<id>/`):** full info + status change actions + log of all changes + "Pair RFID" button (sets `pending_pairing=True`; UI shows "waiting for scan…" state).

**Ticket quick lookup (`/infodesk/tickets/lookup/`):** single search box matching ticket code, boat name, sail number, and owner name simultaneously. Results appear inline. Each result row shows ticket code, color, boat, current status, with direct **Ashore / On water / Lost** action buttons — no detail page needed. Primary fallback when RFID readers are unavailable.

**Bulk ticket creation (`/infodesk/tickets/create-bulk/`):** form for reserve counts per color and spare count. Creates tickets for all registered boats + reserves + spares in one action (per BOATS.md spec).

**Boats on water (`/infodesk/tickets/on-water/`):** safety view — all tickets currently `ON_WATER` with boat name, class, description, owner contact.

**Ticket CSV export (`/infodesk/tickets/export/csv/`):** CSV for the printing service (code, color, boat class, sail number, boat name, owner).

### RFID API

The RFID reader API (`/tickets/api/`) is out of scope for this overhaul. The ticket models and `pending_pairing` mechanism are designed to support it when added later.

### Exports (`/infodesk/exports/`)

Page with buttons for each report. Each report available in two formats:
- **Download** — CSV file
- **Print view** — clean HTML table with print CSS (`@media print`), printable directly from the browser

Both exports filter to people with `attendance_status = ARRIVED`.

**Kitchen report format:**

```
Unit "Bobři z Přístavu 523" — 15 people present (3 with dietary restrictions)
  - Jan Novák: vegan, no peanuts
  - Marie Procházková: gluten-free, lactose-free
  - Petr Dvořák: no fruits, other: "also no bee products"
  12 people: no dietary restrictions

Unit "Racci" — 8 people present (no dietary restrictions)

Individual "Tomáš Kratochvíl" — 1 person present (no fish, no eggs)
Individual "Jana Nováková" — 1 person present (no restrictions)

Organizers — 8 people present (1 with dietary restrictions)
  - Ondřej Fišer: vegan
  7 people: no dietary restrictions

TOTAL: 32 people present
```

Individual participants are always listed by name. Units show per-person restrictions only for those who have them; the rest are counted.

**Medical report format:**

All present people with non-empty `health_restrictions`, sorted by unit. Per person:

```
Jan Novák, 14 let — peanut allergy, carries EpiPen
  Unit: Bobři z Přístavu 523 | Vedoucí: +420 777 123 456

Marie Procházková, 22 let — asthma
  Individual participant | Contact: +420 602 987 654
```

Contact shown: unit's `contact_phone` for unit members; person's entity `contact_phone` for individual participants and organizers.

---

## Section 5 — Migrations Sequence

| Migration | Content |
|-----------|---------|
| 0024 | Add `RaceManagement` group (data migration) |
| 0025 | Dietary restructure: add 10 boolean fields + `diet_other` to `Person`; copy `dietary_restrictions` → `diet_other`; remove `dietary_restrictions` |
| 0026 | Attendance: add `attendance_status`, `arrived_at`, `departed_at` to `Person`; create `AttendanceLog` table |
| 0027 | Sail tickets: create `SailTicket` and `SailTicketLog` tables |

No migrations needed for: module reorganisation (pure Python), evidence ID fix (already `blank=True`), stable participant ID fix (view/form logic only), or password validation fix (form logic only).

---

## Section 6 — Open Issues

| Issue | Resolution |
|-------|------------|
| #34 | Stable `RegularParticipant` IDs — fixed in formset logic (no migration) |
| #41 | Password validation messaging — UX fix in form error messages |
| #44 | Evidence ID optional for non-Junák — help text clarification in form |
| #70 | Dietary restrictions — replaced by structured boolean fields (migration 0025) |
| #97 | Participant/boat lending — already implemented in models; no further action |

Out of scope: #27 (external integration, long-term), #46 (race competition registration extension, separate spec needed).

---

## Out of Scope

- RFID reader API (placeholder in `views/tickets.py`, implemented separately)
- Crew rule validation (sail area, age/count vs. category rules) — deferred per existing spec
- Race data export for race director — separate spec when needed
- External system integration (#27)
