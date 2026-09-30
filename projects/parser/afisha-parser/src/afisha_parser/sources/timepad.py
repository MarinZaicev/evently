"""Адаптер Timepad API v1 (https://dev.timepad.ru/api/get-v1-events/).

Timepad есть во всех городах справочника, в том числе там, где нет KudaGo (Челябинск, Омск,
Пермь и т. д.). Город ищется по русскому названию, поэтому код города не нужен.

Особенности:
  * токен (AFISHA_TIMEPAD_TOKEN) передаётся как Authorization: Bearer. Документация говорит,
    что публичные события доступны и без него, но с ограничением частоты запросов;
  * у площадки нет названия — только адрес, поэтому venue.name = адрес;
  * страница события на Timepad — это и есть страница регистрации/покупки, она же ticket_url;
  * берём только события, прошедшие модерацию (featured, shown), без спама;
  * длинные события (выставка на месяц) начались раньше сегодняшнего дня, поэтому ищем
    с запасом в прошлое, а прошедшее отбрасывает общий фильтр.
"""

import logging
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from pydantic import ValidationError

from ..cities import City, distance_km, get_city
from ..models import Event, Image, Price, Session, Venue
from ..text import capitalize_first, clean_text
from .base import SourceAdapter, SourceConfigError
from .kudago import parse_age

log = logging.getLogger(__name__)

API_BASE = "https://api.timepad.ru/v1"
PAGE_SIZE = 100
MAX_PAGES = 50
# Насколько далеко в прошлое искать начало ещё идущих событий
LOOKBACK_DAYS = 60
MODERATION = "featured,shown"
FIELDS = ",".join([
    "location", "ticket_types", "registration_data", "description_short", "description_html",
    "age_limit", "categories", "poster_image",
])
# Координаты дальше этого от центра города считаем ошибкой
MAX_DISTANCE_KM = 150


class TimepadAccessError(SourceConfigError):
    pass


def _parse_dt(value: Any, tz: ZoneInfo) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=tz)
    return moment.astimezone(tz)


def parse_coordinates(value: Any, city: City) -> tuple[float | None, float | None]:
    """Timepad отдаёт [a, b] без явного порядка — выбираем порядок, при котором точка ближе к городу."""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None, None
    try:
        a, b = float(value[0]), float(value[1])
    except (TypeError, ValueError):
        return None, None
    options = [(lat, lon) for lat, lon in ((a, b), (b, a)) if -90 <= lat <= 90 and -180 <= lon <= 180]
    if not options:
        return None, None
    lat, lon = min(options, key=lambda p: distance_km(p[0], p[1], city.lat, city.lon))
    if distance_km(lat, lon, city.lat, city.lon) > MAX_DISTANCE_KM:
        return None, None
    return lat, lon


_IMAGE_EXT_RE = re.compile(r"\.(?:jpe?g|png|webp|gif)", re.IGNORECASE)


