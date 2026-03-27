import csv
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


def _boat_color(boat):
    """Map a registered boat to the corresponding SailTicket.Color."""
    if not boat.boat_class:
        return SailTicket.Color.OTHER
    if boat.boat_class.name == 'P550':
        return SailTicket.Color.P550
    if boat.boat_class.category == BoatClass.Category.SAIL:
        return SailTicket.Color.SAIL
    return SailTicket.Color.OTHER


def _generate_codes(color_prefix, count):
    """Generate `count` unique sequential codes for the given prefix, skipping existing ones."""
    existing = set(
        SailTicket.objects.filter(code__startswith=f'{color_prefix}-')
        .values_list('code', flat=True)
    )
    codes = []
    n = 1
    limit = count + len(existing) + 1
    while len(codes) < count and n <= limit:
        code = f'{color_prefix}-{n:03d}'
        if code not in existing:
            codes.append(code)
        n += 1
    return codes


COLOR_PREFIX = {
    SailTicket.Color.P550: 'P550',
    SailTicket.Color.SAIL: 'SAIL',
    SailTicket.Color.OTHER: 'OTHER',
    SailTicket.Color.SPARE: 'SPARE',
}


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
            p550_reserves = form.cleaned_data['p550_reserves']
            sail_reserves = form.cleaned_data['sail_reserves']
            other_reserves = form.cleaned_data['other_reserves']
            spare_count = form.cleaned_data['spare_count']

            # Boats that don't yet have any ticket assigned
            assigned_boat_ids = set(
                SailTicket.objects.filter(boat__isnull=False).values_list('boat_id', flat=True)
            )
            boats = Boat.objects.select_related('boat_class').exclude(pk__in=assigned_boat_ids)

            # Group boats by color
            boat_groups = {
                SailTicket.Color.P550: [],
                SailTicket.Color.SAIL: [],
                SailTicket.Color.OTHER: [],
            }
            for boat in boats:
                color = _boat_color(boat)
                boat_groups[color].append(boat)

            reserve_counts = {
                SailTicket.Color.P550: p550_reserves,
                SailTicket.Color.SAIL: sail_reserves,
                SailTicket.Color.OTHER: other_reserves,
            }

            with transaction.atomic():
                to_create = []
                for color, color_boats in boat_groups.items():
                    total = len(color_boats) + reserve_counts[color]
                    if total == 0:
                        continue
                    codes = _generate_codes(COLOR_PREFIX[color], total)
                    for i, boat in enumerate(color_boats):
                        to_create.append(SailTicket(code=codes[i], color=color, boat=boat))
                    for i in range(len(color_boats), total):
                        to_create.append(SailTicket(code=codes[i], color=color))
                if spare_count > 0:
                    spare_codes = _generate_codes(COLOR_PREFIX[SailTicket.Color.SPARE], spare_count)
                    for code in spare_codes:
                        to_create.append(SailTicket(code=code, color=SailTicket.Color.SPARE))
                SailTicket.objects.bulk_create(to_create)
                created = len(to_create)

            messages.success(request, _('%(n)d tickets created.') % {'n': created})
            return redirect('SkaRe:ticket_list')
    else:
        form = BulkTicketCreateForm()

    unassigned_boats = Boat.objects.select_related('boat_class').exclude(
        pk__in=SailTicket.objects.filter(boat__isnull=False).values_list('boat_id', flat=True)
    )
    boat_preview = {}
    for boat in unassigned_boats:
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
        'Code', 'Color', 'Boat class', 'Sail number', 'Boat name',
        'Contact person', 'Contact phone', 'RFID UID', 'Status',
    ])
    for ticket in tickets:
        boat = ticket.boat
        writer.writerow([
            ticket.code,
            ticket.color,
            boat.boat_class.name if boat and boat.boat_class else '',
            boat.sail_number if boat else '',
            boat.name if boat else '',
            boat.contact_person if boat else '',
            boat.contact_phone if boat else '',
            ticket.rfid_uid,
            ticket.status,
        ])
    return response
