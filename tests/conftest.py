import pytest

import config


@pytest.fixture(autouse=True)
def temporary_cache(tmp_path, monkeypatch):
    # every test gets its own empty cache, so the real data/cache.sqlite3 is never touched
    monkeypatch.setattr(config, "CACHE_PATH", str(tmp_path / "cache.sqlite3"))
