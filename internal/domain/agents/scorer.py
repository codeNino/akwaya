"""
Scoring system for prospects (points-based and LLM-based)
"""

import json
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from internal.config.secret import SecretManager
from internal.utils.logger import AppLogger
from internal.utils.prompt import scoring_prompt

logger = AppLogger("domain.agents.scorer")()


# Initialize LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=SecretManager.OPENAI_KEY,
)


def _format_location(location: Any) -> str:
    """Format location object or string to a readable string"""
    if not location:
        return "N/A"
    if isinstance(location, dict):
        # New format: {full_address, city, country}
        parts = []
        if location.get("city"):
            parts.append(location["city"])
        if location.get("country"):
            parts.append(location["country"])
        if location.get("full_address"):
            return location["full_address"]
        return ", ".join(parts) if parts else "N/A"
    return str(location)


async def calculate_llm_score(prospect: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate LLM-based score for a prospect
    
    Args:
        prospect: Prospect dictionary (new format from database)
        
    Returns:
        Dict with prospect_id, llm_score, and reasoning
    """
    try:
        # Extract contact info from arrays
        emails = prospect.get("emails", [])
        phones = prospect.get("phones", [])
        websites = prospect.get("websites", [])
        
        email = emails[0] if emails else "N/A"
        phone = phones[0] if phones else "N/A"
        website = websites[0] if websites else "N/A"
        
        # Format location
        location_str = _format_location(prospect.get("location"))
        
        # Get about (can be null)
        about = prospect.get("about") or "N/A"
        
        # Get source URL from profile_urls
        profile_urls = prospect.get("profile_urls", {})
        source_url = profile_urls.get("linkedin") or profile_urls.get("google_maps") or "N/A"
        
        # Get discovery confidence (new field name)
        discovery_confidence = prospect.get("discovery_confidence", 0.0)
        
        # Business context - try to infer from name/platforms if not present
        business_context = "N/A"
        platforms = prospect.get("platforms", [])
        if platforms:
            business_context = f"Platforms: {', '.join(platforms)}"
        
        prompt = scoring_prompt.format_messages(
            name=prospect.get("name", "Unknown"),
            about=about,
            business_context=business_context,
            location=location_str,
            email=email,
            phone=phone,
            website=website,
            source_url=source_url,
            discovery_confidence=discovery_confidence
        )
        
        response = await llm.ainvoke(prompt)
        content = response.content.strip()

        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        result = json.loads(content)
        
        return {
            "prospect_id": prospect["prospect_id"],
            "llm_score": float(result.get("llm_score", 0.0)),
            "reasoning": result.get("reasoning", "No reasoning provided")
        }
    except Exception as e:
        logger.error(f"Error calculating LLM score for {prospect.get('prospect_id')}: {e}")
        return {
            "prospect_id": prospect["prospect_id"],
            "llm_score": 0.0,
            "reasoning": f"Error: {str(e)}"
        }


def calculate_points_score(prospect: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate points-based score for a prospect
    
    Args:
        prospect: Prospect dictionary (new format from database)
        
    Returns:
        Dict with prospect_id, points_score, and breakdown
    """
    points = 0.0
    max_points = 100.0
    breakdown = {}
    
    # Contact information from arrays (40 points max)
    emails = prospect.get("emails", [])
    phones = prospect.get("phones", [])
    websites = prospect.get("websites", [])
    
    if emails:
        points += 15
        breakdown["email"] = 15
    if phones:
        points += 10
        breakdown["phone"] = 10
    if websites:
        points += 15
        breakdown["website"] = 15
    
    # Location (10 points max) - check if location exists
    location = prospect.get("location")
    if location:
        # Can be dict or string
        if isinstance(location, dict):
            if location.get("full_address") or location.get("city"):
                points += 10
                breakdown["location"] = 10
        else:
            points += 10
            breakdown["location"] = 10
    
    # Business context - infer from platforms/name (20 points max)
    platforms = prospect.get("platforms", [])
    if platforms:
        # More platforms = more points
        if len(platforms) >= 2:
            points += 20
            breakdown["platforms"] = 20
        else:
            points += 15
            breakdown["platforms"] = 15
    
    # About section quality (20 points max)
    about = prospect.get("about")
    if about:
        quality_indicators = [
            "experience", "years", "expert", "professional", "trader",
            "CFA", "CMT", "certified", "specialist", "analyst"
        ]
        found_indicators = sum(1 for indicator in quality_indicators if indicator.lower() in about.lower())
        
        if found_indicators >= 3:
            points += 20
            breakdown["about_quality"] = 20
        elif found_indicators >= 2:
            points += 15
            breakdown["about_quality"] = 15
        elif found_indicators >= 1:
            points += 10
            breakdown["about_quality"] = 10
        else:
            points += 5
            breakdown["about_quality"] = 5
    
    # Discovery confidence (10 points max) - new field name
    discovery_confidence = prospect.get("discovery_confidence", 0.0)
    points += discovery_confidence * 10
    breakdown["discovery_confidence"] = discovery_confidence * 10
    
    # Normalize to 0.0-1.0 scale
    normalized_score = min(points / max_points, 1.0)
    
    return {
        "prospect_id": prospect["prospect_id"],
        "points_score": round(normalized_score, 3),
        "raw_points": round(points, 2),
        "breakdown": breakdown
    }
