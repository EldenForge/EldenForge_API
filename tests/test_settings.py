from core.settings import Settings


def test_settings_loads_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h:5432/d")
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+asyncpg://u:p@h:5432/d_test")
    s = Settings()
    assert s.database_url == "postgresql+asyncpg://u:p@h:5432/d"
    assert s.test_database_url == "postgresql+asyncpg://u:p@h:5432/d_test"


def test_settings_test_database_url_optional(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h:5432/d")
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    s = Settings(_env_file=None)  # do NOT read .env so the default applies
    assert s.test_database_url is None
