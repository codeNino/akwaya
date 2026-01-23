from typing import List, Dict
import asyncio
import json

from internal.domain.scraper.sources.dto import (LinkedInProfileInput, 
    IngestionResults, EnrichedLinkedInProfileOutput)

from internal.domain.scraper.sources.linkedIn import (search_linkedin, 
    deep_scrape_linkedin_profiles)
from internal.domain.scraper.sources.google import search_google_places

from internal.utils.loader import load_yaml, AppLogger, export_to_json

logger = AppLogger("internal.domain.scraper.crawler")()


class WebCrawler:

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
            google_places_task = self.source_from_google_places(batch_size, keywords)
            tasks.append(google_places_task)
            task_keys.append("whitelabels")
        
        individuals_params = ingestion_params.get("individuals")
        if individuals_params:
            batch_size = individuals_params.get("batch-size", 10)
            keywords = individuals_params.get("keywords", None)
            if not keywords:
                raise ValueError("Individuals Keywords not found in the config file")
            linkedin_task = self.source_from_linkedin(batch_size, keywords)
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

    async def source_from_linkedin(self, batch_size: int, keywords: List[str]):
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

    async def enrich_linkedin_profiles(
        self,
        profiles: List[LinkedInProfileInput],
    ) -> List[EnrichedLinkedInProfileOutput]:

        if not profiles:
            return []

        logger.info("Enriching LinkedIn profiles")

        urls = [p["url"] for p in profiles]

        try:
            results = await deep_scrape_linkedin_profiles(urls)
        except Exception as e:
            logger.error("Failed to scrape LinkedIn profiles ::: %s", e)
            return []

        # Build O(1) lookup map
        results_by_url = {
            r["profile_url"]: r
            for r in results
            if r.get("profile_url")
        }

        # logger.info("Enrichment results: %s", results_by_url)

        enriched_profiles: List[EnrichedLinkedInProfileOutput] = []

        for profile in profiles:
            result = results_by_url.get(profile["url"])
            if not result:
                continue

            enriched_profiles.append(
                {
                    "prospect_id": profile["prospect_id"],
                    "profile": result,
                }
            )

        logger.info("Enriched %d LinkedIn profiles", len(enriched_profiles))
        # logger.info("Enrichment results: %s", enriched_profiles)
        return enriched_profiles


    @staticmethod
    def flatten_to_json(nested_list: List[List], json_file_path: str):
        if not nested_list:
            return
        flat_list = [item for sublist in nested_list for item in sublist]

        export_to_json(flat_list, json_file_path)

        return
