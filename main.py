import asyncio

from internal.config.secret import validate_environment
from internal.domain.scraper import WebCawler
from internal.config.paths_config import (FUNNEL_CONFIG_PATH,
        RAW_PROSPECTIVE_WHITELABELS_PATH,
        RAW_PROSPECTIVE_INDIVIDUALS_PATH)

validate_environment(
    ["SERPER_API_KEY", "GOOGLE_API_KEY", "OPENAI_KEY"]
)
    

web_cawler = WebCawler()

def main():
    results = asyncio.run(web_cawler.search_for_prospects(FUNNEL_CONFIG_PATH))
    WebCawler.flatten_to_json(results.get("whitelabels", []), RAW_PROSPECTIVE_WHITELABELS_PATH)
    WebCawler.flatten_to_json(results.get("individuals", []), RAW_PROSPECTIVE_INDIVIDUALS_PATH)


if __name__ == "__main__":
    main()
