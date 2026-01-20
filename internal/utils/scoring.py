def calculate_discovery_confidence(
    *,
    email: str | None,
    phone: str | None,
    website: str | None,
    location: str | None,
    business_type: str | None,
) -> float:
    """
    Calculate discovery confidence score based on available attributes.
    Score range: 0.0 – 1.0
    """

    score = 0.0

    if email:
        score += 0.3

    if phone:
        score += 0.2

    if website:
        score += 0.2

    if location:
        score += 0.15

    if business_type:
        score += 0.15

    # Safety clamp (future-proof)
    return round(min(score, 1.0), 2)
