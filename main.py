import asyncio

from internal.domain.scraper import WebCawler
from internal.config.paths_config import (FUNNEL_CONFIG_PATH,
        RAW_PROSPECTIVE_WHITELABELS_PATH,
        RAW_PROSPECTIVE_INDIVIDUALS_PATH)

web_cawler = WebCawler()

def main():
    results = asyncio.run(web_cawler.search_for_prospects(FUNNEL_CONFIG_PATH))
    WebCawler.flatten_to_json(results.get("whitelabels", []), RAW_PROSPECTIVE_WHITELABELS_PATH)
    WebCawler.flatten_to_json(results.get("individuals", []), RAW_PROSPECTIVE_INDIVIDUALS_PATH)


if __name__ == "__main__":
    main()
