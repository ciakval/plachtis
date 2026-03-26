from functools import wraps
from django.http import HttpResponseForbidden


def is_infodesk(user) -> bool:
    """Return True if the user is a member of the InfoDesk group."""
    return user.groups.filter(name='InfoDesk').exists()


def is_race_management(user) -> bool:
    """Return True if the user is a member of the RaceManagement group."""
    return user.groups.filter(name='RaceManagement').exists()


def infodesk_required(view_func):
    """Decorator: requires login AND InfoDesk group membership. Returns 403 for non-InfoDesk users."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.conf import settings as django_settings
            from django.shortcuts import redirect
            from django.urls import reverse
            try:
                login_url = reverse(django_settings.LOGIN_URL)
            except Exception:
                login_url = django_settings.LOGIN_URL
            return redirect(f'{login_url}?next={request.path}')
        if not is_infodesk(request.user):
            return HttpResponseForbidden()
        return view_func(request, *args, **kwargs)
    return wrapper
