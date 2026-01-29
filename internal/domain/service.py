from typing import Dict, List, Optional
from internal.domain.common.dto import CustomCallAnalysisData

from internal.utils.database.manager import DatabaseManager

from internal.domain.pipeline.augmentation import trigger_leads_information_augmentation
from internal.domain.pipeline.ingestion import trigger_leads_sourcing
from internal.domain.pipeline.loader import persist_enriched_leads_to_database
from internal.domain.calling.retell_service import make_retell_call

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

    persist_enriched_leads_to_database(
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


def call_prospect(db_manager: DatabaseManager, prospect_id: str):
    prospect_model = db_manager.get_prospect_by_id(prospect_id)
    prospect_model.created_at = prospect_model.created_at.isoformat()
    if not prospect_model:
        raise ValueError(f"Prospect with ID {prospect_id} not found")
    to_be_called_prospect = prospect_model.__dict__.copy()
    to_be_called_prospect.pop('_sa_instance_state', None)
    return make_retell_call(to_be_called_prospect)
