"""
State definitions for the scoring agent
"""

from typing import TypedDict, List, Dict, Any


class ScoringState(TypedDict):
    """State for the scoring agent"""
    prospects: List[Dict[str, Any]]  # New format: database prospect structure
    points_scores: List[Dict[str, Any]]
    llm_scores: List[Dict[str, Any]]
    final_scores: List[Dict[str, Any]]

