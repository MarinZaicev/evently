from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from ..export import write_json_atomic
from ..http_client import HttpClient
from ..models import Event

if TYPE_CHECKING:
    from ..config import Settings


class SourceConfigError(RuntimeError):
    """Источник нельзя опросить из-за настроек (нет токена, нет такого города). Трейсбек не нужен."""


class SourceAdapter(ABC):
    """Адаптер знает ровно одно: как превратить ответ своего источника в Event."""

    name: ClassVar[str]

    def __init__(self, http: HttpClient, *, raw_dir: Path | None = None, settings: "Settings | None" = None) -> None:
        self.http = http
        self.raw_dir = raw_dir
        self.settings = settings  # для токенов и прочих настроек конкретного источника

    @abstractmethod
    def fetch_events(self, city: str, *, days: int = 30, limit: int | None = None) -> AsyncIterator[Event]:
        """Асинхронно отдаёт события города на ближайшие `days` дней."""

    async def list_cities(self) -> list[tuple[str, str]]:
        """Пары (slug, название) городов, которые поддерживает источник."""
        raise NotImplementedError(f"{self.name} не умеет отдавать список городов")

    def save_raw(self, name: str, data: Any) -> None:
        """Сохраняем сырой ответ: можно перепарсить без повторного скачивания."""
        if self.raw_dir is not None:
            write_json_atomic(self.raw_dir / f"{name}.json", data)
