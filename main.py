import asyncio

from internal.domain.scraper import WebCawler
from internal.config.paths_config import (SEARCH_CONFIG_PATH,
        RAW_NORMALIZED_PROSPECT_PATH)

web_cawler = WebCawler()

def main():
    linkedin_results, google_places_results = asyncio.run(web_cawler.scrape_from_sources(SEARCH_CONFIG_PATH))
    aggregated_results = linkedin_results + google_places_results
    WebCawler.flatten_to_json(aggregated_results, RAW_NORMALIZED_PROSPECT_PATH)


if __name__ == "__main__":
    main()
