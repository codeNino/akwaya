from fastapi import (APIRouter, BackgroundTasks, Depends, Request)
from fastapi.responses import JSONResponse
from .dto import PipelineRequest
from sqlalchemy.orm import Session


from internal.utils.database.session import inject_session
from internal.utils.database.manager import DatabaseManager

from internal.domain.service import (
    run_leads_acquisition_pipeline,
    update_leads_with_feedback
)
from internal.utils.logger import AppLogger

controller_logger = AppLogger("server.controller")()

router = APIRouter(prefix="/api/v1")

@router.post("/leads/pipeline")
def acquisition_pipeline(request: PipelineRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_leads_acquisition_pipeline, request.query)
    return JSONResponse({"message": "Pipeline triggered successfully"})

@router.post("/webhook/retell_feedback")
async def retell_cold_call_feedback(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(inject_session)):
    try:
        payload = await request.json()
        controller_logger.info(f"Received feedback from cold call :: {payload.get('event')}")
        if payload.get("event") == "call_analyzed":
            prospect_id = payload.get("call", {}).get("metadata", {}).get("prospect_id")
            if not prospect_id:
                controller_logger.info("No prospect_id found in payload")
                return JSONResponse({"message": "No prospect_id found in call metadata"})
            call_summary = payload.get("call", {}).get("call_analysis", {}).get("call_summary", "")
            call_recording_url = payload.get("call", {}).get("recording_url", "")
            custom_analysis_data = payload.get("call", {}).get("call_analysis", {}).get("custom_analysis", {})
            background_tasks.add_task(update_leads_with_feedback,
            DatabaseManager(db),
            {
                "prospect_id": prospect_id,
                "call_summary": call_summary,
                "call_recording_url": call_recording_url,
                "is_qualified_lead": custom_analysis_data.get("qualified_lead", False),
                "is_relevant_industry": custom_analysis_data.get("relevant_industry", False),
            })
        return JSONResponse({"message": "Feedback Received"})
    except Exception as e:
        controller_logger.error(f"Error processing feedback from cold call: {e}")
        return JSONResponse({"message": "Error processing feedback from cold call"})
