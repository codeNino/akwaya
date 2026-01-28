"""
Loader script to insert deduplication results into PostgreSQL database using SQLAlchemy
"""

import json
import uuid
from typing import Dict, List, TypedDict
from datetime import datetime
import sys
from pathlib import Path

_current = Path(__file__).resolve()
for parent in _current.parents:
    if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
        project_root = parent
        break
else:
    project_root = _current.parents[3]

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
from internal.utils.logger import AppLogger
from internal.config.paths_config import (
    LEADS_AUGMENTED_PATH,
    DB_MODELS_TEMP_DIR,
    ENRICHMENT_RESULTS_PATH,
)
from internal.utils.normalizer import normalize_url
from internal.utils.database.models import Prospect
from internal.domain.pipeline.helper import filter_and_prepare_leads
logger = AppLogger("domain.deduplicator.loader")()




def save_model_json(
    model_instance, model_type: str, model_id: str, output_dir: Path
) -> Path:
    """
    Save model JSON representation to temporary file

    Args:
        model_instance: Model instance with to_dict() method
        model_type: Type of model ('prospect', 'prospect_source', 'raw_snapshot')
        model_id: Unique identifier for the model
        output_dir: Directory to save JSON files

    Returns:
        Path to saved JSON file
    """
    model_dir = output_dir / model_type
    model_dir.mkdir(parents=True, exist_ok=True)

    json_path = model_dir / f"{model_id}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            model_instance.to_dict(), f, indent=2, ensure_ascii=False, default=str
        )

    logger.debug("Saved %s JSON to %s", model_type, json_path)
    return json_path


def save_enriched_results_as_json(
    results_file_path: str, raw_prospects_path: str = None, output_dir: Path = None
) -> Dict:
    """
    Save enrichment results as JSON files without inserting into database

    """
    if output_dir is None:
        output_dir = DB_MODELS_TEMP_DIR

    if raw_prospects_path is None:
        raw_prospects_path = str(LEADS_AUGMENTED_PATH)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Saving model JSONs to %s", output_dir)

    logger.info("Loading enrichment results from %s", results_file_path)
    with open(results_file_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    prospects:List[Prospect] = results
    logger.info("Processing %d prospects", len(prospects))

    for prospect in prospects:
        try:
            prepared_lead = filter_and_prepare_leads(prospect)
            # log prepared lead
            logger.info("Prepared lead: %s", prepared_lead)
            # contact = prospect["contact"]
            
            prospect_id = str(uuid.uuid4())
            prepared_lead["prospect_id"] = prospect_id
            # Prepare data for models
            contact = prepared_lead.get("contact", {})  
            location = prepared_lead.get("location", {})
            
            # Extract contact info 
            email = contact.get("email")
            phone = contact.get("phone")
            website = contact.get("website")
            
            # Convert to strings (handle None values)
            emails = email if email else None
            phones = phone if phone else None
            websites = website if website else None
            
            country = location.get("country", None)
            country_acronym = location.get("country_acronym", None)
            address = location.get("address", None)
            
            # Set created_at timestamp
            created_at = datetime.utcnow()

            prospect = Prospect(
                prospect_id=prospect_id,
                name=prepared_lead.get("name", ""),
                about=prepared_lead.get("about", None),
                platforms=prepared_lead.get("source_platform"),
                emails=emails,
                phones=phones,
                websites=websites,
                country=country,
                country_acronym=country_acronym,
                address=address,
                business_context=prepared_lead.get("business_context", None),
                has_phone=prepared_lead.get("has_phone", False),
                has_email=prepared_lead.get("has_email", False),
                created_at=created_at,
            )

            # Save prospect JSON
            save_model_json(prospect, "prospect", prospect_id, output_dir)

        except Exception as e:
            # error_msg = f"Error processing prospect {prospect_id}: {str(e)}"
            # logger.error(error_msg)
            logger.error(f"Error processing prospect: {str(e)}")

def save_enriched_results_as_database(
    results_file_path: str, raw_prospects_path: str = None, output_dir: Path = None
) -> Dict:
    """
    Save enrichment results as database records
    """
    from internal.utils.database import get_session, init_db
    
    if raw_prospects_path is None:
        raw_prospects_path = str(LEADS_AUGMENTED_PATH)

    # Initialize database tables
    logger.info("Initializing database tables...")
    init_db(drop_existing=False)

    with open(results_file_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    prospects: List[Dict] = results
    logger.info("Processing %d prospects for database insertion", len(prospects))

    stats = {
        "prospects_inserted": 0,
        "errors": []
    }

    with get_session() as session:
        for prospect in prospects:
            try:
                prepared_lead = filter_and_prepare_leads(prospect)
                
                # Skip if filter_and_prepare_leads returns None (no phone/email)
                if not prepared_lead:
                    continue

                prospect_id = str(uuid.uuid4())
                prepared_lead["prospect_id"] = prospect_id
                
                # Prepare data for models
                contact = prepared_lead.get("contact", {})  
                location = prepared_lead.get("location", {})
                
                # Extract contact info - filter_and_prepare_leads returns email/phone (singular)
                email = contact.get("email")
                phone = contact.get("phone")
                website = contact.get("website")
                
                # Convert to strings (handle None values)
                emails = email if email else None
                phones = phone if phone else None
                websites = website if website else None
                
                country = location.get("country", None)
                country_acronym = location.get("country_acronym", None)
                address = location.get("address", None)
                
                # Set created_at timestamp
                created_at = datetime.utcnow()

                # Check if prospect already exists
                existing = session.query(Prospect).filter(
                    Prospect.prospect_id == prospect_id
                ).first()
                
                if existing:
                    # Update existing prospect
                    existing.name = prepared_lead.get("name", "")
                    existing.about = prepared_lead.get("about", None)
                    existing.platforms = prepared_lead.get("source_platform")
                    existing.emails = emails
                    existing.phones = phones
                    existing.websites = websites
                    existing.country = country
                    existing.country_acronym = country_acronym
                    existing.address = address
                    existing.business_context = prepared_lead.get("business_context", None)
                    existing.has_phone = prepared_lead.get("has_phone", False)
                    existing.has_email = prepared_lead.get("has_email", False)
                    logger.debug("Updated prospect %s", prospect_id)
                else:
                    # Create new prospect
                    db_prospect = Prospect(
                        prospect_id=prospect_id,
                        name=prepared_lead.get("name", ""),
                        about=prepared_lead.get("about", None),
                        platforms=prepared_lead.get("source_platform"),
                        emails=emails,
                        phones=phones,
                        websites=websites,
                        country=country,
                        country_acronym=country_acronym,
                        address=address,
                        business_context=prepared_lead.get("business_context", None),
                        has_phone=prepared_lead.get("has_phone", False),
                        has_email=prepared_lead.get("has_email", False),
                        created_at=created_at,
                    )
                    session.add(db_prospect)
                    logger.debug("Created prospect %s", prospect_id)
                
                stats["prospects_inserted"] += 1

            except Exception as e:
                error_msg = f"Error processing prospect: {str(e)}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)
        
        # Commit all changes
        session.commit()
    
    logger.info(
        "Database save complete: %d prospects inserted, %d errors",
        stats["prospects_inserted"],
        len(stats["errors"])
    )
    
    if stats["errors"]:
        logger.warning("Encountered %d errors during database save", len(stats["errors"]))
    
    return stats

def main():
    """Main entry point for loading deduplication results"""
    results_path = LEADS_AUGMENTED_PATH
    save_enriched_results_as_json(str(results_path))

if __name__ == "__main__":
    main()
