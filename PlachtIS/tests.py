from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from PlachtIS.middleware import StaticFilesExpiresMiddleware


class StaticFilesExpiresMiddlewareTests(TestCase):
    """Tests for StaticFilesExpiresMiddleware."""

    def setUp(self):
        self.factory = RequestFactory()

    def _make_middleware(self, response):
        """Return a middleware instance whose get_response returns *response*."""
        return StaticFilesExpiresMiddleware(get_response=lambda r: response)

    # ------------------------------------------------------------------
    # Helper: assert that the Expires value looks like an HTTP date string
    # ------------------------------------------------------------------
    def _assert_valid_http_date(self, value):
        from email.utils import parsedate
        self.assertIsNotNone(
            parsedate(value),
            f"Expected a valid HTTP date string, got: {value!r}",
        )

    # ------------------------------------------------------------------
    # Core behaviour
    # ------------------------------------------------------------------

    def test_adds_expires_when_cache_control_max_age_present(self):
        """Expires header is added when Cache-Control contains max-age."""
        response = HttpResponse()
        response["Cache-Control"] = "max-age=3600, public"

        middleware = self._make_middleware(response)
        result = middleware(self.factory.get("/static/some.css"))

        self.assertIn("Expires", result)
        self._assert_valid_http_date(result["Expires"])

    def test_adds_expires_for_immutable_static_files(self):
        """Expires header is derived from the long max-age WhiteNoise sets on
        immutable (content-hashed) static files."""
        one_year = 315360000
        response = HttpResponse()
        response["Cache-Control"] = f"max-age={one_year}, public, immutable"

        middleware = self._make_middleware(response)
        result = middleware(self.factory.get("/static/app.abc123.css"))

        self.assertIn("Expires", result)
        self._assert_valid_http_date(result["Expires"])

    def test_does_not_overwrite_existing_expires(self):
        """If the response already carries an Expires header, it is left alone."""
        original = "Thu, 01 Jan 2099 00:00:00 GMT"
        response = HttpResponse()
        response["Cache-Control"] = "max-age=60, public"
        response["Expires"] = original

        middleware = self._make_middleware(response)
        result = middleware(self.factory.get("/static/some.js"))

        self.assertEqual(result["Expires"], original)

    def test_no_expires_when_no_cache_control(self):
        """Responses without Cache-Control are not modified."""
        response = HttpResponse()

        middleware = self._make_middleware(response)
        result = middleware(self.factory.get("/"))

        self.assertNotIn("Expires", result)

    def test_no_expires_when_cache_control_lacks_max_age(self):
        """Cache-Control without max-age does not trigger Expires."""
        response = HttpResponse()
        response["Cache-Control"] = "no-cache, no-store"

        middleware = self._make_middleware(response)
        result = middleware(self.factory.get("/"))

        self.assertNotIn("Expires", result)

    def test_does_not_match_s_maxage(self):
        """s-maxage is a proxy-cache directive; it must not trigger Expires."""
        response = HttpResponse()
        response["Cache-Control"] = "s-maxage=3600, public"

        middleware = self._make_middleware(response)
        result = middleware(self.factory.get("/some/page/"))

        self.assertNotIn("Expires", result)

    def test_handles_spaces_around_equals(self):
        """max-age = 300 (with spaces) is valid HTTP and should be parsed."""
        response = HttpResponse()
        response["Cache-Control"] = "max-age = 300, public"

        middleware = self._make_middleware(response)
        result = middleware(self.factory.get("/static/asset.css"))

        self.assertIn("Expires", result)
        self._assert_valid_http_date(result["Expires"])

