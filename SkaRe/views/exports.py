import csv
from datetime import date
from django.shortcuts import render
from django.http import HttpResponse
from django.utils.translation import gettext as _
from ..permissions import infodesk_required
from ..models import (
    Person, RegularParticipant, IndividualParticipant, Organizer,
)

DIET_FIELDS = [
    ('diet_vegan', _('Vegan')),
    ('diet_vegetarian', _('Vegetarian')),
    ('diet_gluten_free', _('Gluten-free')),
    ('diet_lactose_free', _('Lactose/dairy-free')),
    ('diet_no_eggs', _('No eggs')),
    ('diet_no_peanuts', _('No peanuts')),
    ('diet_no_tree_nuts', _('No tree nuts')),
    ('diet_no_soy', _('No soy')),
    ('diet_no_fish', _('No fish')),
    ('diet_no_fruits', _('No fruits')),
]


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
            str(p), _('Unit member'), p.unit.entity.scout_unit_name,
            *diet_values, p.diet_other,
        ])

    for p in _arrived_individuals():
        diet_values = [getattr(p, field) for field, _ in DIET_FIELDS]
        writer.writerow([
            str(p), _('Individual'), _('Individual participant'),
            *diet_values, p.diet_other,
        ])

    for p in _arrived_organizers():
        diet_values = [getattr(p, field) for field, _ in DIET_FIELDS]
        writer.writerow([
            str(p), _('Organizer'), _('Organizer'),
            *diet_values, p.diet_other,
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
            str(p), p.date_of_birth, _age(p.date_of_birth),
            _('Unit member'), p.unit.entity.scout_unit_name,
            p.unit.entity.contact_phone, p.health_restrictions,
        ])

    for p in _arrived_individuals():
        if not p.health_restrictions:
            continue
        writer.writerow([
            str(p), p.date_of_birth, _age(p.date_of_birth),
            _('Individual'), _('Individual participant'),
            p.entity.contact_phone, p.health_restrictions,
        ])

    for p in _arrived_organizers():
        if not p.health_restrictions:
            continue
        writer.writerow([
            str(p), p.date_of_birth, _age(p.date_of_birth),
            _('Organizer'), _('Organizer'),
            p.entity.contact_phone, p.health_restrictions,
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
