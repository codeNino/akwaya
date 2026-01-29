from typing import Dict, List
from internal.domain.common.dto import CustomCallAnalysisData

from internal.utils.database.manager import DatabaseManager

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



def update_leads_with_feedback(db_manager: DatabaseManager, data: CustomCallAnalysisData):
    return db_manager.update_prospect_verification_call(
        data.get("prospect_id"),
        data.get("call_summary"),
        data.get("call_recording_url"),
        data.get("is_qualified_lead"),
        data.get("is_relevant_industry"),
    )
    

def retrieve_qualified_leads(db_manager: DatabaseManager):
    return db_manager.get_qualified_prospects()