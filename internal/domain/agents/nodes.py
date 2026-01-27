"""
Graph nodes for the scoring workflow
"""

from typing import Dict, Any
from internal.domain.agents.state import ScoringState
from internal.domain.agents.scorer import calculate_llm_score, calculate_points_score
from internal.utils.logger import AppLogger

logger = AppLogger("domain.agents.nodes")()


def points_scoring_node(state: ScoringState) -> ScoringState:
    """
    Node: Calculate points-based scores for all prospects
    """
    logger.info("Calculating points-based scores for %d prospects", len(state["prospects"]))
    
    points_scores = []
    for prospect in state["prospects"]:
        score = calculate_points_score(prospect)
        points_scores.append(score)
    
    return {
        "points_scores": points_scores
    }


async def llm_scoring_node(state: ScoringState) -> ScoringState:
    """
    Node: Calculate LLM-based scores for all prospects
    """
    logger.info("Calculating LLM-based scores for %d prospects", len(state["prospects"]))
    
    llm_scores = []
    for prospect in state["prospects"]:
        score = await calculate_llm_score(prospect)
        llm_scores.append(score)
    
    return {
        "llm_scores": llm_scores
    }


def combine_scores_node(state: ScoringState) -> ScoringState:
    """
    Node: Combine points and LLM scores into final scores
    Uses weighted average: 40% points, 60% LLM
    """
    logger.info("Combining scores for final ranking")
    
    # Create lookup dictionaries
    points_lookup = {s["prospect_id"]: s for s in state["points_scores"]}
    llm_lookup = {s["prospect_id"]: s for s in state["llm_scores"]}
    
    final_scores = []
    for prospect in state["prospects"]:
        prospect_id = prospect["prospect_id"]
        
        points_data = points_lookup.get(prospect_id, {})
        llm_data = llm_lookup.get(prospect_id, {})
        
        points_score = points_data.get("points_score", 0.0)
        llm_score = llm_data.get("llm_score", 0.0)
        
        # Weighted combination: 40% points, 60% LLM
        final_score = (points_score * 0.4) + (llm_score * 0.6)
        
        final_scores.append({
            "prospect_id": prospect_id,
            "name": prospect.get("name", "Unknown"),
            "final_score": round(final_score, 3),
            "points_score": points_score,
            "llm_score": llm_score,
            "points_breakdown": points_data.get("breakdown", {}),
            "llm_reasoning": llm_data.get("reasoning", ""),
            "prospect_data": prospect
        })
    
    # Sort by final score (descending)
    final_scores.sort(key=lambda x: x["final_score"], reverse=True)
    
    return {
        "final_scores": final_scores
    }

