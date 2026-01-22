from typing import List, Dict, TypedDict, Optional
import asyncio
import json

from internal.utils.search_engine import search_linkedin, search_google_places
from internal.utils.loader import load_yaml, AppLogger

logger = AppLogger("WebCawler")()

class IngestionResults(TypedDict, total=False):
    whitelabels: Optional[List]
    individuals: Optional[List]

class WebCawler:

    def __init__(self, max_concurrent_requests: int = 5):
        # Semaphore limits concurrent requests to avoid rate limiting
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)

    async def search_for_prospects(self, keywords_path: str):
        tasks: list[asyncio.Task] = []
        task_keys: list[str] = []

        config_file = load_yaml(keywords_path)  
        ingestion_params = config_file.get("raw_prospect_ingestion")
        if not ingestion_params:
            raise ValueError("Ingestion params not found in the config file")
        
        whitelabels_params = ingestion_params.get("whitelabels")
        if whitelabels_params:
            batch_size = whitelabels_params.get("batch-size", 10)
            keywords = whitelabels_params.get("keywords", None)
            if not keywords:
                raise ValueError("Whitelabel Keywords not found in the config file")
            google_places_task = self.scrape_google_places(batch_size, keywords)
            tasks.append(google_places_task)
            task_keys.append("whitelabels")
        
        individuals_params = ingestion_params.get("individuals")
        if individuals_params:
            batch_size = individuals_params.get("batch-size", 10)
            keywords = individuals_params.get("keywords", None)
            if not keywords:
                raise ValueError("Individuals Keywords not found in the config file")
            linkedin_task = self.scrape_linkedin(batch_size, keywords)
            tasks.append(linkedin_task)
            task_keys.append("individuals")
        
        results: IngestionResults = {}

        if not tasks:
            return results

        task_results = await asyncio.gather(*tasks, return_exceptions=False)

        for key, value in zip(task_keys, task_results):
            results[key] = value

        return results

    async def _safe_scrape(self, keyword: str, batch_size: int, func):
        async with self.semaphore:
            return await func(keyword, batch_size)

    async def scrape_linkedin(self, batch_size: int, keywords: List[str]):
        try:
            logger.info("Scraping LinkedIn for keywords: %s", keywords)

            # Schedule all keyword searches concurrently
            tasks = [self._safe_scrape(k, batch_size, search_linkedin) for k in keywords]
            linkedin_results = await asyncio.gather(*tasks)

            logger.info("Scraped LinkedIn for keywords: %s", keywords)
            return linkedin_results
        except Exception as e:
            logger.error("Failed to scrape LinkedIn for keywords ::: %s", e)
            return []


    async def scrape_google_places(self, batch_size: int, keywords: List[str]):
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
        if len(nested_list) == 0:
            return None
        flat_list = [item for sublist in nested_list for item in sublist]

        # Write to JSON file
        with open(json_file_path, "w", encoding="utf-8") as f:
            json.dump(flat_list, f, ensure_ascii=False, indent=4)

        return flat_list
