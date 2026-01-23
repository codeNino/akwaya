"""
Prospect Data Mining & Deduplication System
Phase 1: Transform normalized raw prospects into clean, deduplicated entities

Main entry point for the deduplication pipeline.
"""

import sys
import json
from pathlib import Path
from typing import List, Dict

_current = Path(__file__).resolve()
for parent in _current.parents:
    if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
        project_root = parent
        break
else:
    project_root = _current.parents[3]

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from internal.domain.scraper.sources.dto import ProspectDict
from internal.utils.logger import AppLogger
from internal.config.paths_config import ARTIFACTS_DIR, RAW_PROSPECTIVE_INDIVIDUALS_PATH
from internal.domain.pipeline.engine import DeduplicationEngine

logger = AppLogger("domain.pipeline.feature")()


def entrypoint() -> Dict:
    """
    Main entry point for deduplication pipeline
    
    Returns:
        Dict containing deduplication results with summary, prospects, and flags
    """
    logger.info("Loading raw prospects from %s", RAW_PROSPECTIVE_INDIVIDUALS_PATH)
    
    # Load raw prospects
    try:
        with open(RAW_PROSPECTIVE_INDIVIDUALS_PATH, 'r', encoding='utf-8') as f:
            raw_prospects: List[ProspectDict] = json.load(f)
    except FileNotFoundError:
        logger.error("Raw prospects file not found: %s", RAW_PROSPECTIVE_INDIVIDUALS_PATH)
        raise
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in raw prospects file: %s", e)
        raise
    
    logger.info("Loaded %d raw prospects", len(raw_prospects))
    
    # Process deduplication
    engine = DeduplicationEngine()
    results = engine.process(raw_prospects)
    
    # Save results
    output_path = ARTIFACTS_DIR / "deduplication_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info("Results saved to %s", output_path)
    logger.info(
        "Processing complete: %d canonical prospects ready for enrichment (merge rate: %.2f%%)",
        results['summary']['canonical_prospects_created'],
        results['summary']['merge_rate_percent']
    )
    
    return results


if __name__ == "__main__":
    entrypoint()

