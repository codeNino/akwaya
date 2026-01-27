import asyncio
from typing import List, Dict

from internal.domain.common.dto import Prospect, WebsiteScrapingOutput
from internal.domain.common.scoring import filter_high_score_prospects  

from internal.domain.scraper.crawler import WebsiteScraper
from internal.utils.loader import export_to_json, load_json
from internal.domain.brainbox.engine import (
    evaluate_scraped_website
)
from internal.domain.pipeline.helper import merge_prospects_info
    
scraper = WebsiteScraper(
    max_workers=8,
    max_tokens=100,
    enable_semantic_extraction=True,
)

def augment_businesses(businesses: List[Prospect]) -> List[Prospect]:
    if not businesses:
        return []

    high_score = filter_high_score_prospects(businesses)
    if not high_score:
        return []

    websites = [
        b["contact"]["website"]
        for b in high_score
        if b.get("contact", {}).get("website")
    ]
    if not websites:
        return high_score

    scraped = scraper.scrape_many(websites)
    if not scraped:
        return high_score

    evaluated: WebsiteScrapingOutput = asyncio.run(
        evaluate_scraped_website(scraped)
    )

    enriched = [
        info
        for info in evaluated.information
        if info.get("email") or info.get("phone")
    ]
    if not enriched:
        print("no enriched info for prospects")
        return high_score

    return merge_prospects_info(high_score, enriched)


def trigger_leads_information_augmentation(
    sourced_leads_path: str,
    output_path: str,
) -> None:
    prospects: Dict[str, List[Prospect]] = load_json(sourced_leads_path)

    augmented: List[Prospect] = []

    augmented.extend(
        augment_businesses(prospects.get("businesses", []))
    )

    export_to_json(augmented, output_path)





                

                

            
    
    
    
    
    
    
    