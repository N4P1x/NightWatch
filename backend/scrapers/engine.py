"""
Night-Watch Advanced Scraping Engine
Async httpx-based engine with retry, circuit breaker, anti-fingerprinting, and health monitoring.
"""

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import httpx
from bs4 import BeautifulSoup

from backend.scrapers.base import (
    BaseScraper,
    ScrapedIOC,
    ScrapedLeak,
    ScrapeMetrics,
    ScrapeResult,
    SourceType,
)
from backend.scrapers.classifiers import ContentClassifier


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3

    _state: CircuitState = field(default=CircuitState.CLOSED, init=False, repr=False)
    _failure_count: int = field(default=0, init=False, repr=False)
    _success_count: int = field(default=0, init=False, repr=False)
    _last_failure_time: float | None = field(default=None, init=False, repr=False)
    _half_open_calls: int = field(default=0, init=False, repr=False)

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN and self._last_failure_time:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
        return self._state

    def record_success(self):
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.half_open_max_calls:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
        elif self._state == CircuitState.CLOSED:
            self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            self._success_count = 0
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN

    @property
    def allow_request(self) -> bool:
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.half_open_max_calls
        return False


# --- Anti-Fingerprint ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

ACCEPT_HEADERS = [
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
]

ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-US,en;q=0.9,de;q=0.8",
    "en-GB,en;q=0.9",
    "en-US,en;q=0.9,fr;q=0.8,de;q=0.7",
]


