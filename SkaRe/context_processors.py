from django.conf import settings
from .permissions import is_infodesk


def version_info(request):
    return {
        'VERSION': settings.VERSION,
        'BUILD_ID': settings.BUILD_ID,
        'user_is_infodesk': is_infodesk(request.user) if request.user.is_authenticated else False,
    }
