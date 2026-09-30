from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Все настройки читаются из переменных AFISHA_* или из файла .env в текущей папке."""

    model_config = SettingsConfigDict(env_prefix="AFISHA_", env_file=".env", extra="ignore")

    output_dir: Path = Path("output")
    user_agent: str = "afisha-parser/0.2"
    request_timeout: float = 20.0
    request_delay: float = 0.5
    max_retries: int = 4
    image_concurrency: int = 4

    # --- Фильтр прошедших событий ---
    # Сеанс без времени окончания считается прошедшим через столько минут после начала.
    # 0 — как только начался (купить билет уже нельзя).
    past_grace_minutes: int = 0

    # --- Автономный режим (команды run и daemon) ---
    # Какие города собирать: наши slug'и через запятую (список: python -m afisha_parser cities).
    # Для каждого города берутся все источники из AFISHA_SOURCES, которые его знают.
    cities: str = ""
    sources: str = "kudago,timepad"
    # Точный список пар источник:город, например "kudago:msk,timepad:omsk".
    # Используется, только если AFISHA_CITIES пустой
    targets: str = "kudago:msk"
    days: int = 30
    interval_minutes: int = 180
    # Если цикл целиком упал (нет сети), следующая попытка раньше обычного
    retry_minutes: int = 20
    download_images: bool = True
    save_raw: bool = True
    evently: bool = True
    movies: bool = True          # трейлеры к кинопоказам источника (нужен ключ TMDb)
    now_playing: bool = True     # афиша проката TMDb с трейлерами (нужен ключ TMDb)
    # Сколько хранить снимки прошлых запусков (latest.json не удаляется никогда)
    keep_days: int = 7
    raw_keep_days: int = 2

    # --- Отправка в бэкенд Evently (пусто — не отправлять, только файлы) ---
    evently_import_url: str | None = None
    evently_import_token: str | None = None
    evently_import_chunk: int = 200

    # --- Timepad: токен на dev.timepad.ru/api/oauth/ ---
    timepad_token: str | None = None

    # --- TMDb ---
    # v3 «Ключ API» с themoviedb.org — нужен только для кино и трейлеров
    tmdb_api_key: str | None = None
    tmdb_region: str = "RU"
    tmdb_language: str = "ru-RU"

    # --- Скачивание файлов трейлеров (нужен пакет yt-dlp: pip install ".[trailers]") ---
    trailers_download: bool = False
    trailers_per_run: int = 20
    trailer_max_height: int = 720
    trailer_max_mb: int = 150

    def target_pairs(self) -> list[tuple[str, str]]:
        if self.cities.strip():
            return self._pairs_from_cities()
        pairs = []
        for chunk in self.targets.replace(";", ",").split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            source, sep, city = chunk.partition(":")
            if not sep or not source.strip() or not city.strip():
                raise ValueError(f"AFISHA_TARGETS: ожидается источник:город, получено {chunk!r}")
            pairs.append((source.strip(), city.strip()))
        return pairs

    def _pairs_from_cities(self) -> list[tuple[str, str]]:
        from .cities import CITIES

        wanted_sources = [s.strip() for s in self.sources.split(",") if s.strip()]
        pairs = []
        unknown = []
        for slug in (c.strip() for c in self.cities.replace(";", ",").split(",")):
            if not slug:
                continue
            city = CITIES.get(slug)
            if city is None:
                unknown.append(slug)
                continue
            available = city.sources()
            pairs += [(source, slug) for source in wanted_sources if source in available]
        if unknown:
            raise ValueError(f"AFISHA_CITIES: неизвестные города {', '.join(unknown)}. "
                             f"Список: python -m afisha_parser cities")
        return pairs


@lru_cache
def get_settings() -> Settings:
    return Settings()
