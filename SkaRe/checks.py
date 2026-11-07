import os
import tempfile
from pathlib import Path

from django.core.checks import Error, Tags, register
from django.db import connections


def sqlite_path_errors(db_path, alias):
    """Return check errors if SQLite could not write to the database at db_path.

    SQLite creates its journal next to the database, so the directory has to be writable
    as well as the file. Otherwise reads work and every write fails.
    """
    db_path = Path(db_path)
    errors = []
    try:
        with tempfile.TemporaryFile(dir=db_path.parent):
            pass
    except OSError as exc:
        errors.append(Error(
            f"Database directory {db_path.parent} of '{alias}' is not writable: {exc}",
            hint=f'Give the application user (uid {os.getuid()}) ownership of the directory.',
            id='SkaRe.E001',
        ))
    if db_path.exists() and not os.access(db_path, os.W_OK):
        errors.append(Error(
            f"Database file {db_path} of '{alias}' is not writable.",
            hint=f'Give the application user (uid {os.getuid()}) ownership of the file.',
            id='SkaRe.E002',
        ))
    return errors


@register(Tags.database)
def check_sqlite_writable(app_configs, databases=None, **kwargs):
    """Fail `migrate`, and so container start, when the database cannot be written."""
    errors = []
    for alias in databases or []:
        connection = connections[alias]
        if connection.vendor == 'sqlite' and not connection.is_in_memory_db():
            errors.extend(sqlite_path_errors(connection.settings_dict['NAME'], alias))
    return errors
