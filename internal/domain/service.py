from internal.domain.pipeline.augmentation import trigger_leads_information_augmentation
from internal.domain.pipeline.ingestion import trigger_leads_sourcing
from internal.config.paths_config import (LEADS_SOURCED_PATH, LEADS_AUGMENTED_PATH)


def run_leads_acquisition_pipeline(query: str):

    trigger_leads_sourcing(
        query, 
        LEADS_SOURCED_PATH
    )    

    trigger_leads_information_augmentation(
        LEADS_SOURCED_PATH,
        LEADS_AUGMENTED_PATH
    )    
