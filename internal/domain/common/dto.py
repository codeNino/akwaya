from typing import Optional, Literal, List, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field, field_validator

class LocationInfo(TypedDict, total=False):
    country: Optional[str]
    country_acronym: Optional[str]
    address: Optional[str]

class ContactInfo(TypedDict, total=False):
    email: Optional[str]
    phone: Optional[str]
    website: Optional[str]

class Prospect(TypedDict):
    source_platform: Literal["google_places", "google_search"] 
    name: str
    about: Optional[str]
    contact: ContactInfo
    location: LocationInfo
    business_context: Optional[str]


class KeywordGenerationOutput(BaseModel):
    keywords: List[str] = Field(..., description="List of keywords")

    @field_validator("keywords")
    @classmethod
    def keywords_must_not_be_empty(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("keywords must not be empty")
        return v

class LeadsPreprocessingOutput(BaseModel):
    individuals: List[Prospect] = Field(..., description="List of valid individual leads")
    businesses: List[Prospect] = Field(..., description="List of valid business leads")
    articles: List[Prospect] = Field(..., description="List of valid article leads  ")

    class Config:
        extra = "forbid"



class WebsiteInfo(TypedDict, total=False):
    url: str
    email: Optional[str]
    phone: Optional[str]
    about: Optional[str]


class WebsiteScrapingOutput(BaseModel):
   information: List[WebsiteInfo] = Field(..., description="List of valid website information")

   class Config:
        extra = "forbid"