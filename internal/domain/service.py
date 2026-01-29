from typing import Dict, List, Optional
from internal.domain.common.dto import CustomCallAnalysisData

from internal.utils.database.manager import DatabaseManager

from internal.domain.pipeline.augmentation import trigger_leads_information_augmentation
from internal.domain.pipeline.ingestion import trigger_leads_sourcing
from internal.domain.pipeline.loader import persist_enriched_leads_to_database
from internal.domain.calling.retell_service import make_retell_call
from internal.utils.database import get_session

from internal.config.paths_config import (LEADS_SOURCED_PATH, LEADS_AUGMENTED_PATH)

CAMPAIGN_LIMIT = 10

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
    if not prospect_model:
        raise ValueError(f"Prospect with ID {prospect_id} not found")
    return make_retell_call(prospect_model.to_dict())

def run_cold_call_campaign(limit: Optional[int] = None):
    """
    Trigger Retell calls for prospects that have a phone and are not yet called.
    Uses its own DB session (safe for background tasks). Limited to CAMPAIGN_LIMIT (10) calls.
    """
    effective_limit = limit if limit is not None else CAMPAIGN_LIMIT
    effective_limit = min(effective_limit, CAMPAIGN_LIMIT)

    with get_session() as session:
        db_manager = DatabaseManager(session)
        prospects = db_manager.get_prospects_with_phones(limit=effective_limit)

    if not prospects:
        return {"total": 0, "initiated": 0, "failed": 0, "results": []}

    results = []
    initiated = 0
    failed = 0
    for p in prospects:
        out = make_retell_call(p.to_dict())
        results.append(out)
        if out.get("success"):
            initiated += 1
        else:
            failed += 1

    return {
        "total": len(prospects),
        "initiated": initiated,
        "failed": failed,
        "results": results,
    }
