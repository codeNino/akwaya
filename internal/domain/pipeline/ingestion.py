import asyncio

from internal.domain.scraper.searcher import WebSearcher
from internal.utils.loader import export_to_json, load_yaml
from internal.domain.brainbox.engine import (
    generate_keywords, 
    preprocess_leads, 
)
from internal.config.paths_config import (FUNNEL_CONFIG_PATH)


web_searcher = WebSearcher()

def trigger_leads_sourcing(query: str, output_path: str):

    config_file = load_yaml(FUNNEL_CONFIG_PATH)
    scrape_params = config_file.get("raw_prospect_ingestion").get("scrape")
    batch_size = scrape_params.get("batch_size", 50)
    keywords = generate_keywords(query)
    raw_prospects = asyncio.run(web_searcher.search_for_prospects(keywords, batch_size))
    processed_leads = asyncio.run(preprocess_leads(raw_prospects))
    export_to_json(processed_leads.model_dump(), output_path)
    







                

                

            
    
    
    
    
    
    
    