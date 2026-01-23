from .dto import (ProspectParserOutput,ProspectDict)
from typing import List, Dict
from datetime import datetime
from internal.config.secret import SecretManager
import uuid


from urllib.parse import urlparse, urlunparse

from langchain_openai import ChatOpenAI
from .prompt import parser_prompt
from .scoring import calculate_discovery_confidence


llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0,
    api_key=SecretManager.OPENAI_KEY,
)


def extract_important_google_places_info(places: List[Dict]) -> List[ProspectDict]:
    def safe_get(obj, *keys):
        for key in keys:
            obj = obj.get(key, {})
        return obj if obj else None

    important_data = []

    for place in places:
        extracted = {
            "prospect_id": f"temp_{uuid.uuid4()}",
            "source_platform": "google_maps",
            "name":safe_get(place, "displayName", "text"),
            "contact_info": {
                "phone": place.get("nationalPhoneNumber"),
                "website": place.get("websiteUri"),
            },
            "location": place.get("shortFormattedAddress"),
            "business_context": place.get("primaryType"),
            "source_url": place.get("googleMapsUri"),
            "discovery_confidence_score": calculate_discovery_confidence(
                email=place.get("email"),
                phone=place.get("nationalPhoneNumber"),
                website=place.get("websiteUri"),
                location=place.get("shortFormattedAddress"),
                business_type=place.get("primaryType"),
            ),
            "timestamp": datetime.now().isoformat(),
        }
        important_data.append(extracted)

    return important_data


def normalize_linkedin_url(url: str) -> str:
    parsed = urlparse(url)

    if parsed.netloc.endswith("linkedin.com"):
        parts = parsed.netloc.split(".")
        # Replace subdomain with 'www'
        parsed = parsed._replace(netloc="www.linkedin.com")

    return urlunparse(parsed)



def extract_linkedin_profiles(
    cse_results: List[Dict]
) -> List[ProspectDict]:
    """
    Takes a list of Google CSE LinkedIn results and returns
    a list of normalized LinkedIn profiles using one LLM call.
    """

    chain = parser_prompt | llm.with_structured_output(ProspectParserOutput)

    response = chain.invoke({
        "results": cse_results
    })

    return response.model_dump()["prospects"]