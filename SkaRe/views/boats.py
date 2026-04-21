import csv
import io
import urllib.request

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.cache import cache
from django.conf import settings
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.db import transaction
from ..models import Entity, Unit, BoatClass, Boat
from ..forms import BoatForm
from ..permissions import is_infodesk

_SAIL_REGISTRY_CACHE_KEY = "sail_registry_rows"


def _fetch_sheet_csv(url):
    """Fetch the published Google Sheets CSV and return raw text.

    Decodes as UTF-8-sig to strip any BOM. Raises on network errors.
    """
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as response:
        return response.read().decode('utf-8-sig')


def _get_registry_rows():
    """Return parsed registry rows from cache, fetching if needed."""
    import SkaRe.views as _views_module
    rows = cache.get(_SAIL_REGISTRY_CACHE_KEY)
    if rows is None:
        raw = _views_module._fetch_sheet_csv(settings.SAIL_REGISTRY_SHEET_URL)
        lines = io.StringIO(raw).readlines()
        # Row 1 is the sheet title, row 2 is metadata — actual headers are on row 3
        reader = csv.DictReader(lines[2:])
        rows = [row for row in reader if any(v.strip() for v in row.values())]
        cache.set(_SAIL_REGISTRY_CACHE_KEY, rows, settings.SAIL_REGISTRY_CACHE_TTL)
    return rows


@login_required
def boat_sail_lookup(request):
    """AJAX: look up a sail number in the Google Sheets registry."""
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'error': 'missing q'}, status=400)

    try:
        rows = _get_registry_rows()
    except Exception:
        return JsonResponse({'error': 'registry unavailable'}, status=503)

    match = None
    q_lower = q.lower()
    for row in rows:
        sail_num = row.get('plach. číslo', '').strip()
        if sail_num.lower() == q_lower:
            match = row
            break
        # Numeric normalisation: "14" matches "014", etc.
        try:
            if int(sail_num) == int(q):
                match = row
                break
        except (ValueError, TypeError):
            pass

    if match is None:
        return JsonResponse({'error': 'not found'}, status=404)

    # Parse compound 'typ' field: "šalupa - P550 - Černá Eskadra"
    typ = match.get('typ', '').strip()
    typ_parts = [p.strip() for p in typ.split(' - ')] if typ else []
    subtype = typ_parts[0] if len(typ_parts) > 0 else ''
    class_name = typ_parts[1] if len(typ_parts) > 1 else ''

    # Sail area: Czech decimal comma → dot
    # Column header starts with 'plocha' (full name may include ', datum měření' suffix)
    sail_area_raw = ''
    for key, val in match.items():
        if key.lower().startswith('plocha'):
            sail_area_raw = val.strip()
            break
    sail_area = sail_area_raw.replace(',', '.') if sail_area_raw else ''

    return JsonResponse({
        'sail_number': match.get('plach. číslo', '').strip(),
        'boat_name': match.get('Jméno', '').strip(),
        'class_name': class_name,
        'subtype': subtype,
        'sail_area': sail_area,
        'harbor_number': match.get('ev. č.', '').strip(),
        'harbor_name': match.get('přístav', '').strip(),
        'contact_person': match.get('oddíl', '').strip(),
    })


@login_required
def boat_my_unit(request):
    """AJAX: return the most recently created Unit for the current user."""
    unit = (
        Unit.objects
        .filter(entity__created_by=request.user)
        .select_related('entity')
        .order_by('-entity__created_at')
        .first()
    )
    if not unit:
        return JsonResponse({}, status=404)
    return JsonResponse({
        'harbor_number': unit.entity.scout_unit_evidence_id,
        'harbor_name': unit.entity.scout_unit_name,
        'contact_person': unit.contact_person_name,
        'contact_phone': unit.entity.contact_phone,
    })


@login_required
def boat_list(request):
    boats = Boat.objects.select_related('boat_class', 'created_by').order_by('name')
    return render(request, 'SkaRe/boats/list.html', {'boats': boats})


