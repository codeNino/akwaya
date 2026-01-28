from typing import List
from internal.domain.common.dto import Prospect, WebsiteInfo
from internal.utils.normalizer import normalize_url, normalize_phone, normalize_email, EMAIL_REGEX

def merge_prospects_info(
    prospects: List[Prospect],
    augmentation_info: List[WebsiteInfo],
) -> List[Prospect]:

    augmented_prospects: List[Prospect] = []

    augmentation_index = {
        normalize_url(item["url"]) : item
        for item in augmentation_info
        if item.get("url")
    }

    for item in prospects:
        url = item.get("contact", {}).get("website")
        if not url:
            continue
        url = normalize_url(url)
        if url not in augmentation_index:
            continue

        source = augmentation_index[url]

        for key, value in source.items():
            if key == "url":
                continue

            if key == "about" and not item.get("about"):
                item[key] = value
            
            if key == "email" and not item.get("contact", {}).get("email"):
                item["contact"]["email"] = value

            if key == "phone" and not item.get("contact", {}).get("phone"):
                item["contact"]["phone"] = value
        augmented_prospects.append(item)

    return augmented_prospects

def filter_and_prepare_leads(lead: Prospect) -> Prospect:

    contact = lead.get("contact", {})
    location = lead.get("location", {})

    raw_email = contact.get("email")
    raw_phone = contact.get("phone")
    country = location.get("country_acronym")

    email = normalize_email(raw_email)
    phone = normalize_phone(raw_phone, country)

    has_email = bool(email)
    has_phone = bool(phone)

    if not has_email and not has_phone:
        return None

    prepared_lead = {
        **lead,
        "contact": {
            **contact,
            "email": email,
            "phone": phone
        },
        "has_phone": has_phone,
        "has_email": has_email
    }

    return prepared_lead
