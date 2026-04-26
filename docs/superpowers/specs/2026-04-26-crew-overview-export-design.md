# Crew Overview with CSV Export — Design Spec

**Date:** 2026-04-26
**Status:** Approved

## Overview

Add a staff-only crew overview page with filtering, per-crew detail accessible to staff regardless of ownership, and CSV export at both the overview (all/filtered) and per-crew levels. Also adds navigation links from the home page administrator section.

## Scope

- New all-crews overview page with server-side filtering and summary statistics
- New staff-accessible per-crew detail page (separate from the existing owner/infodesk `crew_detail`)
- CSV export for all/filtered crews (from overview) and for a single crew (from detail)
- One new link in the "Administrator options" card on the home page

Out of scope: changes to `crew_detail`, `crew_list`, or `crew_export_csv` (existing views are left unchanged).

## URLs and Views

Four new items added to `SkaRe/urls.py` and implemented in `SkaRe/views/crews.py`. All guarded with `user.is_staff` (redirect to home with error message if not staff).

| View | URL | URL name |
|---|---|---|
| `crew_all` | `crews/all/` | `crew_all` |
| `crew_all_export_csv` | `crews/all/export/csv/` | `crew_all_export_csv` |
| `crew_detail_staff` | `crews/all/<int:crew_id>/` | `crew_detail_staff` |
| `crew_export_single_csv` | `crews/all/<int:crew_id>/export/csv/` | `crew_export_single_csv` |

## View: `crew_all`

**Method:** GET
**Auth:** `@login_required` + `user.is_staff` check

**Query parameters:**
- `q` — free-text search; matches against crew member first name, last name, and boat name (case-insensitive, OR across all three fields)
- `category` — one of the `Crew.CATEGORY_CHOICES` codes, or empty for all

**Query:** Start from `Crew` and filter with ORM traversals:

```python
qs = Crew.objects.select_related('boat', 'boat__boat_class').prefetch_related('members__participant')
if category:
    qs = qs.filter(category=category)
if q:
    qs = qs.filter(
        Q(boat__name__icontains=q) |
        Q(members__participant__first_name__icontains=q) |
        Q(members__participant__last_name__icontains=q)
    ).distinct()
```

**Context passed to template:**
- `crews` — filtered queryset of `Crew` objects (with member prefetch)
- `total_crews` — total crew count (unfiltered)
- `filtered_count` — count after applying filters
- `category_stats` — dict mapping category code → count (unfiltered, for stats bar)
- `category_choices` — `Crew.CATEGORY_CHOICES` (for dropdown)
- `q` — current search value (to repopulate input)
- `selected_category` — current category filter value (to repopulate dropdown)

## View: `crew_all_export_csv`

**Method:** GET
**Auth:** `@login_required` + `user.is_staff` check

Accepts the same `q` and `category` GET params as `crew_all` and applies the same filtering logic. Outputs UTF-8 CSV with BOM.

**Filename:** `crews.csv` (unfiltered) or `crews_<category>.csv` / `crews_search.csv` when filtered.

**Columns** (same structure as existing `crew_export_csv`):
`crew_id`, `category`, `boat_sail_number`, `boat_name`, `boat_class`, `sail_area`, `role`, `first_name`, `last_name`, `date_of_birth`, `scout_category`, `participant_type`, `unit_name`

Uses `_csv_safe()` from `views/exports.py` for injection-safe output.

## View: `crew_detail_staff`

**Method:** GET
**Auth:** `@login_required` + `user.is_staff` check
**Template:** `SkaRe/crews/detail_staff.html`

Fetches crew by `crew_id` (404 if not found). No `can_be_edited()` check — staff can view any crew. Passes:
- `crew`
- `members` (ordered: helmsman first, then crew)
- Back link to `crew_all` (preserving no filter state — simple back link)
- Export link to `crew_export_single_csv`

The template extends or mirrors `crews/detail.html` with two additions: a "Back to Crew Overview" button and an "Export CSV" button. It does **not** show edit/delete controls.

## View: `crew_export_single_csv`

**Method:** GET
**Auth:** `@login_required` + `user.is_staff` check

Fetches crew by `crew_id` (404 if not found). Outputs one row per crew member.

**Filename:** `crew_<id>.csv`

**Columns:** Same as `crew_all_export_csv`.

## Template: `crews/all.html`

Structure:

```
<h1> All Crews </h1>

[Stats bar — alert-info]
Total: X / Y crews  |  Q: n  S: n  R: n  D: n  SN: n  DN: n  OŽ: n  OD: n  MS: n

[Filter form — GET]
  [text input: q]  [category dropdown]  [Search button]
  [Clear button — plain anchor to crew_all with no params]

[Export CSV button → crew_all_export_csv?q=...&category=...]

[Table]
  Category | Boat | Helmsman | Members | Actions
  ...rows...

[Back to Home]
```

Stats bar shows "X / Y crews" when filters are active (X = filtered_count, Y = total_crews), or just "Y crews" when no filter is applied. Per-category counts are always unfiltered totals (for a stable reference).

## Template: `crews/detail_staff.html`

Mirrors existing `crews/detail.html`. Differences:
- No edit/delete buttons
- "Back to Crew Overview" → `crew_all`
- "Export CSV" button → `crew_export_single_csv` for this crew

## Home Page Change

In `registration/home.html`, inside the `{% if user.is_staff %}` "Administrator options" card, add one button:

```html
<a class="btn btn-warning" href="{% url 'SkaRe:crew_all' %}">
    <i class="bi bi-people-fill"></i> {% trans "Crew Overview" %}
</a>
```

## Security

All four new views check `user.is_staff` explicitly after `@login_required`. Non-staff users are redirected to `home` with an error message (consistent with `crew_export_csv` pattern). No new model permissions or groups introduced.

## What Is Not Changed

- `crew_export_csv` at `crews/export/csv/` — left as-is
- `crew_detail` at `crews/<id>/` — permission logic unchanged
- `crew_list` at `crews/` — unchanged
- No new models or migrations
