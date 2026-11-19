import pytest

import config


@pytest.fixture(autouse=True)
def temporary_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_PATH", str(tmp_path / "cache.sqlite3"))
