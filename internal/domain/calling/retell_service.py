"""
Retell phone calling service for prospects
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

_current = Path(__file__).resolve()
for parent in _current.parents:
    if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
        project_root = parent
        break
else:
    project_root = _current.parents[3]

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import json

from retell import Retell
from internal.utils.logger import AppLogger
from internal.utils.database import get_session
from internal.utils.database.models import Prospect
from internal.config.secret import SecretManager
from internal.config.paths_config import DB_MODELS_TEMP_DIR

logger = AppLogger("domain.calling.retell_service")()


# Initialize Retell client
retell_client = Retell(api_key=SecretManager.RETELL_API_KEY)


def get_prospects_with_phones_from_files(
    prospects_dir: Optional[Path] = None, limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get prospect phone numbers from JSON files in db_models_temp directory

    Args:
        prospects_dir: Directory containing prospect JSON files (defaults to DB_MODELS_TEMP_DIR/prospect)
        limit: Optional limit on number of prospects to return

    Returns:
        List of prospect dictionaries with phone numbers
    """
    if prospects_dir is None:
        prospects_dir = DB_MODELS_TEMP_DIR / "prospect"

    if not prospects_dir.exists():
        logger.warning("Prospects directory does not exist: %s", prospects_dir)
        return []

    logger.info("Reading prospect phone numbers from %s", prospects_dir)

    prospects = []
    json_files = list(prospects_dir.glob("*.json"))

    if not json_files:
        logger.warning("No JSON files found in %s", prospects_dir)
        return []

    logger.info("Found %d prospect JSON files", len(json_files))

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                prospect_data = json.load(f)

            # Check if prospect has phone number
            phone = prospect_data.get("phones")
            has_phone = prospect_data.get("has_phone", False)

            # Only include prospects with valid phone numbers
            if has_phone and phone and phone.strip() and phone.lower() != "null":
                prospects.append(prospect_data)

                # Apply limit if specified
                if limit and len(prospects) >= limit:
                    break

        except Exception as e:
            logger.error("Error reading prospect file %s: %s", json_file, e)
            continue

    logger.info("Loaded %d prospects with phone numbers from files", len(prospects))
    return prospects


def get_prospects_with_phones(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Query database for prospects with phone numbers

    Args:
        limit: Optional limit on number of prospects to return

    Returns:
        List of prospect dictionaries with phone numbers
    """
    logger.info("Querying database for prospects with phone numbers")

    prospects = []
    with get_session() as session:
        query = (
            session.query(Prospect)
            .filter(Prospect.has_phone == True)
            .filter(Prospect.phones.isnot(None))
            .filter(Prospect.phones != "")
        )

        if limit:
            query = query.limit(limit)

        db_prospects = query.all()

        for prospect in db_prospects:
            prospect_dict = prospect.to_dict()
            prospects.append(prospect_dict)

    logger.info("Found %d prospects with phone numbers", len(prospects))
    return prospects


def format_phone_number(phone: str) -> str:
    """
    Format phone number for Retell API (E.164 format: +1234567890)

    Args:
        phone: Phone number string

    Returns:
        Formatted phone number
    """
    if not phone:
        return ""

    # Remove all non-digit characters except +
    cleaned = "".join(c for c in phone if c.isdigit() or c == "+")

    # If doesn't start with +, add it
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned

    return cleaned


def make_retell_call(
    prospect: Dict[str, Any],
    from_number: Optional[str] = None,
    agent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Make a Retell phone call to a prospect

    Args:
        prospect: Prospect dictionary with phone number and other data
        from_number: Phone number to call from (defaults to RETELL_FROM_NUMBER)
        agent_id: Optional Retell agent ID

    Returns:
        Dictionary with call response or error information
    """
    if not from_number:
        from_number = SecretManager.RETELL_FROM_NUMBER

    if not from_number:
        error_msg = "No from_number provided and RETELL_FROM_NUMBER not set"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "prospect_id": prospect.get("prospect_id"),
        }

    phone = prospect.get("phones")
    if not phone:
        error_msg = f"Prospect {prospect.get('prospect_id')} has no phone number"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "prospect_id": prospect.get("prospect_id"),
        }

    # Format phone number
    to_number = format_phone_number(phone)

    if not to_number:
        error_msg = f"Invalid phone number format: {phone}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "prospect_id": prospect.get("prospect_id"),
        }

    try:
        logger.info(
            "Initiating call to prospect %s (%s) from %s",
            prospect.get("name"),
            to_number,
            from_number,
        )

        # Prepare call parameters
        # Note: agent_id is not a parameter for create_phone_call()
        # It should be configured in the Retell dashboard or passed via other means
        call_params = {
            "from_number": from_number,
            "to_number": to_number,
        }

        # Add custom data with prospect information
        call_params["retell_llm_dynamic_variables"] = {
            "prospect_name": prospect.get("name"),
            "business_context": prospect.get("business_context"),
            "about": prospect.get("about"),
            "country": prospect.get("country"),
            "platforms": prospect.get("platforms"),
            "date_time": prospect.get("created_at"),
        }
        
        # If agent_id is provided, log it but don't pass it to create_phone_call
        # The agent_id should be configured in your Retell account settings
        if agent_id:
            logger.info("Agent ID provided: %s (not passed to API, configure in Retell dashboard)", agent_id)

        # Make the call
        phone_call_response = retell_client.call.create_phone_call(**call_params)

        logger.info(
            "Call initiated successfully. Call ID: %s, Agent ID: %s",
            getattr(phone_call_response, "call_id", "unknown"),
            getattr(phone_call_response, "agent_id", "unknown"),
        )

        return {
            "success": True,
            "call_id": getattr(phone_call_response, "call_id", None),
            "agent_id": getattr(phone_call_response, "agent_id", None),
            "prospect_id": prospect.get("prospect_id"),
            "prospect_name": prospect.get("name"),
            "to_number": to_number,
            "from_number": from_number,
            "response": phone_call_response,
        }

    except Exception as e:
        error_msg = f"Error making Retell call to {to_number}: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "prospect_id": prospect.get("prospect_id"),
            "to_number": to_number,
        }


