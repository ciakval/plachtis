from django.conf import settings


def version_info(request):
    return {
        'VERSION': settings.VERSION,
        'BUILD_ID': settings.BUILD_ID,
    }
