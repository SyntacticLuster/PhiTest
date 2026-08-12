import os
import tempfile
import pytest
from pathlib import Path
from phitest.adapters.sqlite_repository import SQLiteRepository

MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"


@pytest.fixture
def tmp_repo(tmp_path):
    db = str(tmp_path / "test.db")
    return SQLiteRepository(db, MIGRATIONS_DIR)
