import csv
from datetime import date

from django.db.models import Count, Q
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext as _

from ..models import (
    IndividualParticipant,
    Organizer,
    Person,
    RegularParticipant,
    Unit,
)
from ..permissions import infodesk_required

DIET_FIELDS = [
    ('diet_vegetarian', _('Vegetarian')),
    ('diet_vegan', _('Vegan')),
    ('diet_no_soy', _('No soy')),
    ('diet_lactose_free', _('Lactose-free')),
    ('diet_gluten_free', _('Gluten-free')),
    ('diet_no_peanuts', _('No peanuts')),
    ('diet_no_eggs', _('No eggs')),
    ('diet_no_fish', _('No fish')),
]


def _csv_safe(value):
    """Prefix cells starting with formula characters to prevent CSV injection."""
    s = str(value) if value else ''
    if s and s[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + s
    return s


def _fmt_dt(dt):
    if not dt:
        return ''
    if timezone.is_aware(dt):
        dt = timezone.localtime(dt)
    return dt.strftime('%Y-%m-%d %H:%M')


def _age(date_of_birth):
    today = date.today()
    return today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )


def _arrived_unit_participants():
    return (
        RegularParticipant.objects.filter(
            attendance_status=Person.AttendanceStatus.ARRIVED
        ).select_related('unit__entity').order_by(
            'unit__entity__scout_unit_name', 'last_name', 'first_name'
        )
    )


def _arrived_individuals():
    return (
        IndividualParticipant.objects.filter(
            attendance_status=Person.AttendanceStatus.ARRIVED
        ).select_related('entity').order_by('last_name', 'first_name')
    )


def _arrived_organizers():
    return (
        Organizer.objects.filter(
            attendance_status=Person.AttendanceStatus.ARRIVED
        ).select_related('entity').order_by('last_name', 'first_name')
    )


@infodesk_required
def exports_index(request):
    return render(request, 'SkaRe/exports/index.html')


@infodesk_required
def exports_kitchen_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="kitchen_report.csv"'
    response.write('\ufeff')  # UTF-8 BOM for Excel

    writer = csv.writer(response)
    diet_labels = [label for _, label in DIET_FIELDS]
    writer.writerow([
        _('Name'), _('Type'), _('Unit/Group'),
        *diet_labels,
        _('Other dietary restrictions'),
    ])

    for p in _arrived_unit_participants():
        diet_values = [getattr(p, field) for field, _ in DIET_FIELDS]
        writer.writerow([
            _csv_safe(p), _('Unit member'), _csv_safe(p.unit.entity.scout_unit_name),
            *diet_values, _csv_safe(p.diet_other),
        ])

    for p in _arrived_individuals():
        diet_values = [getattr(p, field) for field, _ in DIET_FIELDS]
        writer.writerow([
            _csv_safe(p), _('Individual'), _('Individual participant'),
            *diet_values, _csv_safe(p.diet_other),
        ])

    for p in _arrived_organizers():
        diet_values = [getattr(p, field) for field, _ in DIET_FIELDS]
        writer.writerow([
            _csv_safe(p), _('Organizer'), _('Organizer'),
            *diet_values, _csv_safe(p.diet_other),
        ])

    return response


@infodesk_required
def exports_kitchen_print(request):
    unit_participants = _arrived_unit_participants()
    units_map = {}
    for p in unit_participants:
        uid = p.unit.pk
        if uid not in units_map:
            units_map[uid] = {
                'unit': p.unit,
                'with_restrictions': [],
                'clean_count': 0,
            }
        if p.dietary_summary():
            units_map[uid]['with_restrictions'].append(p)
        else:
            units_map[uid]['clean_count'] += 1

    individuals = list(_arrived_individuals())
    organizers = list(_arrived_organizers())

    organizers_with_restrictions = []
    organizers_clean_count = 0
    for o in organizers:
        if o.dietary_summary():
            organizers_with_restrictions.append(o)
        else:
            organizers_clean_count += 1

    total = (
        sum(len(d['with_restrictions']) + d['clean_count'] for d in units_map.values())
        + len(individuals)
        + len(organizers)
    )

    return render(request, 'SkaRe/exports/kitchen_print.html', {
        'units_data': list(units_map.values()),
        'individuals': individuals,
        'organizers': organizers,
        'organizers_with_restrictions': organizers_with_restrictions,
        'organizers_clean_count': organizers_clean_count,
        'total': total,
    })


