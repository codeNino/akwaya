from typing import Optional
from pydantic import BaseModel


class PipelineRequest(BaseModel):
    query: str


class CallRequest(BaseModel):
    prospect_id: str


class ColdCallCampaignRequest(BaseModel):
    """Optional limit (max 10). Omit = use default of 10."""
    limit: Optional[int] = None