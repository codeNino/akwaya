from typing import List, Dict
import asyncio


from internal.domain.brainbox.engine import generate_keywords
from internal.domain.scraper.sources.google import search_google_places, search_google_with_serper

from internal.utils.loader import load_yaml, AppLogger, export_to_json

logger = AppLogger("internal.domain.scraper.crawler")()


class WebSearcher:

    def __init__(self, max_concurrent_requests: int = 5):
        # Semaphore limits concurrent requests to avoid rate limiting
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)

    async def search_for_prospects(self, query: str, batch_size: int):
        tasks: list[asyncio.Task] = []

        keywords = generate_keywords(query)
        
        google_places_task = self.source_from_google_places(batch_size, keywords)
        tasks.append(google_places_task)
        
        google_search_task = self.source_from_google_search(batch_size, keywords)
        tasks.append(google_search_task)
        

        return await asyncio.gather(*tasks, return_exceptions=True)
        

    async def _safe_scrape(self, keyword: str, batch_size: int, func):
        async with self.semaphore:
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
            return []


    @staticmethod
    def flatten_to_json(nested_list: List[List], json_file_path: str):
        if not nested_list:
            return
        flat_list = [item for sublist in nested_list for item in sublist]

        export_to_json(flat_list, json_file_path)

        return
