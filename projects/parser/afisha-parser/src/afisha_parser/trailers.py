"""Скачивание файлов трейлеров с YouTube через yt-dlp (по желанию, по умолчанию выключено).

Про права. Трейлер — чужое произведение. Показывать его в приложении через официальный
плеер YouTube (поле trailer.embed_url) можно без разрешений. Хранить у себя файл
и раздавать его пользователям — только с разрешения правообладателя (прокатчика),
плюс это нарушает условия YouTube. Поэтому скачивание включается отдельным флагом
AFISHA_TRAILERS_DOWNLOAD=true и нужно для случаев, когда разрешение есть
(или файлы нужны для внутренней проверки/превью, а не для раздачи).

Устройство:
  * файлы — output/trailers/<id ролика>.mp4, один ролик качается один раз;
  * trailers/index.json помнит скачанное и неудачи: после MAX_FAILURES попыток ролик
    больше не трогаем (удалён, закрыт в регионе и т. п.);
  * за один цикл качается не больше AFISHA_TRAILERS_PER_RUN роликов, чтобы первый
    запуск не занял полдня.
"""

import asyncio
import importlib.util
import json
import logging
import shutil
from collections.abc import Callable, Iterable
from pathlib import Path

from .config import Settings
from .enrichers.tmdb_trailers import Trailer
from .export import write_json_atomic

log = logging.getLogger(__name__)

MAX_FAILURES = 3
INDEX_NAME = "index.json"

# (ссылка, папка, id ролика, настройки) → путь к файлу или None
Downloader = Callable[[str, Path, str, Settings], Path | None]


def yt_dlp_available() -> bool:
    return importlib.util.find_spec("yt_dlp") is not None


def _format_selector(max_height: int, can_merge: bool) -> str:
    progressive = f"b[height<={max_height}][ext=mp4]/b[height<={max_height}]/b"
    if not can_merge:
        return progressive  # без ffmpeg склеить видео и звук нельзя — берём готовый файл
    return f"bv*[height<={max_height}][ext=mp4]+ba[ext=m4a]/{progressive}"


def yt_dlp_download(url: str, dest_dir: Path, key: str, settings: Settings) -> Path | None:
    import yt_dlp  # необязательная зависимость: pip install ".[trailers]"

    dest_dir.mkdir(parents=True, exist_ok=True)
    options = {
        "format": _format_selector(settings.trailer_max_height, shutil.which("ffmpeg") is not None),
        "merge_output_format": "mp4",
        "outtmpl": str(dest_dir / f"{key}.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "max_filesize": settings.trailer_max_mb * 1024 * 1024,
        "retries": 3,
        "socket_timeout": 30,
        "http_headers": {"User-Agent": settings.user_agent},
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([url])
    files = [p for p in dest_dir.glob(f"{key}.*") if p.suffix not in {".part", ".ytdl", ".tmp"}]
    return max(files, key=lambda p: p.stat().st_size) if files else None


def _load_index(folder: Path) -> dict:
    try:
        data = json.loads((folder / INDEX_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    return {"files": dict(data.get("files") or {}), "failed": dict(data.get("failed") or {})}


async def download_trailers(
    trailers: Iterable[Trailer],
    output_dir: Path,
    settings: Settings,
    *,
    downloader: Downloader | None = None,
) -> int:
    """Качает недостающие ролики и проставляет trailer.local_path. Возвращает число новых файлов."""
    trailers = [t for t in trailers if t is not None]
    if not trailers:
        return 0
    if downloader is None:
        if not yt_dlp_available():
            log.error('Скачивание трейлеров включено, но yt-dlp не установлен: pip install ".[trailers]"')
            return 0
        downloader = yt_dlp_download

    folder = output_dir / "trailers"
    index = _load_index(folder)
    files: dict[str, str] = {k: v for k, v in index["files"].items() if (output_dir / v).is_file()}
    failed: dict[str, int] = index["failed"]

    queue: list[Trailer] = []
    for trailer in {t.key: t for t in trailers}.values():
        if trailer.key in files or failed.get(trailer.key, 0) >= MAX_FAILURES:
            continue
        queue.append(trailer)
    budget = max(0, settings.trailers_per_run)
    if len(queue) > budget:
        log.info("Трейлеры: в очереди %d, за этот цикл качаю %d, остальные — в следующих", len(queue), budget)
    downloaded = 0
    for trailer in queue[:budget]:
        try:
            path = await asyncio.to_thread(downloader, trailer.url, folder, trailer.key, settings)
        except Exception as exc:  # yt-dlp бросает свои DownloadError, сеть — свои
            path = None
            log.warning("Трейлер %s не скачан: %s", trailer.url, str(exc).splitlines()[0] if str(exc) else exc)
        if path is None:
            failed[trailer.key] = failed.get(trailer.key, 0) + 1
            continue
        files[trailer.key] = path.relative_to(output_dir).as_posix()
        failed.pop(trailer.key, None)
        downloaded += 1

    for trailer in trailers:
        trailer.local_path = files.get(trailer.key)
    write_json_atomic(folder / INDEX_NAME, {"files": dict(sorted(files.items())), "failed": failed})
    log.info("Трейлеры: новых файлов %d, всего скачано %d", downloaded, len(files))
    return downloaded