def _url(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    url = "https:" + value if value.startswith("//") else value
    # Timepad иногда склеивает два адреса постера: «…poster_org_1.jpg-/preview/…/poster_event_2.jpg».
    # Такой адрес отдаёт 400 — обрезаем после первого расширения картинки.
    match = _IMAGE_EXT_RE.search(url)
    if match and url[match.end():].startswith("-/"):
        url = url[: match.end()]
    return url


def parse_price(item: dict) -> Price:
    reg = item.get("registration_data") or {}
    prices = [t.get("price") for t in item.get("ticket_types") or [] if isinstance(t, dict)]
    prices += [reg.get("price_min"), reg.get("price_max")]
    numbers = sorted({int(p) for p in prices if isinstance(p, (int, float)) and not isinstance(p, bool) and p >= 0})
    if not numbers:
        return Price()
    if numbers == [0]:
        return Price(text="бесплатно", min=0, max=0, is_free=True)
    paid = [n for n in numbers if n > 0]
    text = f"{paid[0]} ₽" if len(paid) == 1 else f"от {paid[0]} до {paid[-1]} ₽"
    return Price(text=text, min=paid[0], max=paid[-1], is_free=False)


def parse_event(item: dict, *, city: City) -> Event | None:
    title = clean_text(item.get("name"))
    url = item.get("url")
    if not title or not isinstance(url, str) or item.get("id") is None:
        return None

    tz = city.zone
    start = _parse_dt(item.get("starts_at"), tz)
    end = _parse_dt(item.get("ends_at"), tz)
    if end is not None and start is not None and end < start:
        end = None
    sessions = [Session(starts_at=start, ends_at=end)] if start or end else []

    location = item.get("location") or {}
    venue = None
    address = clean_text(location.get("address"))
    if address:
        lat, lon = parse_coordinates(location.get("coordinates"), city)
        venue = Venue(name=address, address=address, lat=lat, lon=lon)

    images = []
    poster = item.get("poster_image") or {}
    if image_url := _url(poster.get("uploadcare_url")) or _url(poster.get("default_url")):
        images.append(Image(url=image_url))

    categories = [
        name.strip().lower()
        for c in item.get("categories") or []
        if isinstance(c, dict) and isinstance(name := c.get("name"), str) and name.strip()
    ]
    organization = item.get("organization") or {}

    return Event(
        source=TimepadAdapter.name,
        source_id=str(item["id"]),
        source_url=url,
        ticket_url=url,
        city=city.slug,
        title=capitalize_first(title),
        tagline=clean_text(organization.get("name")) if isinstance(organization, dict) else None,
        description=clean_text(item.get("description_short")),
        full_text=clean_text(item.get("description_html")),
        categories=categories,
        age_restriction=parse_age(item.get("age_limit")),
        price=parse_price(item),
        venue=venue,
        sessions=sessions,
        images=images,
    )


class TimepadAdapter(SourceAdapter):
    name = "timepad"

    @property
    def token(self) -> str | None:
        return self.settings.timepad_token if self.settings else None

    async def fetch_events(
        self, city: str, *, days: int = 30, limit: int | None = None
    ) -> AsyncIterator[Event]:
        found = get_city(city)
        if found is None or not found.timepad:
            raise SourceConfigError(f"Города {city!r} нет в справочнике cities.py")
        now = datetime.now(UTC).replace(microsecond=0)
        oldest, newest = now - timedelta(days=LOOKBACK_DAYS), now + timedelta(days=days)
        base_params = {
            "cities": found.name,
            "fields": FIELDS,
            "moderation_statuses": MODERATION,
            "starts_at_min": oldest.isoformat(),
            "starts_at_max": newest.isoformat(),
            # Сначала самые поздние: как только пошли события старше окна — дальше читать незачем.
            # Не полагаемся на то, что Timepad применит starts_at_min (на первом прогоне не применял).
            "sort": "-starts_at",
            "limit": PAGE_SIZE,
        }
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else None
        yielded = 0
        for page in range(1, MAX_PAGES + 1):
            params = {**base_params, "skip": (page - 1) * PAGE_SIZE}
            try:
                response = await self.http.get(f"{API_BASE}/events.json", params=params, headers=headers)
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status in (401, 403):
                    raise TimepadAccessError(
                        f"Timepad ответил {status}: нужен токен. Получите его на dev.timepad.ru/api/oauth/ "
                        f"и впишите в .env: AFISHA_TIMEPAD_TOKEN=..." if not self.token
                        else f"Timepad ответил {status}: токен не подходит или отозван"
                    ) from exc
                if page > 1 and status in (400, 422):
                    log.warning("Timepad %s: дальше страницы %d не пускает (%d), беру что есть", city, page - 1, status)
                    return
                raise
            data = response.json()
            self.save_raw(f"events-page-{page:03d}", data)
            values = data.get("values") or []
            log.info("Timepad %s: страница %d, записей %d (всего у источника: %s)",
                     city, page, len(values), data.get("total"))
            starts = [s for item in values if (s := _parse_dt(item.get("starts_at"), found.zone))]
            for item in values:
                start = _parse_dt(item.get("starts_at"), found.zone)
                if start is not None and start > newest:
                    continue  # за горизонтом сбора
                try:
                    event = parse_event(item, city=found)
                except (KeyError, TypeError, ValueError, ValidationError) as exc:
                    log.warning("Timepad: пропускаю событие id=%s: %s", item.get("id"), exc)
                    continue
                if event is None:
                    continue
                yield event
                yielded += 1
                if limit is not None and yielded >= limit:
                    return
            total = data.get("total")
            if len(values) < PAGE_SIZE or (isinstance(total, int) and page * PAGE_SIZE >= total):
                return
            if starts and starts == sorted(starts, reverse=True) and starts[-1] < oldest:
                log.info("Timepad %s: дальше только события старше %d дней, останавливаюсь", city, LOOKBACK_DAYS)
                return
        log.warning("Timepad %s: достигнут предел %d страниц", city, MAX_PAGES)

    async def list_cities(self) -> list[tuple[str, str]]:
        from ..cities import CITIES
        return [(c.slug, c.name) for c in CITIES.values() if c.timepad]
