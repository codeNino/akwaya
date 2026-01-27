"""
Loader script to insert deduplication results into PostgreSQL database using SQLAlchemy
"""

import json
import uuid
from typing import Dict, List
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
    DEDUPLICATION_RESULTS_PATH,
    RAW_PROSPECTIVE_INDIVIDUALS_PATH,
    DB_MODELS_TEMP_DIR,
    DEDUPLICATION_WHITELABELS_RESULTS_PATH,
)
from internal.utils.database import DatabaseManager, get_session, init_db
from internal.utils.database.models import Prospect, ProspectSource, RawSnapshot
# from internal.utils.parser import normalize_website, parse_location

logger = AppLogger("domain.pipeline.loader")()


def parse_location(location_str: str) -> Dict:
    """
    Parse location string into structured JSONB format
    
    Args:
        location_str: Location string like "New York, NY" or "London, UK"
        
    Returns:
        Dict with city, country, and full_address
    """
    if not location_str:
        return {}
    
    parts = [p.strip() for p in location_str.split(',')]
    
    result = {
        'full_address': location_str
    }
    
    if len(parts) >= 1:
        result['city'] = parts[0]
    if len(parts) >= 2:
        result['country'] = parts[-1]
    
    return result

def normalize_website(website: str) -> str:
    """
    Normalize website URL
    
    Args:
        website: Website URL or domain
        
    Returns:
        Normalized URL
    """
    if not website:
        return ""
    
    if not website.startswith(('http://', 'https://')):
        website = 'https://' + website
    
    # Remove trailing slash
    website = website.rstrip('/')
    
    return website

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


