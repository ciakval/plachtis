import json
from functools import wraps

from django.conf import settings
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
