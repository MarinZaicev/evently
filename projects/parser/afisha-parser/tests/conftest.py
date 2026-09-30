import json
import os
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path):
    """Тесты не должны видеть настоящий .env и переменные AFISHA_* сервера:
    иначе, например, AFISHA_CITIES из рабочего .env подменяет города в тестах."""
    for key in list(os.environ):
        if key.startswith("AFISHA_"):
            monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)  # Settings ищет .env в текущей папке — здесь его нет


@pytest.fixture
def kudago_page() -> dict:
    return json.loads((FIXTURES / "kudago_events_page.json").read_text(encoding="utf-8"))
