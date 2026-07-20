from pathlib import Path

import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def use_repository_schema(monkeypatch, tmp_path):
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "hermes-skill"
        / "schemas"
        / "commitment.schema.json"
    )
    monkeypatch.setenv("COMMITMENT_SCHEMA_PATH", str(schema_path))
    monkeypatch.setenv("COMMITMENTS_DB_PATH", str(tmp_path / "test_commitments.db"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
