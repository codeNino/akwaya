from pydantic import BaseModel

class PipelineRequest(BaseModel):
    query: str