@infodesk_required
def exports_medical_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="medical_report.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow([
        _('Name'), _('Date of birth'), _('Age'), _('Type'), _('Unit/Group'),
        _('Contact phone'), _('Health restrictions'),
    ])

    for p in _arrived_unit_participants():
        if not p.health_restrictions:
            continue
        writer.writerow([
            _csv_safe(p), p.date_of_birth, _age(p.date_of_birth),
            _('Unit member'), _csv_safe(p.unit.entity.scout_unit_name),
            _csv_safe(p.unit.entity.contact_phone), _csv_safe(p.health_restrictions),
        ])

    for p in _arrived_individuals():
        if not p.health_restrictions:
            continue
        writer.writerow([
            _csv_safe(p), p.date_of_birth, _age(p.date_of_birth),
            _('Individual'), _('Individual participant'),
            _csv_safe(p.entity.contact_phone), _csv_safe(p.health_restrictions),
        ])

    for p in _arrived_organizers():
        if not p.health_restrictions:
            continue
        writer.writerow([
            _csv_safe(p), p.date_of_birth, _age(p.date_of_birth),
            _('Organizer'), _('Organizer'),
            _csv_safe(p.entity.contact_phone), _csv_safe(p.health_restrictions),
        ])

    return response


@infodesk_required
def exports_medical_print(request):
    unit_participants = [
        p for p in _arrived_unit_participants() if p.health_restrictions
    ]
    individuals = [p for p in _arrived_individuals() if p.health_restrictions]
    organizers = [p for p in _arrived_organizers() if p.health_restrictions]

    return render(request, 'SkaRe/exports/medical_print.html', {
        'unit_participants': unit_participants,
        'individuals': individuals,
        'organizers': organizers,
    })


def _unit_category_stats():
    """Map unit_id -> {adult, rover, scout, cub, total}."""
    rows = (
        RegularParticipant.objects.values('unit')
        .annotate(
            total=Count('id'),
            adult=Count('id', filter=Q(category=Person.ScoutCategory.ADULT)),
            rover=Count('id', filter=Q(category=Person.ScoutCategory.ROVER)),
            scout=Count('id', filter=Q(category=Person.ScoutCategory.SCOUT)),
            cub=Count('id', filter=Q(category=Person.ScoutCategory.CUB)),
        )
    )
    return {r['unit']: r for r in rows}


def _individual_category_cells(category):
    c = Person.ScoutCategory
    if not category:
        return [0, 0, 0, 0, 1]
    return [
        1 if category == c.ADULT else 0,
        1 if category == c.ROVER else 0,
        1 if category == c.SCOUT else 0,
        1 if category == c.CUB else 0,
        0 if category in (c.ADULT, c.ROVER, c.SCOUT, c.CUB) else 1,
    ]


@login_required
def exports_organizer_units_csv(request):
    """CSV overview of units and individual participants for event organizers."""
    if not request.user.is_staff:
        return HttpResponseForbidden()

    stats_by_unit = _unit_category_stats()
    units = Unit.objects.select_related('entity').order_by('entity__scout_unit_name', 'pk')
    individuals = IndividualParticipant.objects.select_related('entity').order_by(
        'last_name', 'first_name', 'pk'
    )

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="units_and_individuals_overview.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow([
        _('Registration type'),
        _('Name'),
        _('Evidence ID'),
        _('Leader / contact person'),
        _('Contact email'),
        _('Contact phone'),
        _('Backup contact phone'),
        _('Home town'),
        _('Participants total'),
        _('Participants — Adult'),
        _('Participants — Rover'),
        _('Participants — Scout'),
        _('Participants — Cub'),
        _('Participants — other or unset category'),
        _('Registration created'),
        _('Expected arrival'),
        _('Expected departure'),
        _('Confirmed'),
        _('Paid'),
    ])

    for unit in units:
        ent = unit.entity
        st = stats_by_unit.get(unit.pk, {})
        total = st.get('total', 0)
        adult = st.get('adult', 0)
        rover = st.get('rover', 0)
        scout = st.get('scout', 0)
        cub = st.get('cub', 0)
        other = max(0, total - adult - rover - scout - cub)
        writer.writerow([
            _('Unit'),
            _csv_safe(ent.scout_unit_name),
            _csv_safe(ent.scout_unit_evidence_id),
            _csv_safe(unit.contact_person_name),
            _csv_safe(ent.contact_email),
            _csv_safe(ent.contact_phone),
            _csv_safe(unit.backup_contact_phone),
            _csv_safe(ent.home_town),
            total,
            adult,
            rover,
            scout,
            cub,
            other,
            _fmt_dt(ent.created_at),
            _fmt_dt(ent.expected_arrival),
            _fmt_dt(ent.expected_departure),
            _('Yes') if ent.confirmed else _('No'),
            _('Yes') if ent.paid else _('No'),
        ])

    for p in individuals:
        ent = p.entity
        adult, rover, scout, cub, other = _individual_category_cells(p.category)
        writer.writerow([
            _('Individual participant'),
            _csv_safe(str(p)),
            _csv_safe(ent.scout_unit_evidence_id),
            _csv_safe(str(p)),
            _csv_safe(ent.contact_email),
            _csv_safe(ent.contact_phone),
            '',
            _csv_safe(ent.home_town),
            1,
            adult,
            rover,
            scout,
            cub,
            other,
            _fmt_dt(ent.created_at),
            _fmt_dt(ent.expected_arrival),
            _fmt_dt(ent.expected_departure),
            _('Yes') if ent.confirmed else _('No'),
            _('Yes') if ent.paid else _('No'),
        ])

    return response
