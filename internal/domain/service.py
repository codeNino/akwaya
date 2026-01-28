from typing import Dict, List
from internal.domain.common.dto import CustomCallAnalysisData

from internal.config.paths_config import ARTIFACTS_DIR
from internal.utils.loader import export_to_json

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



def update_leads_with_feedback(user_id: str, data: CustomCallAnalysisData):
    # export_to_json(data, ARTIFACTS_DIR / f"feedback_about_lead_{user_id}.json")
    pass
    