@login_required
def boat_detail(request, boat_id):
    boat = get_object_or_404(Boat.objects.select_related('boat_class', 'created_by'), id=boat_id)
    return render(request, 'SkaRe/boats/detail.html', {
        'boat': boat,
        'is_creator': boat.created_by == request.user,
        'can_edit': boat.can_be_edited(request.user),
        'can_delete': boat.created_by == request.user or is_infodesk(request.user),
    })


@login_required
def boat_register(request):
    has_unit = Unit.objects.filter(entity__created_by=request.user).exists()
    if request.method == 'POST':
        form = BoatForm(request.POST)
        if form.is_valid():
            boat = form.save(commit=False)
            boat.created_by = request.user
            boat.save()
            messages.success(request, _('Boat registered successfully.'))
            return redirect('SkaRe:boat_detail', boat_id=boat.pk)
    else:
        form = BoatForm()
    return render(request, 'SkaRe/boats/form.html', {
        'form': form,
        'has_unit': has_unit,
        'action': 'register',
    })


@login_required
def boat_edit(request, boat_id):
    boat = get_object_or_404(Boat.objects.select_related('boat_class', 'created_by'), id=boat_id)
    if not boat.can_be_edited(request.user):
        messages.error(request, _('You do not have permission to edit this boat.'))
        return redirect('SkaRe:boat_detail', boat_id=boat_id)
    has_unit = Unit.objects.filter(entity__created_by=request.user).exists()
    if request.method == 'POST':
        form = BoatForm(request.POST, instance=boat)
        if form.is_valid():
            form.save()
            messages.success(request, _('Boat updated successfully.'))
            return redirect('SkaRe:boat_detail', boat_id=boat.pk)
    else:
        form = BoatForm(instance=boat)
    return render(request, 'SkaRe/boats/form.html', {
        'form': form,
        'boat': boat,
        'has_unit': has_unit,
        'action': 'edit',
    })


@login_required
def boat_delete(request, boat_id):
    boat = get_object_or_404(Boat, id=boat_id)
    if boat.created_by != request.user and not is_infodesk(request.user):
        messages.error(request, _('You do not have permission to delete this boat.'))
        return redirect('SkaRe:boat_detail', boat_id=boat_id)
    if request.method == 'POST':
        boat.delete()
        messages.success(request, _('Boat deleted successfully.'))
        return redirect('SkaRe:boat_list')
    return render(request, 'SkaRe/boats/confirm_delete.html', {'boat': boat})


@login_required
def boat_lend(request, boat_id):
    """Manage which users can see and use this boat in crew registration."""
    boat = get_object_or_404(Boat, id=boat_id)

    if not boat.can_be_edited(request.user):
        messages.error(request, _('You do not have permission to manage lending for this boat.'))
        return redirect('SkaRe:boat_detail', boat_id=boat_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            username = request.POST.get('username', '').strip()
            try:
                user_to_add = User.objects.get(username=username)
                if user_to_add == request.user:
                    messages.warning(request, _('You cannot lend to yourself.'))
                elif boat.visible_to.filter(id=user_to_add.id).exists():
                    messages.warning(request, _('User "{username}" already has access.').format(username=username))
                else:
                    boat.visible_to.add(user_to_add)
                    messages.success(request, _('User "{username}" can now see this boat.').format(username=username))
            except User.DoesNotExist:
                messages.error(request, _('User "{username}" not found.').format(username=username))
        elif action == 'remove':
            user_id = request.POST.get('user_id')
            try:
                user_to_remove = User.objects.get(id=user_id)
                boat.visible_to.remove(user_to_remove)
                messages.success(request, _('Access removed for user "{username}".').format(username=user_to_remove.username))
            except (User.DoesNotExist, ValueError):
                pass
        return redirect('SkaRe:boat_lend', boat_id=boat_id)

    return render(request, 'SkaRe/boats/lend.html', {
        'boat': boat,
        'lent_to': boat.visible_to.all(),
    })
