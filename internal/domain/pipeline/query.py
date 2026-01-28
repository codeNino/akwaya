from typing import List
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
from internal.utils.database.manager import DatabaseManager, EnrichmentsQueue
from internal.utils.database.session import get_session
from internal.utils.logger import AppLogger

logger = AppLogger("domain.pipeline.query")()


def retrieve_enrichments_queue(min_confidence: float = 0.5) -> List[EnrichmentsQueue]:
    """
    Retrieve database records that are ready for enrichment

    Args:
        min_confidence: Minimum discovery confidence threshold

    Returns:
        List of enrichment queue records
    """
    with get_session() as session:
        database_manager = DatabaseManager(session=session)
        return database_manager.get_enrichment_queue(min_confidence=min_confidence)


def enrich_prospect(prospect_id: str) -> None:
    """
    Enrich a prospect

    Args:
        prospect_id: ID of the prospect to enrich

    Returns:
        None
    """
    with get_session() as session:
        database_manager = DatabaseManager(session=session)
        database_manager.enrich_prospect(prospect_id=prospect_id)


if __name__ == "__main__":
    results = retrieve_enrichments_queue(min_confidence=0.1)
    print(results)