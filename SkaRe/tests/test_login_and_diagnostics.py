import io
import logging
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from django.contrib.auth.models import User
from django.db import OperationalError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse


class LoginNextRedirectTest(TestCase):
    """The ?next= parameter on login must never cause an error or an open redirect."""

    def setUp(self):
        User.objects.create_user(username='sailor', password='pw')
        self.login_url = reverse('SkaRe:login')
        self.home_url = reverse('SkaRe:home')

    def _login(self, next_value):
        return self.client.post(
            self.login_url,
            {'username': 'sailor', 'password': 'pw'},
            query_params={'next': next_value},
        )

    def test_local_path_is_followed(self):
        response = self._login('/boats/')
        self.assertRedirects(response, '/boats/', fetch_redirect_response=False)

    def test_bare_word_falls_back_to_home(self):
        # Used to raise NoReverseMatch, which the user saw as a 500.
        response = self._login('foo')
        self.assertRedirects(response, self.home_url, fetch_redirect_response=False)

    def test_external_url_falls_back_to_home(self):
        response = self._login('https://evil.example/')
        self.assertRedirects(response, self.home_url, fetch_redirect_response=False)

    def test_protocol_relative_url_falls_back_to_home(self):
        response = self._login('//evil.example/')
        self.assertRedirects(response, self.home_url, fetch_redirect_response=False)


class ServerErrorLoggingTest(TestCase):
    """Unhandled exceptions must reach the console even though DEBUG is False."""

    def test_traceback_reaches_console_handler(self):
        handlers = [
            handler for handler in logging.getLogger('django').handlers
            if isinstance(handler, logging.StreamHandler)
        ]
        self.assertTrue(handlers, 'django logger has no console handler')
        handler = handlers[0]
        captured = io.StringIO()
        original_stream = handler.setStream(captured)
        self.client.raise_request_exception = False
        try:
            with mock.patch(
                'SkaRe.views.registration.authenticate',
                side_effect=OperationalError('attempt to write a readonly database'),
            ):
                response = self.client.post(
                    reverse('SkaRe:login'), {'username': 'a', 'password': 'b'},
                )
        finally:
            handler.setStream(original_stream)

        self.assertEqual(response.status_code, 500)
        self.assertIn('Traceback', captured.getvalue())
        self.assertIn('attempt to write a readonly database', captured.getvalue())

    def test_not_found_does_not_reach_console_handler(self):
        # Scanners cause thousands of 404s; the access log already records them.
        handler = next(
            handler for handler in logging.getLogger('django').handlers
            if isinstance(handler, logging.StreamHandler)
        )
        captured = io.StringIO()
        original_stream = handler.setStream(captured)
        try:
            response = self.client.get('/.env')
        finally:
            handler.setStream(original_stream)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(captured.getvalue(), '')


@unittest.skipIf(os.geteuid() == 0, 'root ignores directory permissions')
class SqliteWritableCheckTest(SimpleTestCase):
    """SQLite needs a writable file AND a writable directory (for its journal)."""

    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.directory = Path(temp_dir.name)
        self.addCleanup(self.directory.chmod, stat.S_IRWXU)
        self.db_path = self.directory / 'db.sqlite3'

    def _errors(self):
        from SkaRe.checks import sqlite_path_errors
        return sqlite_path_errors(self.db_path, 'default')

    def test_writable_directory_and_file_pass(self):
        self.db_path.touch()
        self.assertEqual(self._errors(), [])

    def test_missing_file_in_writable_directory_passes(self):
        # Fresh install: migrate is about to create the database.
        self.assertEqual(self._errors(), [])

    def test_read_only_directory_fails(self):
        # The production incident: the file was writable but the directory was not.
        self.db_path.touch()
        self.directory.chmod(stat.S_IRUSR | stat.S_IXUSR)
        self.assertEqual([error.id for error in self._errors()], ['SkaRe.E001'])

    def test_read_only_file_fails(self):
        self.db_path.touch()
        self.db_path.chmod(stat.S_IRUSR)
        self.assertEqual([error.id for error in self._errors()], ['SkaRe.E002'])
