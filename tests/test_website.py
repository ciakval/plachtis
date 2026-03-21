"""
Integration tests for the PlachtIS website at https://plachtis-test.remesh.cz.

Tests several parallel connections, logs in with credentials created by the
'seed_large' management command, and verifies the website responds as expected.

Usage:
    python -m pytest tests/test_website.py -v
    python tests/test_website.py
"""
import concurrent.futures
import unittest

import requests

BASE_URL = "https://plachtis-test.remesh.cz"

# Credentials created by 'python manage.py seed_large'
TEST_USERNAME = "testuser_large"
TEST_PASSWORD = "testpass123"

# Number of parallel workers for concurrent connection tests
NUM_PARALLEL_WORKERS = 5

# Pages accessible without authentication
ANONYMOUS_PAGES = [
    "/",
    "/user/login/",
    "/user/register/",
    "/user/forgot_password/",
]

# Pages that require a logged-in user
AUTHENTICATED_PAGES = [
    "/",
    "/unit/list/",
    "/individual/list/",
    "/organizer/list/",
    "/all/list/",
    "/merchandise/list/",
    "/unit/register/",
    "/individual/register/",
    "/organizer/register/",
]


def create_authenticated_session() -> requests.Session:
    """Return a Session that is authenticated with seed_large credentials."""
    session = requests.Session()

    login_url = f"{BASE_URL}/user/login/"
    response = session.get(login_url, timeout=15)
    response.raise_for_status()

    csrf_token = session.cookies.get("csrftoken")
    if not csrf_token:
        raise ValueError(
            f"No csrftoken cookie returned by {login_url}. "
            "Check that the server is reachable and CSRF middleware is enabled."
        )

    response = session.post(
        login_url,
        data={
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
            "csrfmiddlewaretoken": csrf_token,
        },
        headers={"Referer": login_url},
        timeout=15,
    )
    response.raise_for_status()

    return session


def fetch_page(session: requests.Session, path: str) -> dict:
    """Fetch *path* and return a result dict."""
    url = f"{BASE_URL}{path}"
    response = session.get(url, timeout=15)
    return {
        "path": path,
        "url": response.url,
        "status_code": response.status_code,
        "ok": response.status_code == 200,
        "content_length": len(response.content),
    }


class TestAnonymousAccess(unittest.TestCase):
    """Public pages should be reachable without authentication."""

    def test_homepage_returns_200(self):
        response = requests.get(f"{BASE_URL}/", timeout=15)
        self.assertEqual(response.status_code, 200)

    def test_login_page_returns_200(self):
        response = requests.get(f"{BASE_URL}/user/login/", timeout=15)
        self.assertEqual(response.status_code, 200)

    def test_register_page_returns_200(self):
        response = requests.get(f"{BASE_URL}/user/register/", timeout=15)
        self.assertEqual(response.status_code, 200)

    def test_forgot_password_page_returns_200(self):
        response = requests.get(f"{BASE_URL}/user/forgot_password/", timeout=15)
        self.assertEqual(response.status_code, 200)

    def test_anonymous_pages_parallel(self):
        """All public pages should load successfully under parallel load."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_PARALLEL_WORKERS) as executor:
            # Each submission gets its own Session to avoid thread-safety issues.
            futures = {
                executor.submit(fetch_page, requests.Session(), path): path
                for path in ANONYMOUS_PAGES
            }
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                self.assertTrue(
                    result["ok"],
                    f"Page {result['path']} returned HTTP {result['status_code']}",
                )


class TestAuthentication(unittest.TestCase):
    """Login with seed_large credentials and verify protected pages are reachable."""

    @classmethod
    def setUpClass(cls):
        cls.session = create_authenticated_session()

    def test_home_after_login_returns_200(self):
        result = fetch_page(self.session, "/")
        self.assertTrue(result["ok"], f"Homepage returned HTTP {result['status_code']}")

    def test_home_after_login_not_redirected_to_login_page(self):
        """After login the home page must not redirect back to /user/login/."""
        result = fetch_page(self.session, "/")
        self.assertNotIn(
            "/user/login/",
            result["url"],
            "Authenticated request was redirected to login page",
        )

    def test_unit_list_returns_200(self):
        result = fetch_page(self.session, "/unit/list/")
        self.assertTrue(result["ok"], f"/unit/list/ returned HTTP {result['status_code']}")

    def test_individual_list_returns_200(self):
        result = fetch_page(self.session, "/individual/list/")
        self.assertTrue(result["ok"], f"/individual/list/ returned HTTP {result['status_code']}")

    def test_organizer_list_returns_200(self):
        result = fetch_page(self.session, "/organizer/list/")
        self.assertTrue(result["ok"], f"/organizer/list/ returned HTTP {result['status_code']}")

    def test_all_list_returns_200(self):
        result = fetch_page(self.session, "/all/list/")
        self.assertTrue(result["ok"], f"/all/list/ returned HTTP {result['status_code']}")

    def test_merchandise_list_returns_200(self):
        result = fetch_page(self.session, "/merchandise/list/")
        self.assertTrue(result["ok"], f"/merchandise/list/ returned HTTP {result['status_code']}")


class TestParallelConnections(unittest.TestCase):
    """Website must respond correctly under several simultaneous authenticated connections."""

    @classmethod
    def setUpClass(cls):
        """Create one authenticated session per parallel worker."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_PARALLEL_WORKERS) as executor:
            futures = [executor.submit(create_authenticated_session) for _ in range(NUM_PARALLEL_WORKERS)]
            cls.sessions = [f.result() for f in concurrent.futures.as_completed(futures)]

    def test_parallel_homepage_requests(self):
        """All parallel sessions must reach the homepage successfully."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_PARALLEL_WORKERS) as executor:
            futures = [
                executor.submit(fetch_page, session, "/")
                for session in self.sessions
            ]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                self.assertTrue(
                    result["ok"],
                    f"Homepage returned HTTP {result['status_code']} under parallel load",
                )

    def test_parallel_authenticated_pages(self):
        """All authenticated pages must respond correctly across parallel connections."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_PARALLEL_WORKERS) as executor:
            futures = [
                executor.submit(fetch_page, session, path)
                for session in self.sessions
                for path in AUTHENTICATED_PAGES
            ]
            failed = []
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if not result["ok"]:
                    failed.append(result)

        self.assertEqual(
            len(failed),
            0,
            f"Pages that failed under parallel load: {failed}",
        )

    def test_parallel_list_pages(self):
        """List pages (with large datasets from seed_large) must respond within timeout."""
        list_pages = ["/unit/list/", "/individual/list/", "/organizer/list/", "/all/list/"]
        with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_PARALLEL_WORKERS) as executor:
            futures = [
                executor.submit(fetch_page, session, path)
                for session in self.sessions
                for path in list_pages
            ]
            failed = []
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if not result["ok"]:
                    failed.append(result)

        self.assertEqual(
            len(failed),
            0,
            f"List pages that failed under parallel load: {failed}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
