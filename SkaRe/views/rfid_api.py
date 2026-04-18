import json
from functools import wraps

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt

from ..models import SailTicket, SailTicketLog


def require_api_key(view_func):
    """Decorator: validates Authorization: Bearer <RFID_API_KEY> header."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        expected = getattr(settings, 'RFID_API_KEY', '')
        auth = request.headers.get('Authorization', '')
        if not expected or auth != f'Bearer {expected}':
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


@csrf_exempt
@require_api_key
def rfid_alive(request):
    tickets_with_boat = SailTicket.objects.filter(boat__isnull=False)
    boats_on_water = tickets_with_boat.filter(
        status=SailTicket.Status.ON_WATER
    ).count()
    boats_ashore = tickets_with_boat.filter(
        status=SailTicket.Status.ASHORE
    ).count()

    pending = SailTicket.objects.filter(pending_pairing=True).first()

    data = {
        'mode': 'pairing' if pending else 'scanning',
        'boats_on_water': boats_on_water,
        'boats_ashore': boats_ashore,
        'timestamp': now().isoformat(),
    }
    if pending:
        data['pairing_ticket'] = pending.code
    return JsonResponse(data)


_MODULE_TRANSITIONS = {
    'departure': SailTicket.Status.ON_WATER,
    'arrival': SailTicket.Status.ASHORE,
}


def _boat_data(boat):
    """Build the boat sub-dict for API responses. Omits blank/null fields."""
    if boat is None:
        return None
    data = {
        'name': boat.name,
        'contact_person': boat.contact_person,
        'contact_phone': boat.contact_phone,
    }
    if boat.sail_number:
        data['sail_number'] = boat.sail_number
    if boat.boat_class:
        data['class'] = boat.boat_class.name
    if boat.harbor_number:
        data['harbor_number'] = boat.harbor_number
    if boat.harbor_name:
        data['harbor_name'] = boat.harbor_name
    return data


@csrf_exempt
@require_api_key
def rfid_scan(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    module_id = body.get('module_id', '')
    rfid_uid = body.get('rfid_uid', '')

    if not rfid_uid:
        return JsonResponse({'error': 'Missing rfid_uid'}, status=400)
    if module_id not in _MODULE_TRANSITIONS:
        return JsonResponse({'error': 'Invalid module_id'}, status=400)

    timestamp = now().isoformat()

    # ── Pairing mode ──────────────────────────────────────────────────────
    pending = SailTicket.objects.filter(pending_pairing=True).first()
    if pending:
        if SailTicket.objects.filter(rfid_uid=rfid_uid).exists():
            return JsonResponse({
                'result': 'error',
                'error': 'already_paired',
                'timestamp': timestamp,
            })
        with transaction.atomic():
            pending.rfid_uid = rfid_uid
            pending.pending_pairing = False
            pending.save(update_fields=['rfid_uid', 'pending_pairing', 'updated_at'])
        return JsonResponse({
            'result': 'ok',
            'ticket_code': pending.code,
            'timestamp': timestamp,
        })

    # ── Scanning mode — implemented in Task 4 ────────────────────────────
    return JsonResponse({'error': 'Not implemented'}, status=500)