def save_deduplication_results_as_json(
    results_file_path: str, raw_prospects_path: str = None, output_dir: Path = None
) -> Dict:
    """
    Save deduplication results as JSON files without inserting into database

    Creates model instances and saves their JSON representations to files.
    RawSnapshot uses the exact payload from raw_prospect_normalized.json.
    This is useful for previewing what would be saved to the database.

    Args:
        results_file_path: Path to deduplication_results.json
        raw_prospects_path: Path to raw_prospect_normalized.json (defaults to RAW_NORMALIZED_PROSPECT_PATH)
        output_dir: Directory to save JSON files (defaults to DB_MODELS_TEMP_DIR)

    Returns:
        Dict with saving statistics
    """
    if output_dir is None:
        output_dir = DB_MODELS_TEMP_DIR

    if raw_prospects_path is None:
        raw_prospects_path = str(RAW_PROSPECTIVE_INDIVIDUALS_PATH)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Saving model JSONs to %s", output_dir)

    logger.info("Loading raw prospects from %s", raw_prospects_path)
    with open(raw_prospects_path, "r", encoding="utf-8") as f:
        raw_prospects = json.load(f)

    raw_prospect_map = {p["prospect_id"]: p for p in raw_prospects}

    logger.info("Loading deduplication results from %s", results_file_path)
    with open(results_file_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    prospects = results.get("prospects_for_enrichment", [])
    logger.info("Processing %d prospects", len(prospects))

    stats = {
        "prospects_saved": 0,
        "sources_saved": 0,
        "snapshots_saved": 0,
        "errors": [],
    }

    for prospect_data in prospects:
        try:
            # Extract prospect information
            prospect_id = prospect_data["prospect_id"]
            name = prospect_data["name"]
            contact_info = prospect_data["contact_info"]
            sources = prospect_data.get("sources", [])

            # Prepare data for models
            emails = contact_info.get("emails", [])
            phones = contact_info.get("phones", [])
            websites = [
                normalize_website(w) for w in contact_info.get("websites", []) if w
            ]
            platforms = list(set([s["source_platform"] for s in sources]))

            # Build profile_urls JSONB
            profile_urls = {}
            for source in sources:
                platform = source["source_platform"]
                url = source.get("source_url", "")
                if url:
                    profile_urls[platform] = url

            location = parse_location(prospect_data.get("location", ""))

            # Parse created_at timestamp
            created_at_str = prospect_data.get(
                "created_at", datetime.utcnow().isoformat()
            )
            try:
                created_at = datetime.fromisoformat(
                    created_at_str.replace("Z", "+00:00")
                )
            except:
                created_at = datetime.utcnow()

            # Extract about field (convert list to string if needed)
            about_raw = prospect_data.get("about", [])
            if isinstance(about_raw, list):
                about = "\n".join(about_raw) if about_raw else None
            else:
                about = about_raw if about_raw else None
            
            # Create Prospect model instance (without database)
            # Prospect uses String for prospect_id
            prospect = Prospect(
                prospect_id=prospect_id,
                name=name,
                about=about,
                emails=emails,
                phones=phones,
                websites=websites,
                platforms=platforms,
                profile_urls=profile_urls,
                location=location,
                discovery_confidence=prospect_data.get("confidence_score", 0.0),
                created_at=created_at,
            )

            # Save prospect JSON
            save_model_json(prospect, "prospect", prospect_id, output_dir)
            stats["prospects_saved"] += 1

            # Process sources and snapshots
            for source in sources:
                # Parse discovered_at timestamp
                discovered_at_str = source.get("timestamp", created_at_str)
                try:
                    discovered_at = datetime.fromisoformat(
                        discovered_at_str.replace("Z", "+00:00")
                    )
                except:
                    discovered_at = created_at

                # Get the original raw prospect data from raw_prospect_normalized.json
                temp_prospect_id = source.get("temp_prospect_id")
                raw_prospect_data = raw_prospect_map.get(temp_prospect_id)

                if not raw_prospect_data:
                    logger.warning(
                        "Raw prospect data not found for temp_prospect_id %s, using source data",
                        temp_prospect_id,
                    )
                    # Fallback: construct from source data
                    raw_prospect_data = {
                        "prospect_id": temp_prospect_id,
                        "source_platform": source.get("source_platform"),
                        "name": name,  # Use prospect name as fallback
                        "about": prospect_data.get("about", ""),
                        "contact_info": {"email": None, "phone": None, "website": None},
                        "location": prospect_data.get("location", ""),
                        "business_context": prospect_data.get("business_context"),
                        "source_url": source.get("source_url", ""),
                        "discovery_confidence_score": source.get(
                            "discovery_confidence", 0.0
                        ),
                        "timestamp": discovered_at_str,
                    }

                # Extract business_context from raw_prospect_data
                business_context = raw_prospect_data.get("business_context") if isinstance(raw_prospect_data, dict) else None
                
                # Create RawSnapshot model instance
                snapshot_id = str(uuid.uuid4())
                snapshot = RawSnapshot(
                    snapshot_id=uuid.UUID(snapshot_id),
                    prospect_id=prospect_id,
                    platform=source["source_platform"],
                    business_context=business_context,
                    snapshot_at=discovered_at,
                    is_latest=True,
                )

                # Save snapshot JSON
                save_model_json(snapshot, "raw_snapshot", snapshot_id, output_dir)
                stats["snapshots_saved"] += 1

                # Create ProspectSource model instance
                source_id = str(uuid.uuid4())
                source_obj = ProspectSource(
                    source_id=uuid.UUID(source_id),
                    prospect_id=prospect_id,
                    platform=source["source_platform"],
                    discovered_at=discovered_at,
                    discovery_method=None,
                    raw_snapshot_id=uuid.UUID(snapshot_id),
                )

                # Save source JSON
                save_model_json(source_obj, "prospect_source", source_id, output_dir)
                stats["sources_saved"] += 1

            logger.debug("Processed prospect %s", prospect_id)

        except Exception as e:
            error_msg = f"Error processing prospect {prospect_data.get('prospect_id', 'unknown')}: {str(e)}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)

    logger.info(
        "JSON saving complete: %d prospects, %d sources, %d snapshots saved",
        stats["prospects_saved"],
        stats["sources_saved"],
        stats["snapshots_saved"],
    )

    if stats["errors"]:
        logger.warning("Encountered %d errors during saving", len(stats["errors"]))

    return stats


def load_deduplication_results(
    results_file_path: str, raw_prospects_path: str = None
) -> Dict:
    """
    Load deduplication results into PostgreSQL database

    Args:
        results_file_path: Path to deduplication_results.json
        raw_prospects_path: Path to raw_prospect_normalized.json (defaults to RAW_NORMALIZED_PROSPECT_PATH)

    Returns:
        Dict with loading statistics
    """
    if raw_prospects_path is None:
        raw_prospects_path = str(RAW_PROSPECTIVE_INDIVIDUALS_PATH)

    # Initialize database tables
    logger.info("Initializing database tables...")
    init_db(drop_existing=False)

    # Load raw prospects for RawSnapshot data
    logger.info("Loading raw prospects from %s", raw_prospects_path)
    with open(raw_prospects_path, "r", encoding="utf-8") as f:
        raw_prospects = json.load(f)

    # Create a mapping from temp_prospect_id to raw prospect data
    raw_prospect_map = {p["prospect_id"]: p for p in raw_prospects}

    # Load deduplication results
    logger.info("Loading deduplication results from %s", results_file_path)
    with open(results_file_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    prospects = results.get("prospects_for_enrichment", [])
    logger.info("Processing %d prospects", len(prospects))

    stats = {
        "prospects_inserted": 0,
        "sources_inserted": 0,
        "snapshots_inserted": 0,
        "errors": [],
    }

    with get_session() as session:
        db_manager = DatabaseManager(session=session)

        for prospect_data in prospects:
            try:
                # Extract prospect information
                prospect_id = prospect_data["prospect_id"]
                name = prospect_data["name"]
                contact_info = prospect_data["contact_info"]
                sources = prospect_data.get("sources", [])

                emails = contact_info.get("emails", [])
                phones = contact_info.get("phones", [])
                websites = [
                    normalize_website(w) for w in contact_info.get("websites", []) if w
                ]

                platforms = list(set([s["source_platform"] for s in sources]))

                profile_urls = {}
                for source in sources:
                    platform = source["source_platform"]
                    url = source.get("source_url", "")
                    if url:
                        profile_urls[platform] = url

                location = parse_location(prospect_data.get("location", ""))

                created_at_str = prospect_data.get(
                    "created_at", datetime.utcnow().isoformat()
                )
                try:
                    created_at = datetime.fromisoformat(
                        created_at_str.replace("Z", "+00:00")
                    )
                except:
                    created_at = datetime.utcnow()
                
                # Extract about field (convert list to string if needed)
                about_raw = prospect_data.get("about", [])
                if isinstance(about_raw, list):
                    about = "\n".join(about_raw) if about_raw else None
                else:
                    about = about_raw if about_raw else None
                    
                prospect = db_manager.create_prospect(
                    prospect_id=prospect_id,
                    name=name,
                    about=about,
                    emails=emails,
                    phones=phones,
                    websites=websites,
                    platforms=platforms,
                    profile_urls=profile_urls,
                    location=location,
                    discovery_confidence=prospect_data.get("confidence_score", 0.0),
                    created_at=created_at,
                    session=session,
                )

                if prospect:
                    stats["prospects_inserted"] += 1
                else:
                    stats["errors"].append(f"Failed to insert prospect {prospect_id}")
                    continue

                # Insert sources and snapshots
                for source in sources:
                    discovered_at_str = source.get("timestamp", created_at_str)
                    try:
                        discovered_at = datetime.fromisoformat(
                            discovered_at_str.replace("Z", "+00:00")
                        )
                    except:
                        discovered_at = created_at

                    # Get the original raw prospect data from raw_prospect_normalized.json
                    temp_prospect_id = source.get("temp_prospect_id")
                    raw_prospect_data = raw_prospect_map.get(temp_prospect_id)

                    if not raw_prospect_data:
                        logger.warning(
                            "Raw prospect data not found for temp_prospect_id %s, using source data",
                            temp_prospect_id,
                        )
                        # Fallback: construct from source data
                        raw_prospect_data = {
                            "prospect_id": temp_prospect_id,
                            "source_platform": source.get("source_platform"),
                            "name": name,
                            "about": prospect_data.get("about", ""),
                            "contact_info": {
                                "email": None,
                                "phone": None,
                                "website": None,
                            },
                            "location": prospect_data.get("location", ""),
                            "business_context": prospect_data.get("business_context"),
                            "source_url": source.get("source_url", ""),
                            "discovery_confidence_score": source.get(
                                "discovery_confidence", 0.0
                            ),
                            "timestamp": discovered_at_str,
                        }

                    # Extract business_context from raw_prospect_data
                    business_context = raw_prospect_data.get("business_context") if isinstance(raw_prospect_data, dict) else None
                    
                    snapshot = db_manager.create_raw_snapshot(
                        prospect_id=prospect_id,
                        platform=source["source_platform"],
                        snapshot_at=discovered_at,
                        business_context=business_context,
                        session=session,
                    )

                    if snapshot:
                        stats["snapshots_inserted"] += 1
                        # Ensure snapshot_id is a valid UUID string
                        if snapshot.snapshot_id:
                            snapshot_id = str(snapshot.snapshot_id)
                        else:
                            logger.warning(
                                "Snapshot created but snapshot_id is None for prospect %s",
                                prospect_id,
                            )
                            snapshot_id = None
                    else:
                        logger.warning(
                            "Failed to insert snapshot for prospect %s", prospect_id
                        )
                        snapshot_id = None

                    source_obj = db_manager.create_prospect_source(
                        prospect_id=prospect_id,
                        platform=source["source_platform"],
                        discovered_at=discovered_at,
                        discovery_method=None,
                        raw_snapshot_id=(
                            snapshot_id if snapshot_id else None
                        ),  # Explicitly pass None if invalid
                        session=session,
                    )

                    if source_obj:
                        stats["sources_inserted"] += 1
                    else:
                        logger.warning(
                            "Failed to insert source for prospect %s", prospect_id
                        )

                logger.debug("Processed prospect %s", prospect_id)

            except Exception as e:
                error_msg = f"Error processing prospect {prospect_data.get('prospect_id', 'unknown')}: {str(e)}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)

    logger.info(
        "Loading complete: %d prospects, %d sources, %d snapshots inserted",
        stats["prospects_inserted"],
        stats["sources_inserted"],
        stats["snapshots_inserted"],
    )

    if stats["errors"]:
        logger.warning("Encountered %d errors during loading", len(stats["errors"]))

    return stats


def main():
    """Main entry point for loading deduplication results"""
    # results_path = DEDUPLICATION_RESULTS_PATH
    results_path = DEDUPLICATION_WHITELABELS_RESULTS_PATH

    if not results_path.exists():
        logger.error("Deduplication results file not found: %s", results_path)
        return

    # Load results into database
    # stats = load_deduplication_results(str(results_path))
    
    # Save models as JSON without database insertion
    stats = save_deduplication_results_as_json(str(DEDUPLICATION_WHITELABELS_RESULTS_PATH))

    # Or specify custom output directory
    stats = save_deduplication_results_as_json(
        str(DEDUPLICATION_WHITELABELS_RESULTS_PATH), output_dir=Path("custom/output/path")
    )

    # Print summary
    # print("\n" + "="*50)
    # print("Database Loading Summary")
    # print("="*50)
    # print(f"Prospects inserted: {stats['prospects_inserted']}")
    # print(f"Sources inserted: {stats['sources_inserted']}")
    # print(f"Snapshots inserted: {stats['snapshots_inserted']}")
    # if stats['errors']:
    #     print(f"\nErrors: {len(stats['errors'])}")
    #     for error in stats['errors'][:5]:  # Show first 5 errors
    #         print(f"  - {error}")
    # print("="*50)


if __name__ == "__main__":
    main()
