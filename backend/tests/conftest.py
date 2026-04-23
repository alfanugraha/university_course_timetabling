"""
backend/tests/conftest.py
Shared pytest fixtures and import-time patches.
"""

import sys
from unittest.mock import MagicMock, patch

# Patch psycopg2 before any app module is imported so tests can run
# without a real PostgreSQL driver installed.
sys.modules.setdefault("psycopg2", MagicMock())
sys.modules.setdefault("psycopg2.extensions", MagicMock())

# Patch SQLAlchemy engine creation so database.py doesn't try to connect
_mock_engine = MagicMock()
_mock_session_cls = MagicMock()

with patch("sqlalchemy.create_engine", return_value=_mock_engine):
    with patch("sqlalchemy.orm.sessionmaker", return_value=_mock_session_cls):
        import app.database  # noqa: F401 — ensure module is loaded with patches
