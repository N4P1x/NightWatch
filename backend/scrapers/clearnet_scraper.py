"""
Night-Watch Clearnet Scraper
Async scraper for clearnet paste sites, forums, and news feeds.
No Tor proxy - direct HTTP(S) connections.
"""

from typing import Any

from backend.scrapers.base import BaseScraper, ScrapedIOC, ScrapedLeak, ScrapeResult, SourceType
from backend.scrapers.engine import ScrapingEngine
from backend.scrapers.extractors import AdvancedIOCExtractor, LeakExtractor


class ClearnetScraper(BaseScraper):
    """Async clearnet scraper for HTTPS sources."""

    def __init__(self, **kwargs):
        super().__init__(source_type=SourceType.CLEARNET, **kwargs)
        self.ioc_extractor = AdvancedIOCExtractor()
        self.leak_extractor = LeakExtractor()

    async def scrape(self, url: str, source_id: int, config: dict[str, Any] = None) -> ScrapeResult:
        engine = ScrapingEngine(
            timeout=self.timeout,
            max_retries=self.max_retries,
            max_content_size=self.max_content_size,
        )
        return await engine.scrape_url(
            url=url,
            source_id=source_id,
            source_type=SourceType.CLEARNET,
            config=config or {"use_tor": False},
            scraper=self,
        )

    async def extract_iocs(self, text: str, source_url: str = "") -> list[ScrapedIOC]:
        return await self.ioc_extractor.extract_all(text, source_url)

    async def extract_leaks(self, text: str, url: str, source_id: int, page_title: str = "") -> list[ScrapedLeak]:
        return await self.leak_extractor.extract(text, url, source_id, page_title=page_title)
