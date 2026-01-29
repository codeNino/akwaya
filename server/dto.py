from pydantic import BaseModel

class PipelineRequest(BaseModel):
    query: str

class CallRequest(BaseModel):
    prospect_id: str  