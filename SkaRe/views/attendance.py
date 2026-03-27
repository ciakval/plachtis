from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponseBadRequest, HttpResponseNotAllowed
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from ..permissions import infodesk_required
from ..models import Unit, IndividualParticipant, Organizer, Person, AttendanceLog

VALID_STATUSES = {s.value for s in Person.AttendanceStatus}


@infodesk_required
def attendance_units_list(request):
    units = Unit.objects.select_related('entity').annotate(
        total=Count('regular_participants'),
        arrived=Count('regular_participants', filter=Q(
            regular_participants__attendance_status=Person.AttendanceStatus.ARRIVED
        )),
    ).order_by('entity__scout_unit_name')
    return render(request, 'SkaRe/attendance/units_list.html', {'units': units})


@infodesk_required
def attendance_unit_detail(request, unit_id):
    unit = get_object_or_404(Unit.objects.select_related('entity'), pk=unit_id)
    participants = unit.regular_participants.order_by('last_name', 'first_name')
    return render(request, 'SkaRe/attendance/unit_detail.html', {
        'unit': unit,
        'participants': participants,
        'statuses': Person.AttendanceStatus,
    })


@infodesk_required
def attendance_individuals_list(request):
    individuals = IndividualParticipant.objects.select_related('entity').order_by('last_name', 'first_name')
    return render(request, 'SkaRe/attendance/individuals_list.html', {
        'individuals': individuals,
        'statuses': Person.AttendanceStatus,
    })


@infodesk_required
def attendance_organizers_list(request):
    organizers = Organizer.objects.select_related('entity').order_by('last_name', 'first_name')
    return render(request, 'SkaRe/attendance/organizers_list.html', {
        'organizers': organizers,
        'statuses': Person.AttendanceStatus,
    })


@infodesk_required
def attendance_set_status(request, person_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    person = get_object_or_404(Person, pk=person_id)
    new_status = request.POST.get('new_status', '')
    if new_status not in VALID_STATUSES:
        return HttpResponseBadRequest('Invalid status')

    now = timezone.now()
    person.attendance_status = new_status
    if new_status == Person.AttendanceStatus.ARRIVED:
        person.arrived_at = now
    elif new_status == Person.AttendanceStatus.DEPARTED:
        person.departed_at = now
    else:
        person.arrived_at = None
        person.departed_at = None
    person.save(update_fields=['attendance_status', 'arrived_at', 'departed_at'])

    AttendanceLog.objects.create(
        person=person,
        status=new_status,
        changed_by=request.user,
    )

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER', '')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect('SkaRe:infodesk_dashboard')


@infodesk_required
def attendance_unit_mark_all_arrived(request, unit_id):
    if request.method != 'POST':
        return redirect('SkaRe:attendance_unit_detail', unit_id=unit_id)
    unit = get_object_or_404(Unit, pk=unit_id)
    now = timezone.now()
    to_mark = unit.regular_participants.filter(
        attendance_status=Person.AttendanceStatus.EXPECTED
    )
    with transaction.atomic():
        to_update = list(to_mark)
        for person in to_update:
            person.attendance_status = Person.AttendanceStatus.ARRIVED
            person.arrived_at = now
        Person.objects.bulk_update(to_update, ['attendance_status', 'arrived_at'])
        AttendanceLog.objects.bulk_create([
            AttendanceLog(
                person=person,
                status=Person.AttendanceStatus.ARRIVED,
                changed_by=request.user,
            )
            for person in to_update
        ])
    messages.success(request, _('%(n)d participants marked as arrived.') % {'n': len(to_update)})
    return redirect('SkaRe:attendance_unit_detail', unit_id=unit_id)
