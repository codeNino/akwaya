from typing import List, Dict
import asyncio
import json

from internal.utils.search_engine import search_linkedin, search_google_places
from internal.utils.loader import load_yaml, AppLogger

logger = AppLogger("WebCawler")()


class WebCawler:

    def __init__(self, max_concurrent_requests: int = 5):
        # Semaphore limits concurrent requests to avoid rate limiting
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)

    async def scrape_from_sources(self, keywords_path: str):
        config_file = load_yaml(keywords_path)  
        batch_size = config_file.get("batch-size", 10)
        keywords = config_file.get("keywords", None)
        if not keywords:
            raise ValueError("Keywords not found in the config file")

        linkedin_task = self.scrape_linkedin(batch_size, keywords.get("linkedin", []))
        google_places_task = self.scrape_google_places(batch_size, keywords.get("google_places", []))

        linkedin_results, google_places_results = await asyncio.gather(
            linkedin_task, google_places_task
        )

        return linkedin_results, google_places_results

    async def _safe_scrape(self, keyword: str, batch_size: int, func):
        async with self.semaphore:
            return await func(keyword, batch_size)

    async def scrape_linkedin(self, batch_size: int, keywords: List[str]):
        logger.info("Scraping LinkedIn for keywords: %s", keywords)

        # Schedule all keyword searches concurrently
        tasks = [self._safe_scrape(k, batch_size, search_linkedin) for k in keywords]
        linkedin_results = await asyncio.gather(*tasks)

        logger.info("Scraped LinkedIn for keywords: %s", keywords)
        return linkedin_results


    async def scrape_google_places(self, batch_size: int, keywords: List[str]):
        logger.info("Scraping Google Places for keywords: %s", keywords)

        tasks = [self._safe_scrape(k, batch_size, search_google_places) for k in keywords]
        google_places_results = await asyncio.gather(*tasks)

        logger.info("Scraped Google Places for keywords: %s", keywords)
        return google_places_results

    @staticmethod
    def flatten_to_json(nested_list: List[List[Dict]], json_file_path: str):
        logger.info("Original List Length: %s", len(nested_list))
        flat_list = [item for sublist in nested_list for item in sublist]
        logger.info("Flattened List Length: %s", len(flat_list))

        # Write to JSON file
        with open(json_file_path, "w", encoding="utf-8") as f:
            json.dump(flat_list, f, ensure_ascii=False, indent=4)

        return flat_list
