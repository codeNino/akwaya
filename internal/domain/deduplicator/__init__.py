"""
Deduplication pipeline package

Exports main classes and functions for prospect deduplication.
"""

from internal.domain.deduplicator.filter import (
    filter_leads,
    filter_by_contact_priority,
    get_contact_priority,
    get_priority_stats,
    ContactPriority,
)
from internal.domain.deduplicator.feature import entrypoint

__all__ = [
    'filter_leads',
    'filter_by_contact_priority',
    'get_contact_priority',
    'get_priority_stats',
    'ContactPriority',
    'entrypoint',
]

