from typing import List
from .dto import Prospect

def calculate_points(prospect: Prospect) -> float:
    contact = prospect.get("contact", {})

    has_contact = any(
        contact.get(field)
        for field in ("email", "phone", "website")
    )
    if not has_contact:
        return 0.0

    score = 0.0

    if contact.get("email"):
        score += 0.2
    if contact.get("phone"):
        score += 0.2
    if contact.get("website"):
        score += 0.3
    if prospect.get("location", {}).get("country"):
        score += 0.10
    if prospect.get("business_context"):
        score += 0.10
    if prospect.get("about"):
        score += 0.10

    return score



def filter_high_score_prospects(prospects: List[Prospect], threshold: float = 0.3) -> List[Prospect]:
    filtered = []
    for prospect in prospects:
        score = calculate_points(prospect)
        if score >= threshold:
            filtered.append(prospect)
    return filtered
