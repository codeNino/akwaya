from internal.domain.common.dto import Prospect
from typing import List, Dict, Tuple, Optional

def extract_country(address_components: List[Dict]) -> Tuple[Optional[str], Optional[str]]:
    for component in address_components or []:
        if "country" in component.get("types", []):
            return component.get("longText"), component.get("shortText")
    return None, None

def extract_important_google_places_info(places: List[Dict]) -> List[Prospect]:
    def safe_get(obj, *keys):
        for key in keys:
            obj = obj.get(key, {})
        return obj if obj else None

    important_data = []

    for place in places:
        country, country_code = extract_country(place.get("addressComponents", []))
        extracted = {
            "source_platform": "google_places",
            "name":safe_get(place, "displayName", "text"),
            "contact": {
                "phone": place.get("nationalPhoneNumber"),
                "website": place.get("websiteUri"),
            },
            "location": {
                "address": place.get("shortFormattedAddress"),
                "country_code": country_code,
                "country": country,
            },
            "business_context": place.get("primaryType"),
        }
        important_data.append(extracted)

    return important_data