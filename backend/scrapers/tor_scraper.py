"""
Night-Watch Async Tor Scraper
Uses httpx with SOCKS5 proxy for Tor hidden service scraping.
"""

from typing import Any

from backend.scrapers.base import BaseScraper, ScrapedIOC, ScrapedLeak, ScrapeResult, SourceType
from backend.scrapers.engine import ScrapingEngine
from backend.scrapers.extractors import AdvancedIOCExtractor, LeakExtractor


class AsyncTorScraper(BaseScraper):
    """Async Tor hidden service scraper with full IOC/leak extraction."""

    def __init__(self, tor_proxy: str = "socks5://127.0.0.1:9050", **kwargs):
        super().__init__(source_type=SourceType.TOR_ONION, **kwargs)
        self.tor_proxy = tor_proxy
        self.ioc_extractor = AdvancedIOCExtractor()
        self.leak_extractor = LeakExtractor()

    async def scrape(self, url: str, source_id: int, config: dict[str, Any] = None) -> ScrapeResult:
        engine = ScrapingEngine(
            tor_proxy=self.tor_proxy,
            timeout=self.timeout,
            max_retries=self.max_retries,
            max_content_size=self.max_content_size,
        )
        return await engine.scrape_url(
            url=url,
            source_id=source_id,
            source_type=SourceType.TOR_ONION,
            config=config or {"use_tor": True},
            scraper=self,
        )

    async def extract_iocs(self, text: str, source_url: str = "") -> list[ScrapedIOC]:
        return await self.ioc_extractor.extract_all(text, source_url)

    async def extract_leaks(self, text: str, url: str, source_id: int, page_title: str = "") -> list[ScrapedLeak]:
        return await self.leak_extractor.extract(text, url, source_id, page_title=page_title)
