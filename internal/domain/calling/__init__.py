"""
Calling service for prospects
"""

from internal.domain.calling.retell_service import (
    call_prospects_with_phones,
    get_prospects_with_phones,
    get_prospects_with_phones_from_files,
    make_retell_call,
)

__all__ = [
    "call_prospects_with_phones",
    "get_prospects_with_phones",
    "get_prospects_with_phones_from_files",
    "make_retell_call",
]

