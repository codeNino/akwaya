from typing import List, Dict
import asyncio


from internal.domain.brainbox.engine import generate_keywords
from internal.domain.scraper.sources.google import search_google_places, search_google_with_serper

from internal.utils.loader import load_yaml, AppLogger, export_to_json

logger = AppLogger("internal.domain.scraper.crawler")()


class WebSearcher:

    def __init__(self, max_concurrent_requests: int = 5):
        self._max_concurrent_requests = max_concurrent_requests
        self._semaphore = None

    async def search_for_prospects(self, query: str, batch_size: int):
        # Create semaphore in the current event loop to avoid "bound to a different event loop"
        self._semaphore = asyncio.Semaphore(self._max_concurrent_requests)
        tasks: list[asyncio.Task] = []

        keywords = generate_keywords(query)
        
        google_places_task = self.source_from_google_places(batch_size, keywords)
        tasks.append(google_places_task)
        
        google_search_task = self.source_from_google_search(batch_size, keywords)
        tasks.append(google_search_task)
        

        return await asyncio.gather(*tasks, return_exceptions=True)
        

    def _ensure_semaphore_for_loop(self) -> None:
        """Create or refresh semaphore so it is bound to the current event loop."""
        loop = asyncio.get_running_loop()
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._max_concurrent_requests)
            return
        # Recreate if bound to a different loop (e.g. after asyncio.run() in another call)
        old_loop = getattr(self._semaphore, "_loop", None)
        if old_loop is not loop:
            self._semaphore = asyncio.Semaphore(self._max_concurrent_requests)

    async def _safe_scrape(self, keyword: str, batch_size: int, func):
        self._ensure_semaphore_for_loop()
        async with self._semaphore:
            return await func(keyword, batch_size)

    async def source_from_google_search (self, batch_size: int, keywords: List[str]):
        try:
            logger.info("Scraping Google Search for keywords: %s", keywords)

            # Schedule all keyword searches concurrently
            tasks = [self._safe_scrape(k, batch_size, search_google_with_serper) for k in keywords]
            google_search_results = await asyncio.gather(*tasks)

            logger.info("Scraped Google Search for keywords: %s", keywords)
            return google_search_results
        except Exception as e:
            logger.error("Failed to scrape Google Search for keywords ::: %s", e)
            return []


    async def source_from_google_places(self, batch_size: int, keywords: List[str]):
        try:
            logger.info("Scraping Google Places for keywords: %s", keywords)

            tasks = [self._safe_scrape(k, batch_size, search_google_places) for k in keywords]
            google_places_results = await asyncio.gather(*tasks)

            logger.info("Scraped Google Places for keywords: %s", keywords)
            return google_places_results
        except Exception as e:
            logger.error("Failed to scrape Google Places for keywords ::: %s", e)
            logger.info("Pipeline will continue with other sources (e.g. Serper). Check network/DNS if places.googleapis.com is unreachable.")
            return []


