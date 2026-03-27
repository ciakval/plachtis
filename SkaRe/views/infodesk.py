from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext as _
from ..permissions import infodesk_required
from ..models import Entity, Person, SailTicket


@infodesk_required
def infodesk_dashboard(request):
    unconfirmed_count = Entity.objects.filter(confirmed=False).count()
    arrived_count = Person.objects.filter(attendance_status=Person.AttendanceStatus.ARRIVED).count()
    expected_count = Person.objects.filter(attendance_status=Person.AttendanceStatus.EXPECTED).count()
    not_coming_count = Person.objects.filter(attendance_status=Person.AttendanceStatus.NOT_COMING).count()
    on_water_count = SailTicket.objects.filter(status=SailTicket.Status.ON_WATER).count()
    return render(request, 'SkaRe/infodesk/dashboard.html', {
        'unconfirmed_count': unconfirmed_count,
        'arrived_count': arrived_count,
        'expected_count': expected_count,
        'not_coming_count': not_coming_count,
        'on_water_count': on_water_count,
    })


def _entity_row(entity):
    """Return (name, type_label) for an Entity.

    Uses hasattr to detect which reverse OneToOne profile exists.
    Django 3.2+ changed RelatedObjectDoesNotExist handling so that
    hasattr() returns False instead of propagating the exception —
    this is safe as long as we use select_related() in the view query.
    """
    if hasattr(entity, 'unit_profile'):
        return entity.scout_unit_name or f'Unit #{entity.pk}', _('Unit')
    elif hasattr(entity, 'individual_participant_profile'):
        return str(entity.individual_participant_profile), _('Individual')
    elif hasattr(entity, 'organizer_profile'):
        return str(entity.organizer_profile), _('Organizer')
    return f'Entity #{entity.pk}', _('Unknown')


@infodesk_required
def infodesk_registrations(request):
    entities = Entity.objects.select_related(
        'unit_profile',
        'individual_participant_profile',
        'organizer_profile',
    ).order_by('created_at')

    rows = []
    for entity in entities:
        name, type_label = _entity_row(entity)
        rows.append({'entity': entity, 'name': name, 'type': type_label})

    return render(request, 'SkaRe/infodesk/registrations.html', {'rows': rows})


@infodesk_required
def infodesk_confirm_entity(request, entity_id):
    if request.method != 'POST':
        return redirect('SkaRe:infodesk_registrations')
    entity = get_object_or_404(Entity, pk=entity_id)
    entity.confirmed = True
    entity.save(update_fields=['confirmed'])
    messages.success(request, _('Registration confirmed.'))
    return redirect('SkaRe:infodesk_registrations')


@infodesk_required
def infodesk_reject_entity(request, entity_id):
    if request.method != 'POST':
        return redirect('SkaRe:infodesk_registrations')
    entity = get_object_or_404(Entity, pk=entity_id)
    entity.confirmed = False
    entity.save(update_fields=['confirmed'])
    messages.success(request, _('Registration rejected.'))
    return redirect('SkaRe:infodesk_registrations')


@infodesk_required
def infodesk_bulk_confirm(request):
    if request.method != 'POST':
        return redirect('SkaRe:infodesk_registrations')
    raw_ids = request.POST.getlist('entity_ids')
    ids = []
    for raw in raw_ids:
        try:
            ids.append(int(raw))
        except (ValueError, TypeError):
            pass
    if ids:
        Entity.objects.filter(pk__in=ids).update(confirmed=True)
        messages.success(request, _('%(n)d registrations confirmed.') % {'n': len(ids)})
    return redirect('SkaRe:infodesk_registrations')
