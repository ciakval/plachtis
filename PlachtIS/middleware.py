import re
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

_MAX_AGE_RE = re.compile(r"(?:^|,)\s*max-age\s*=\s*(\d+)", re.IGNORECASE)


class StaticFilesExpiresMiddleware:
    """
    Add an ``Expires`` header to responses that carry a ``Cache-Control:
    max-age=`` directive but no ``Expires`` header.

    Browsers (notably Firefox) may show NS_BINDING_ABORTED or fail to load
    static resources (such as favicons) when the ``Expires`` header is absent,
    because HTTP/1.0 caches and some browser code-paths still rely on it.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if "Expires" not in response and "Cache-Control" in response:
            match = _MAX_AGE_RE.search(response["Cache-Control"])
            if match:
                try:
                    max_age = int(match.group(1))
                    expires = datetime.now(tz=timezone.utc) + timedelta(
                        seconds=max_age
                    )
                    response["Expires"] = format_datetime(expires, usegmt=True)
                except ValueError:
                    pass

        return response
