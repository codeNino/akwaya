from typing import TypedDict, Optional, Literal, List, Any, Dict
from pydantic import BaseModel, Field, field_validator, ValidationInfo
from datetime import datetime
import uuid

from .scoring import calculate_discovery_confidence


class ContactInfoDict(TypedDict, total=False):
    email: Optional[str]
    phone: Optional[str]
    website: Optional[str]


class ProspectDict(TypedDict):
    prospect_id: str
    source_platform: Literal["google_maps", "linkedin"] 
    name: str
    about: str
    contact_info: ContactInfoDict
    location: str
    business_context: Optional[str]
    about: Optional[str]
    source_url: str
    discovery_confidence_score: float  # 0.0 – 1.0
    timestamp: str  # ISO8601


class ContactInfo(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None


class Prospect(BaseModel):
    prospect_id: str = Field(default_factory=lambda: f"temp_{uuid.uuid4()}")
    source_platform: Literal["google_maps", "linkedin"] = "linkedin"
    name: str
    about: Optional[str] = None

    about: str
    contact_info: ContactInfo

    location: str
    business_context: Optional[str] = None
    source_url: str

    discovery_confidence_score: float
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


    @field_validator("timestamp", mode="before")
    @classmethod
    def fix_timestamp(cls, v):
        return datetime.utcnow().isoformat()
    
    @field_validator("prospect_id", mode="before")
    @classmethod
    def fix_prospect_id(cls, v):
        return f"temp_{uuid.uuid4()}"


    @field_validator("discovery_confidence_score", mode="after")
    def fix_discovery_confidence_score(cls, v,info):
        return calculate_discovery_confidence(
            email=info.data.get("contact_info").email,
            phone=info.data.get("contact_info").phone,
            website=info.data.get("contact_info").website,
            location=info.data.get("location"),
            business_type=info.data.get("business_context"),
        )

class ProspectParserOutput(BaseModel):
    prospects: List[Prospect]
