"""
Loader script to insert deduplication results into PostgreSQL database using SQLAlchemy
"""

import json
import uuid
from typing import Dict, List, Optional, TypedDict
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
)

from sqlalchemy import or_
from sqlalchemy.orm import Session

from internal.utils.database.models import Prospect
from internal.domain.pipeline.helper import filter_and_prepare_leads
from internal.utils.database import get_session, init_db

logger = AppLogger("domain.pipeline.loader")()

def write_model_to_json(
    model_instance, model_type: str, model_id: str, output_dir: Path
) -> Path:
    """
    Write a single model instance to a JSON file (for debugging/verification).

    Args:
        model_instance: Model instance with to_dict() method
        model_type: Type of model ('prospect')
        model_id: Unique identifier for the model
        output_dir: Directory to write JSON files into

    Returns:
        Path to the written JSON file
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


def export_enriched_leads_to_json(
    results_file_path: str, raw_prospects_path: str = None, output_dir: Path = None
) -> Dict:
    """
    Load enriched leads from a results file and write each prospect as a JSON file
    (no database insertion). Used for verification and debugging.
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
            if not prepared_lead:
                logger.debug(
                    "Skipping prospect (no phone/email): %s",
                    prospect.get("name", "unknown"),
                )
                continue

            prospect_id = str(uuid.uuid4())
            prepared_lead["prospect_id"] = prospect_id
            contact = prepared_lead.get("contact", {})  
            location = prepared_lead.get("location", {})
            email = contact.get("email")
            phone = contact.get("phone")
            website = contact.get("website")
            emails = email if email else None
            phones = phone if phone else None
            websites = website if website else None
            
            country = location.get("country", None)
            country_acronym = location.get("country_acronym") or location.get("country_code")
            address = location.get("address", None)

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

            write_model_to_json(prospect, "prospect", prospect_id, output_dir)

        except Exception as e:
            logger.error(f"Error processing prospect: {str(e)}")

def find_existing_prospect(
    phones: Optional[str] = None,
    emails: Optional[str] = None,
    name: Optional[str] = None,
    session: Optional[Session] = None,
) -> Optional[Prospect]:
    """
    Check if a prospect already exists by phone, email, or name (OR logic).
    Returns the existing Prospect if found, else None.

    Args:
        phones: Normalized phone string (e.g. +234...).
        emails: Normalized email string.
        name: Prospect name (trimmed).
        session: Optional DB session. If None, opens and closes one.

    Returns:
        Existing Prospect instance or None.
    """
    conditions = []
    if phones:
        conditions.append(Prospect.phones == phones)
    if emails:
        conditions.append(Prospect.emails == emails)
    if name:
        conditions.append(Prospect.name == name)
    if not conditions:
        return None

    def query(sess: Session) -> Optional[Prospect]:
        return sess.query(Prospect).filter(or_(*conditions)).first()

    if session is not None:
        return query(session)
    with get_session() as sess:
        return query(sess)

def persist_enriched_leads_to_database(
    results_file_path: str, raw_prospects_path: str = None
) -> Dict:
    """
    Load enriched leads from a results file and insert them into the database.
    Uses the same data preparation as export_enriched_leads_to_json.
    """

    if raw_prospects_path is None:
        raw_prospects_path = str(LEADS_AUGMENTED_PATH)

    logger.info("Initializing database tables...")
    init_db(drop_existing=False)

    logger.info("Loading enrichment results from %s", results_file_path)
    with open(results_file_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    prospects: List[Dict] = results
    logger.info("Processing %d prospects for database insertion", len(prospects))

    stats: Dict = {
        "prospects_inserted": 0,
        "skipped_duplicates": 0,
        "errors": [],
    }

    with get_session() as session:
        for prospect in prospects:
            try:
                prepared_lead = filter_and_prepare_leads(prospect)
                if not prepared_lead:
                    continue

                contact = prepared_lead.get("contact", {})
                location = prepared_lead.get("location", {})

                email = contact.get("email")
                phone = contact.get("phone")
                website = contact.get("website")

                emails = email if email else None
                phones = phone if phone else None
                websites = website if website else None

                name = prepared_lead.get("name", "").strip()

                existing = find_existing_prospect(
                    phones=phones,
                    emails=emails,
                    name=name,
                    session=session,
                )
                if existing:
                    stats["skipped_duplicates"] += 1
                    logger.debug(
                        "Skipping duplicate: %s (existing prospect_id=%s)",
                        name or phones or emails,
                        existing.prospect_id,
                    )
                    continue

                prospect_id = str(uuid.uuid4())
                prepared_lead["prospect_id"] = prospect_id

                country = location.get("country", None)
                country_acronym = location.get("country_acronym") or location.get("country_code")
                address = location.get("address", None)

                created_at = datetime.utcnow()

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
                stats["prospects_inserted"] += 1
                logger.debug("Created prospect %s", prospect_id)

            except Exception as e:
                error_msg = f"Error processing prospect: {str(e)}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)

    logger.info(
        "Database save complete: %d inserted, %d duplicates skipped, %d errors",
        stats["prospects_inserted"],
        stats["skipped_duplicates"],
        len(stats["errors"]),
    )
    if stats["errors"]:
        logger.warning("Encountered %d errors during database save", len(stats["errors"]))

    return stats

def main():
    """Main entry point for loading deduplication results."""
    results_path = LEADS_AUGMENTED_PATH
    # export_enriched_leads_to_json(str(results_path))
    persist_enriched_leads_to_database(str(results_path))

if __name__ == "__main__":
    main()
