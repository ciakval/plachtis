# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PlachtIS is a Django 6.0 event registration system for SkaRe (a sailing event). It manages scout unit registrations, individual/organizer participants, boat registrations, and event logistics. Primary language is Czech.

## Common Commands

```bash
# Development server
uv run manage.py runserver

# Database migrations
uv run manage.py migrate
uv run manage.py makemigrations

# Run all tests
uv run manage.py test

# Run tests for specific module / class / method
uv run manage.py test SkaRe.tests.test_boat_views
uv run manage.py test SkaRe.tests.test_boat_views.SailLookupViewTest
uv run manage.py test SkaRe.tests.test_boat_views.SailLookupViewTest.test_found_returns_json

# Useful test flags
uv run manage.py test --failfast --keepdb --verbosity=2

# Seed test data
uv run manage.py seed_small
uv run manage.py seed_medium
uv run manage.py seed_large

# Translations (compile after editing .po files)
uv run manage.py compilemessages

# Django system checks
uv run manage.py check
uv run manage.py check --deploy  # production validation
```

## Architecture

### Apps & Key Files

- **`PlachtIS/`** — Django project: `settings.py`, `urls.py` (root router)
- **`SkaRe/`** — Single Django app containing all business logic:
  - `models/` — Data models split by domain: `registration.py`, `boats.py`, `tickets.py`, `attendance.py`
  - `views/` — Function-based views split by domain: `registration.py`, `boats.py`, `crews.py`, `tickets.py`, `attendance.py`, `infodesk.py`, `exports.py`
  - `forms/` — Forms split by domain: `registration.py`, `boats.py`, `crews.py`, `tickets.py`
  - `permissions.py` — `infodesk_required` / `is_infodesk` / `is_race_management` helpers
  - `urls.py` — App URL routing
  - `form_utils.py` — CSRF token helpers for duplicate-submission prevention
  - `context_processors.py` — Injects `VERSION`/`BUILD_ID` into all templates
  - `management/commands/` — `seed_small/medium/large.py` seeding commands
  - `tests/` — Test suite (boat, crew, registration, ticket, attendance, infodesk, exports, permissions)

### Data Model

```
Person (abstract base)
├── RegularParticipant  — member of a Unit
├── IndividualParticipant — has its own Entity
└── Organizer           — has its own Entity

Entity  — registration owner/editor metadata
├── Unit (scout troop) — has RegularParticipants via formset
├── IndividualParticipant (OneToOne)
└── Organizer (OneToOne)

EventSettings (django-solo singleton) — registration/editing deadlines

BoatClass → Boat (created_by User, references BoatClass)
Crew → CrewMember (references Person)

SailTicket (RFID-tagged ticket per person, rfid_uid field) → SailTicketLog
AttendanceLog (event attendance tracking)
```

### Permission Model

Ownership is tracked via `Entity.created_by`. Editors can be delegated via `Entity.editors` (ManyToMany). Key model methods: `can_be_edited()`, `can_manage_editors()`, `is_owner()`. After registration deadline, edits are blocked unless `Entity.unlocked_for_editing=True`.

### Key Patterns

- **Singleton settings**: `EventSettings.get_solo()` via `django-solo`; controls `is_registration_open()` / `is_editing_open()`
- **Atomic transactions**: Boat create/edit wrapped in `@transaction.atomic`
- **External API**: Google Sheets CSV fetched for sail registry lookup, cached 1 hour (configurable via `SAIL_REGISTRY_CACHE_TTL`). Returns 503 on fetch failure, 404 on missing sail number.
- **Formsets**: `get_participant_formset()` handles dynamic participants when registering a unit
- **Phone validation**: `validate_czech_phone()` and `validate_event_phone()` in `forms.py`

### Configuration

Environment variables (see `.env.example`):
- `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`
- `SAIL_REGISTRY_SHEET_URL` — Google Sheets CSV URL for sail lookup
- `SAIL_REGISTRY_CACHE_TTL` — cache duration in seconds (default 3600)

SQLite is used in development (`db.sqlite3`). Production runs on Docker + Gunicorn + Caddy reverse proxy, deployed via GitHub Actions to a VPS.
