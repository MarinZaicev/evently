"""Общий HTTP-клиент: паузы между запросами, повторы при сбоях, честный User-Agent."""

import asyncio
import logging
import time
from types import TracebackType

import httpx

from .config import Settings

log = logging.getLogger(__name__)

RETRY_STATUSES = {429, 500, 502, 503, 504}


class HttpClient:
    def __init__(
        self,
        settings: Settings,
        *,
        delay: float | None = None,
        accept: str = "application/json",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            timeout=settings.request_timeout,
            headers={"User-Agent": settings.user_agent, "Accept": accept},
            follow_redirects=True,
            transport=transport,
        )
        self._delay = settings.request_delay if delay is None else delay
        self._max_retries = max(1, settings.max_retries)
        self._last_request = 0.0
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "HttpClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self._client.aclose()

    async def _throttle(self) -> None:
        async with self._lock:
            wait = self._last_request + self._delay - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request = time.monotonic()

    async def get(self, url: str, *, params: dict | None = None, headers: dict | None = None) -> httpx.Response:
        for attempt in range(1, self._max_retries + 1):
            await self._throttle()
            response: httpx.Response | None = None
            try:
                response = await self._client.get(url, params=params, headers=headers)
            except httpx.TransportError as exc:
                if attempt == self._max_retries:
                    raise
                log.warning("Сетевая ошибка %s (попытка %d/%d): %s", url, attempt, self._max_retries, exc)
            else:
                if response.status_code not in RETRY_STATUSES or attempt == self._max_retries:
                    response.raise_for_status()
                    return response
                log.warning(
                    "HTTP %d от %s (попытка %d/%d)", response.status_code, url, attempt, self._max_retries
                )
            await asyncio.sleep(self._backoff(attempt, response))
        raise RuntimeError("недостижимо: цикл всегда возвращает ответ или бросает исключение")

    @staticmethod
    def _backoff(attempt: int, response: httpx.Response | None) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After", "")
            if retry_after.isdigit():
                return min(float(retry_after), 60.0)
        return min(2.0 ** attempt, 30.0)
