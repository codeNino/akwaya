from fastapi import (APIRouter, BackgroundTasks)
from fastapi.responses import JSONResponse
from .dto import PipelineRequest
from internal.domain.service import run_leads_acquisition_pipeline

router = APIRouter(prefix="/api/v1")

@router.post("/pipeline")
def pipeline(request: PipelineRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_leads_acquisition_pipeline, request.query)
    return JSONResponse({"message": "Pipeline triggered successfully"})