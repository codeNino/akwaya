"""
Deduplication pipeline package

Exports main classes and functions for prospect deduplication.
"""

from internal.utils.models import (
    MergedContactInfo,
    SourceReference,
    CanonicalProspect
)
from internal.domain.pipeline.matcher import ProspectMatcher
from internal.domain.pipeline.engine import DeduplicationEngine
from internal.domain.pipeline.feature import entrypoint
from internal.domain.pipeline.loader import load_deduplication_results
# from internal.domain.pipeline.query import get_enrichment_queue

__all__ = [
    'MergedContactInfo',
    'SourceReference',
    'CanonicalProspect',
    'ProspectMatcher',
    'DeduplicationEngine',
    'load_deduplication_results',
    'entrypoint',
]

