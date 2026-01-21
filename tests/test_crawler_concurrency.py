import asyncio
import time
from typing import List
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
import sys
import os
sys.path.append(os.path.abspath("/Users/MAC/Documents/Projects/Active/mbl/sandbox/akwaya"))

from internal.domain.scraper import WebCawler

class TestWebCrawler(unittest.IsolatedAsyncioTestCase):

    async def test_concurrency(self):
        """
        Verify that multiple searches run concurrently and are limited by semaphore.
        We mock search_linkedin to take distinct time and check start/end times.
        """
        
        # Mock search functions to simulate delay
        async def mock_search_linkedin(query, batch_size=10):
            print(f"Start search for {query}")
            await asyncio.sleep(1) # Simulate network delay
            print(f"End search for {query}")
            return [{"name": query}]

        async def mock_search_google_places(query, batch_size=10):
             await asyncio.sleep(1)
             return [{"name": query}]

        # Patch the search functions where they are imported in scraper.py
        with patch('internal.domain.scraper.search_linkedin', side_effect=mock_search_linkedin) as mock_sl, \
             patch('internal.domain.scraper.search_google_places', side_effect=mock_search_google_places) as mock_gp, \
             patch('internal.domain.scraper.load_yaml') as mock_load:
            
            # Setup mock yaml data
            mock_load.return_value = {
                "keywords": {
                    "linkedin": ["term1", "term2", "term3", "term4", "term5", "term6"],
                    "google_places": []
                }
            }

            # Create crawler with limit of 2 concurrent requests
            crawler = WebCawler(max_concurrent_requests=2)
            
            start_time = time.time()
            linkedin_results, _ = await crawler.scrape_from_sources("dummy_path")
            end_time = time.time()
            
            duration = end_time - start_time
            print(f"Total duration: {duration:.2f}s")

            # With 6 items and concurrency 2, it should take roughly 3 batches of 1s = 3s.
            # If it was sequential: 6s.
            # If it was fully parallel (unlimited): 1s.
            
            # Allow some buffer for overhead
            self.assertLess(duration, 5.0, "Should be faster than sequential execution")
            self.assertGreater(duration, 2.5, "Should respect semaphore limits (approx 3s)")
            
            self.assertEqual(len(linkedin_results), 6)
            print("Concurrency verification passed!")

if __name__ == "__main__":
    unittest.main()