def build_fingerprint_headers() -> dict[str, str]:
    """Build randomized browser-like headers to avoid detection."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": random.choice(ACCEPT_HEADERS),
        "Accept-Language": random.choice(ACCEPT_LANGUAGES),
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": random.choice(["max-age=0", "no-cache"]),
    }


# --- Source Health Tracking ---
@dataclass
class SourceHealth:
    source_url: str
    total_attempts: int = 0
    successes: int = 0
    failures: int = 0
    consecutive_failures: int = 0
    avg_response_time_ms: float = 0.0
    last_success: datetime | None = None
    last_failure: datetime | None = None
    last_error: str | None = None

    @property
    def reliability(self) -> float:
        return (self.successes / self.total_attempts * 100) if self.total_attempts > 0 else 0.0

    @property
    def is_healthy(self) -> bool:
        return self.consecutive_failures < 5 and self.reliability > 50

    def record_success(self, response_time_ms: float):
        self.total_attempts += 1
        self.successes += 1
        self.consecutive_failures = 0
        self.last_success = datetime.now(UTC)
        self.avg_response_time_ms = (
            (self.avg_response_time_ms * (self.total_attempts - 1) + response_time_ms)
            / self.total_attempts
        )

    def record_failure(self, error: str):
        self.total_attempts += 1
        self.failures += 1
        self.consecutive_failures += 1
        self.last_failure = datetime.now(UTC)
        self.last_error = error


# --- Main Engine ---
class ScrapingEngine:
    """
    Enterprise-grade async scraping engine.
    Features: async httpx, circuit breaker, anti-fingerprinting, retry with backoff,
    source health tracking, content extraction, real-time metrics.
    """

    def __init__(
        self,
        max_concurrent: int = 10,
        tor_proxy: str = "socks5://127.0.0.1:9050",
        timeout: float = 30.0,
        max_retries: int = 3,
        max_content_size: int = 5_000_000,
        retry_delay_base: int = 2,
        verify_ssl: bool = True,
    ):
        self.max_concurrent = max_concurrent
        self.tor_proxy = tor_proxy
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_content_size = max_content_size
        self.retry_delay_base = retry_delay_base
        self.verify_ssl = verify_ssl
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._source_health: dict[str, SourceHealth] = {}
        self._metrics = ScrapeMetrics()
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._cancel_event = asyncio.Event()

    @property
    def metrics(self) -> ScrapeMetrics:
        return self._metrics

    def get_source_health(self, url: str) -> SourceHealth:
        if url not in self._source_health:
            self._source_health[url] = SourceHealth(source_url=url)
        return self._source_health[url]

    def get_circuit_breaker(self, url: str) -> CircuitBreaker:
        domain = url.split("/")[2] if "/" in url else url
        if domain not in self._circuit_breakers:
            self._circuit_breakers[domain] = CircuitBreaker()
        return self._circuit_breakers[domain]

    @staticmethod
    def _sanitize_proxy_url(url: str) -> str:
        """Remove credentials from a proxy URL for safe logging."""
        try:
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(url)
            if parsed.username or parsed.password:
                netloc = f"{parsed.hostname}:{parsed.port}" if parsed.port else parsed.hostname
                parsed = parsed._replace(netloc=netloc)
                return urlunparse(parsed)
            return url
        except Exception:
            return url

    def _build_client(self, use_tor: bool = True) -> httpx.AsyncClient:
        """Build an httpx AsyncClient with appropriate proxy and timeout."""
        proxies = {"all://": self.tor_proxy} if use_tor else None
        return httpx.AsyncClient(
            proxies=proxies,
            timeout=httpx.Timeout(self.timeout, connect=10.0),
            follow_redirects=True,
            verify=self.verify_ssl,
            limits=httpx.Limits(
                max_connections=self.max_concurrent * 2,
                max_keepalive_connections=self.max_concurrent,
                keepalive_expiry=30,
            ),
        )

    @asynccontextmanager
    async def _rate_limited_request(self):
        """Context manager for rate-limited concurrent requests."""
        async with self._semaphore:
            yield

    async def scrape_url(
        self,
        url: str,
        source_id: int,
        source_type: SourceType = SourceType.TOR_ONION,
        config: dict[str, Any] = None,
        scraper: BaseScraper | None = None,
    ) -> ScrapeResult:
        """Scrape a single URL with full retry, circuit breaker, and health tracking."""
        cfg = config or {}
        use_tor = cfg.get("use_tor", source_type == SourceType.TOR_ONION)
        health = self.get_source_health(url)
        cb = self.get_circuit_breaker(url)

        if not cb.allow_request:
            return ScrapeResult(
                url=url, source_id=source_id, source_type=source_type,
                error=f"Circuit breaker OPEN for {url}", success=False,
            )

        start_time = time.monotonic()
        last_error = ""

        for attempt in range(1, self.max_retries + 1):
            if self._cancel_event.is_set():
                return ScrapeResult(
                    url=url, source_id=source_id, source_type=source_type,
                    error="Scrape cancelled", success=False,
                )

            async with self._rate_limited_request():
                try:
                    result = await asyncio.wait_for(
                        self._do_fetch(url, source_id, source_type, use_tor, cfg, scraper),
                        timeout=self.timeout + 5.0,
                    )
                    elapsed_ms = (time.monotonic() - start_time) * 1000
                    result.response_time_ms = elapsed_ms

                    if result.success:
                        cb.record_success()
                        health.record_success(elapsed_ms)
                        self._metrics.successful += 1
                        self._metrics.total_iocs += len(result.iocs)
                        self._metrics.total_leaks += len(result.leaks)
                        return result
                    else:
                        last_error = result.error or "Unknown error"

                except Exception as e:
                    last_error = str(e)

            cb.record_failure()
            health.record_failure(last_error)

            if attempt < self.max_retries:
                delay = self.retry_delay_base ** attempt + random.uniform(0.5, 2.0)
                await asyncio.sleep(delay)

        self._metrics.failed += 1
        health.record_failure(f"All {self.max_retries} retries failed: {last_error}")
        elapsed_ms = (time.monotonic() - start_time) * 1000

        return ScrapeResult(
            url=url, source_id=source_id, source_type=source_type,
            error=f"Failed after {self.max_retries} attempts: {last_error}",
            response_time_ms=elapsed_ms, success=False,
        )

    def _extract_text(self, raw_html: str) -> tuple[str, str, str]:
        """Extract title, body text, and cleaned content from HTML."""
        from backend.scrapers.extractors import sanitize_text
        soup = BeautifulSoup(raw_html, "html.parser")
        for tag in soup(["script", "style", "noscript", "link", "meta"]):
            tag.decompose()
        title_tag = soup.find("title")
        title = sanitize_text(title_tag.get_text(strip=True)[:200]) if title_tag else ""
        body = soup.find("body") or soup
        text = body.get_text(separator=" ", strip=True)
        text = sanitize_text(text)[:50000]
        return title, text, str(soup)

    def _detect_rss_feed(self, raw_html: str) -> list[str]:
        """Detect RSS/Atom feed and extract article URLs. Returns empty list if not a feed."""
        articles: list[str] = []
        soup = BeautifulSoup(raw_html, "xml")
        is_rss = soup.find("rss") is not None
        is_atom = soup.find("feed") is not None

        if not is_rss and not is_atom:
            soup = BeautifulSoup(raw_html, "html.parser")
            is_rss = soup.find("rss") is not None
            is_atom = soup.find("feed") is not None

        if not is_rss and not is_atom:
            return []

        if is_rss:
            for item in soup.find_all("item"):
                link_tag = item.find("link")
                if link_tag and link_tag.get_text(strip=True):
                    articles.append(link_tag.get_text(strip=True))
        elif is_atom:
            for entry in soup.find_all("entry"):
                link_tag = entry.find("link")
                if link_tag:
                    href = link_tag.get("href")
                    if href:
                        articles.append(href)

        return articles

    async def _do_fetch(
        self,
        url: str,
        source_id: int,
        source_type: SourceType,
        use_tor: bool,
        config: dict[str, Any],
        scraper: BaseScraper | None,
    ) -> ScrapeResult:
        """Perform the actual HTTP fetch and content extraction."""
        result = ScrapeResult(url=url, source_id=source_id, source_type=source_type)
        headers = build_fingerprint_headers()

        async with self._build_client(use_tor=use_tor) as client:
            async with client.stream("GET", url, headers=headers) as response:
                result.status_code = response.status_code

                if response.status_code != 200:
                    result.error = f"HTTP {response.status_code}"
                    return result

                try:
                    content_length = int(response.headers.get("content-length", 0))
                except (ValueError, TypeError):
                    content_length = 0
                if content_length > self.max_content_size:
                    result.error = f"Content too large: {content_length} bytes"
                    return result

                content = b""
                async for chunk in response.aiter_bytes():
                    content += chunk
                    if len(content) > self.max_content_size:
                        break
            raw_html = content.decode("utf-8", errors="replace")[:self.max_content_size]

            result.content = raw_html

            # Check if this is an RSS/Atom feed — if so, crawl individual articles
            rss_articles = self._detect_rss_feed(raw_html)
            if rss_articles:
                all_iocs: list[ScrapedIOC] = []
                all_leaks: list[ScrapedLeak] = []
                result.title = rss_articles[0][:200] if rss_articles else "RSS Feed"

                for article_url in rss_articles[:config.get("max_rss_articles", 5)]:
                    try:
                        article_response = await client.get(article_url, headers=headers)
                        if article_response.status_code != 200:
                            continue
                        article_html = article_response.text
                        if len(article_html) > self.max_content_size:
                            article_html = article_html[:self.max_content_size]

                        _, article_text, _ = self._extract_text(article_html)

                        if scraper:
                            iocs = await scraper.extract_iocs(article_text, article_url)
                        else:
                            from backend.scrapers.extractors import AdvancedIOCExtractor
                            extractor = AdvancedIOCExtractor()
                            iocs = await extractor.extract_all(article_text, article_url)

                        all_iocs.extend(iocs)
                    except Exception:
                        continue

                result.iocs = all_iocs
                result.leaks = all_leaks
                result.success = True
                return result

            # Standard HTML page
            result.title, text, _ = self._extract_text(raw_html)
            result.text_content = text

            if scraper:
                result.iocs = await scraper.extract_iocs(text, url)
                result.leaks = await scraper.extract_leaks(text, url, source_id, page_title=result.title or "")
            else:
                from backend.scrapers.extractors import AdvancedIOCExtractor, LeakExtractor
                extractor = AdvancedIOCExtractor()
                leak_extractor = LeakExtractor()
                result.iocs = await extractor.extract_all(text, url)
                result.leaks = await leak_extractor.extract(text, url, source_id, page_title=result.title or "")

            _classifier = ContentClassifier()
            result.category, _ = _classifier.classify(text, url)
            result.severity, _ = _classifier.assess_severity(
                text, result.category,
                ioc_count=len(result.iocs),
                has_cve=any(ioc.type == "cve" for ioc in result.iocs),
            )

            result.success = True
            return result

    async def scrape_batch(
        self,
        targets: list[dict[str, Any]],
        on_complete: Callable[[ScrapeResult], Awaitable[None]] | None = None,
    ) -> list[ScrapeResult]:
        """Scrape a batch of URLs concurrently with metrics tracking."""
        self._metrics = ScrapeMetrics(
            total_urls=len(targets),
            started_at=datetime.now(UTC),
        )
        self._cancel_event.clear()

        results: list[ScrapeResult] = []

        async def _scrape_one(target: dict[str, Any]) -> ScrapeResult:
            url = target["url"]
            source_id = target.get("source_id", 0)
            source_type = SourceType(target.get("source_type", "tor_onion"))
            config = target.get("config", {})

            result = await self.scrape_url(url, source_id, source_type, config)
            self._metrics.scraped += 1

            if on_complete:
                await on_complete(result)

            return result

        tasks = [asyncio.create_task(_scrape_one(t)) for t in targets]
        self._active_tasks = {t.get_name(): t for t in tasks}
        try:
            done_results = await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            self._active_tasks.clear()

        for r in done_results:
            if isinstance(r, Exception):
                self._metrics.errors.append(str(r)[:200])
            elif isinstance(r, ScrapeResult):
                results.append(r)

        self._metrics.completed_at = datetime.now(UTC)
        if self._metrics.started_at:
            self._metrics.uptime_seconds = (
                self._metrics.completed_at - self._metrics.started_at
            ).total_seconds()

        return results

    async def cancel(self):
        """Cancel all active scrape tasks."""
        self._cancel_event.set()
        for task in self._active_tasks.values():
            task.cancel()
        self._active_tasks.clear()

    def get_all_health(self) -> dict[str, dict[str, Any]]:
        """Get health status for all tracked sources."""
        return {
            url: {
                "reliability": round(h.reliability, 1),
                "total_attempts": h.total_attempts,
                "consecutive_failures": h.consecutive_failures,
                "avg_response_time_ms": round(h.avg_response_time_ms, 1),
                "is_healthy": h.is_healthy,
                "last_success": h.last_success.isoformat() if h.last_success else None,
                "last_error": h.last_error,
            }
            for url, h in self._source_health.items()
        }

    def get_circuit_states(self) -> dict[str, str]:
        return {
            domain: cb.state.value
            for domain, cb in self._circuit_breakers.items()
        }
