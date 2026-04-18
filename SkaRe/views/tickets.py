import csv
import re
from collections import defaultdict
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from ..permissions import infodesk_required
from ..models import SailTicket, SailTicketLog, Boat, BoatClass
from ..forms import BulkTicketCreateForm

VALID_TICKET_STATUSES = {s.value for s in SailTicket.Status}


def _csv_safe(value):
    """Prefix cells starting with formula characters to prevent CSV injection."""
    s = str(value) if value else ''
    if s and s[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + s
    return s


def _boat_color(boat):
    """Map a registered boat to the corresponding SailTicket.Color."""
    if not boat.boat_class:
        return SailTicket.Color.OTHER
    if boat.boat_class.name == 'P550':
        return SailTicket.Color.P550
    if boat.boat_class.category == BoatClass.Category.SAIL:
        return SailTicket.Color.SAIL
    return SailTicket.Color.OTHER


COLOR_PREFIX = {
    SailTicket.Color.P550: 'P550',
    SailTicket.Color.SAIL: 'SAIL',
    SailTicket.Color.OTHER: 'OTHER',
    SailTicket.Color.SPARE: 'SPARE',
}


def _extract_numeric(sail_number):
    """Extract the integer from a sail number string, e.g. 'CZE 1234' → 1234.

    Returns None if no digits are present or the result is zero.
    """
    digits = re.sub(r'\D', '', sail_number)
    n = int(digits) if digits else 0
    return n if n > 0 else None


def _build_ticket_plan(boats, reserve_counts, spare_count):
    """Return a list of unsaved SailTicket instances representing the full plan.

    Each ticket is annotated with a ``from_sail_number`` bool attribute.

    Args:
        boats: queryset of Boat objects, select_related('boat_class')
        reserve_counts: dict mapping SailTicket.Color → int (reserves per category)
        spare_count: int — number of SPARE tickets to generate
    """
    boat_groups = {
        SailTicket.Color.P550: [],
        SailTicket.Color.SAIL: [],
        SailTicket.Color.OTHER: [],
    }
    for boat in boats.order_by('pk'):
        color = _boat_color(boat)
        boat_groups[color].append(boat)

    tickets = []

    for color, color_boats in boat_groups.items():
        prefix = COLOR_PREFIX[color]
        claimed = {}    # int number → Boat
        unnumbered = []

        for boat in color_boats:
            num = _extract_numeric(boat.sail_number) if boat.sail_number else None
            if num is not None and num not in claimed:
                claimed[num] = boat
            else:
                unnumbered.append(boat)

        total_sequential = len(unnumbered) + reserve_counts.get(color, 0)
        sequential = []
        n = 1
        while len(sequential) < total_sequential:
            if n not in claimed:
                sequential.append(n)
            n += 1

        for num, boat in claimed.items():
            t = SailTicket(code=f'{prefix}-{num}', color=color, boat=boat)
            t.from_sail_number = True
            tickets.append(t)

        for i, boat in enumerate(unnumbered):
            t = SailTicket(code=f'{prefix}-{sequential[i]}', color=color, boat=boat)
            t.from_sail_number = False
            tickets.append(t)

        for i in range(len(unnumbered), total_sequential):
            t = SailTicket(code=f'{prefix}-{sequential[i]}', color=color)
            t.from_sail_number = False
            tickets.append(t)

    for i in range(1, spare_count + 1):
        t = SailTicket(code=f'SPARE-{i}', color=SailTicket.Color.SPARE)
        t.from_sail_number = False
        tickets.append(t)

    return tickets


@infodesk_required
def ticket_list(request):
    tickets = SailTicket.objects.select_related('boat', 'boat__boat_class')
    status_filter = request.GET.get('status', '')
    color_filter = request.GET.get('color', '')
    if status_filter in VALID_TICKET_STATUSES:
        tickets = tickets.filter(status=status_filter)
    if color_filter in {c.value for c in SailTicket.Color}:
        tickets = tickets.filter(color=color_filter)
    return render(request, 'SkaRe/tickets/list.html', {
        'tickets': tickets,
        'status_filter': status_filter,
        'color_filter': color_filter,
        'statuses': SailTicket.Status,
        'colors': SailTicket.Color,
    })


@infodesk_required
def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(
        SailTicket.objects.select_related('boat', 'boat__boat_class'),
        pk=ticket_id,
    )
    logs = ticket.logs.select_related('changed_by').order_by('-changed_at')
    return render(request, 'SkaRe/tickets/detail.html', {
        'ticket': ticket,
        'logs': logs,
        'statuses': SailTicket.Status,
    })


@infodesk_required
def ticket_set_status(request, ticket_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    ticket = get_object_or_404(SailTicket, pk=ticket_id)
    new_status = request.POST.get('new_status', '')
    if new_status not in VALID_TICKET_STATUSES:
        return HttpResponseBadRequest('Invalid status')
    ticket.status = new_status
    ticket.save(update_fields=['status', 'updated_at'])
    SailTicketLog.objects.create(
        ticket=ticket,
        status=new_status,
        changed_by=request.user,
    )
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER', '')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect('SkaRe:ticket_detail', ticket_id=ticket.pk)


@infodesk_required
def ticket_pair_rfid(request, ticket_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    ticket = get_object_or_404(SailTicket, pk=ticket_id)
    with transaction.atomic():
        SailTicket.objects.filter(pending_pairing=True).update(pending_pairing=False)
        ticket.pending_pairing = True
        ticket.save(update_fields=['pending_pairing', 'updated_at'])
    messages.info(request, _('Waiting for RFID scan on ticket %(code)s\u2026') % {'code': ticket.code})
    return redirect('SkaRe:ticket_detail', ticket_id=ticket.pk)


@infodesk_required
def ticket_unpair_rfid(request, ticket_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    ticket = get_object_or_404(SailTicket, pk=ticket_id)
    if not ticket.rfid_uid:
        return HttpResponseBadRequest('Ticket has no paired card')
    ticket.rfid_uid = ''
    ticket.save(update_fields=['rfid_uid', 'updated_at'])
    SailTicketLog.objects.create(
        ticket=ticket,
        status=ticket.status,
        changed_by=request.user,
        note=f'RFID card unpaired by {request.user.username}',
    )
    messages.success(request, _('RFID card unpaired from ticket %(code)s.') % {'code': ticket.code})
    return redirect('SkaRe:ticket_detail', ticket_id=ticket.pk)


@infodesk_required
def ticket_lookup(request):
    query = request.GET.get('q', '').strip()
    results = []
    if query:
        results = SailTicket.objects.filter(
            Q(code__icontains=query) |
            Q(boat__name__icontains=query) |
            Q(boat__sail_number__icontains=query) |
            Q(boat__contact_person__icontains=query)
        ).select_related('boat', 'boat__boat_class').order_by('code')
    return render(request, 'SkaRe/tickets/lookup.html', {
        'query': query,
        'results': results,
        'statuses': SailTicket.Status,
    })


@infodesk_required
def ticket_create_bulk(request):
    if request.method == 'POST':
        form = BulkTicketCreateForm(request.POST)
        if form.is_valid():
            reserve_counts = {
                SailTicket.Color.P550: form.cleaned_data['p550_reserves'],
                SailTicket.Color.SAIL: form.cleaned_data['sail_reserves'],
                SailTicket.Color.OTHER: form.cleaned_data['other_reserves'],
            }
            spare_count = form.cleaned_data['spare_count']
            boats = Boat.objects.select_related('boat_class')
            plan = _build_ticket_plan(boats, reserve_counts, spare_count)

            if request.POST.get('confirm') == '1':
                with transaction.atomic():
                    SailTicket.objects.all().delete()
                    SailTicket.objects.bulk_create(plan)
                messages.success(request, _('%(n)d tickets created.') % {'n': len(plan)})
                return redirect('SkaRe:ticket_list')

            # Step 1: show preview — group tickets by color for the template
            groups = defaultdict(list)
            for ticket in plan:
                groups[ticket.color].append(ticket)
            color_order = [
                SailTicket.Color.P550,
                SailTicket.Color.SAIL,
                SailTicket.Color.OTHER,
                SailTicket.Color.SPARE,
            ]
            plan_by_color = [
                (SailTicket.Color(color).label, groups[color])
                for color in color_order
                if groups[color]
            ]
            return render(request, 'SkaRe/tickets/create_bulk.html', {
                'form': form,
                'plan': plan,
                'plan_by_color': plan_by_color,
                'existing_ticket_count': SailTicket.objects.count(),
            })
    else:
        form = BulkTicketCreateForm()

    all_boats = Boat.objects.select_related('boat_class')
    boat_preview = {}
    for boat in all_boats:
        color = _boat_color(boat)
        boat_preview[color] = boat_preview.get(color, 0) + 1

    return render(request, 'SkaRe/tickets/create_bulk.html', {
        'form': form,
        'boat_preview': boat_preview,
        'existing_ticket_count': SailTicket.objects.count(),
    })


@infodesk_required
def ticket_on_water(request):
    tickets = SailTicket.objects.filter(
        status=SailTicket.Status.ON_WATER
    ).select_related('boat', 'boat__boat_class', 'boat__created_by')
    return render(request, 'SkaRe/tickets/on_water.html', {'tickets': tickets})


@infodesk_required
def ticket_export_csv(request):
    tickets = SailTicket.objects.select_related(
        'boat', 'boat__boat_class'
    ).order_by('color', 'code')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="sail_tickets.csv"'
    response.write('\ufeff')  # UTF-8 BOM for Excel

    writer = csv.writer(response)
    writer.writerow([
        'Code', 'Color', 'Boat class', 'Sail number', 'Boat name', 'Harbor',
        'Contact person', 'Contact phone', 'RFID UID', 'Status',
    ])
    for ticket in tickets:
        boat = ticket.boat
        writer.writerow([
            ticket.code,
            ticket.color,
            _csv_safe(boat.boat_class.name) if boat and boat.boat_class else '',
            boat.sail_number if boat else '',
            _csv_safe(boat.name) if boat else '',
            _csv_safe(str(boat.harbor_number) + " " + boat.harbor_name) if boat else '',
            _csv_safe(boat.contact_person) if boat else '',
            _csv_safe(boat.contact_phone) if boat else '',
            _csv_safe(ticket.rfid_uid),
            ticket.status,
        ])
    return response