def call_prospects_with_phones(
    limit: Optional[int] = None,
    from_number: Optional[str] = None,
    agent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get prospects with phone numbers and initiate Retell calls

    Args:
        limit: Optional limit on number of prospects to call
        from_number: Phone number to call from
        agent_id: Optional Retell agent ID

    Returns:
        Dictionary with calling statistics and results
    """
    logger.info("Starting phone calling campaign for prospects with phone numbers")

    # Get prospects with phone numbers
    # prospects = get_prospects_with_phones(limit=limit)
    prospects = get_prospects_with_phones_from_files(limit=limit)

    if not prospects:
        logger.warning("No prospects with phone numbers found")
        return {
            "total_prospects": 0,
            "calls_initiated": 0,
            "calls_failed": 0,
            "results": [],
        }

    stats = {
        "total_prospects": len(prospects),
        "calls_initiated": 0,
        "calls_failed": 0,
        "results": [],
    }

    # Make calls to each prospect
    for prospect in prospects:
        result = make_retell_call(
            prospect=prospect, from_number=from_number, agent_id=agent_id
        )

        stats["results"].append(result)

        if result.get("success"):
            stats["calls_initiated"] += 1
        else:
            stats["calls_failed"] += 1

    logger.info(
        "Calling campaign complete: %d calls initiated, %d failed out of %d prospects",
        stats["calls_initiated"],
        stats["calls_failed"],
        stats["total_prospects"],
    )

    return stats


if __name__ == "__main__":
    # Example usage
    import json

    # Get prospects with phones
    prospects = get_prospects_with_phones_from_files(limit=5)
    print(f"\nFound {len(prospects)} prospects with phone numbers")

    # Make calls (uncomment to actually make calls)
    results = call_prospects_with_phones(
        limit=5,
        from_number=SecretManager.RETELL_FROM_NUMBER,
        agent_id=SecretManager.RETELL_AGENT_ID,
    )
    print("\n" + "=" * 80)
    print("CALLING CAMPAIGN RESULTS")
    print("=" * 80)
    print(f"Total prospects: {results['total_prospects']}")
    print(f"Calls initiated: {results['calls_initiated']}")
    print(f"Calls failed: {results['calls_failed']}")

    print("\nCall Results:")
    for result in results["results"]:
        if result["success"]:
            print(
                f"✓ {result['prospect_name']}: Call ID {result.get('call_id', 'N/A')}"
            )
        else:
            print(
                f"✗ {result.get('prospect_name', 'Unknown')}: {result.get('error', 'Unknown error')}"
            )
