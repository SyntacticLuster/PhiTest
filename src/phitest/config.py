import os
from pathlib import Path

DB_PATH: str = os.environ.get("PHITEST_DB_PATH", "phitest.db")
MAX_OBSERVATION_LENGTH: int = int(os.environ.get("PHITEST_MAX_OBSERVATION_LENGTH", "65536"))
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
MIGRATIONS_DIR: Path = PROJECT_ROOT / "migrations"
TEMPLATES_DIR: Path = PROJECT_ROOT / "templates"
STATIC_DIR: Path = PROJECT_ROOT / "static"
