import asyncio
from typing import List, Dict

from internal.utils.normalizer import flatten_list
from internal.domain.common.dto import Prospect, WebsiteScrapingOutput, ArticleExtractionOutput
from internal.domain.common.scoring import filter_high_score_prospects  

from internal.domain.scraper.crawler import WebsiteScraper
from internal.domain.scraper.searcher import WebSearcher
from internal.utils.loader import export_to_json, load_json
from internal.domain.brainbox.engine import (
    evaluate_scraped_website,
    extract_leads_from_articles
)
from internal.domain.pipeline.helper import merge_prospects_info
    
scraper = WebsiteScraper(
    max_workers=8,
    max_tokens=100,
    enable_semantic_extraction=True,
)

web_searcher = WebSearcher()

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
        return high_score

    return merge_prospects_info(high_score, enriched)


def augment_from_articles(articles: List[Prospect]) -> List[Prospect]:
    if not articles:
        return []

    websites = [
        b["contact"]["website"]
        for b in articles
        if b.get("contact", {}).get("website")
    ]

    if not websites:
        return []

    scraped = scraper.scrape_many(websites)
    if not scraped:
        return []

    extraction_output: ArticleExtractionOutput = asyncio.run(
        extract_leads_from_articles(scraped)
    )

    business_prospects: List[Prospect] = asyncio.run(
        web_searcher.source_from_google_places(
            len(extraction_output.businesses),
            extraction_output.businesses
        )
    )

    business_prospects = flatten_list(business_prospects)

    leads: List[Prospect] = []

    if extraction_output.businesses:
        business_prospects = augment_businesses(business_prospects)
        leads.extend(business_prospects)

    return leads

def trigger_leads_information_augmentation(
    sourced_leads_path: str,
    output_path: str,
) -> None:
    prospects: Dict[str, List[Prospect]] = load_json(sourced_leads_path)

    augmented: List[Prospect] = []

    augmented.extend(
        augment_businesses(prospects.get("businesses", []))
    )
    augmented.extend(
        augment_from_articles(prospects.get("articles", []))
    )
    export_to_json(augmented, output_path)





                

                

            
    
    
    
    
    
    
    