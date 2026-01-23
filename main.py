import asyncio
import json
from internal.config.secret import validate_environment
from internal.domain.scraper.sources.parser import normalize_linkedin_url
from internal.domain.scraper.crawler import WebCrawler
from internal.utils.loader import export_to_json
from internal.config.paths_config import (FUNNEL_CONFIG_PATH,
        RAW_PROSPECTIVE_WHITELABELS_PATH,
        RAW_PROSPECTIVE_INDIVIDUALS_PATH, ARTIFACTS_DIR)

validate_environment(
    ["SERPER_API_KEY", "GOOGLE_API_KEY", "OPENAI_KEY", "SCRAPFLY_KEY"]
)
    

web_crawler = WebCrawler()

def main():
    
    with open(RAW_PROSPECTIVE_INDIVIDUALS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        payload = [{"prospect_id": item['prospect_id'], 
        "url" : normalize_linkedin_url(item['source_url'])} for item in data]
        results = asyncio.run(web_crawler.enrich_linkedin_profiles(payload[1:2]))
        export_to_json(results, ARTIFACTS_DIR / "enriched_linkedin_profiles.json")
    
    


if __name__ == "__main__":
    main()
