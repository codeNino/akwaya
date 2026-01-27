"""
Main entry point for the leads scoring agent
"""
from pathlib import Path
import sys
import asyncio

_current = Path(__file__).resolve()
for parent in _current.parents:
    if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
        project_root = parent
        break
else:
    project_root = _current.parents[3]

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from typing import List, Dict, Any
from internal.utils.logger import AppLogger
from internal.domain.agents.state import ScoringState
from internal.domain.agents.graph import create_scoring_graph

logger = AppLogger("domain.agents.agent")()


async def score_prospects(prospects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Score a list of prospects using the LangGraph agent
    
    Args:
        prospects: List of prospect dictionaries
        
    Returns:
        List of scored prospects with final scores, sorted by score (descending)
    """
    if not prospects:
        logger.warning("No prospects provided for scoring")
        return []
    
    logger.info("Starting leads scoring for %d prospects", len(prospects))
    graph = create_scoring_graph()
    
    initial_state: ScoringState = {
        "prospects": prospects,
        "points_scores": [],
        "llm_scores": [],
        "final_scores": []
    }
    
    result = await graph.ainvoke(initial_state)
    
    logger.info(
        "Scoring complete. Top score: %.3f, Bottom score: %.3f",
        result["final_scores"][0]["final_score"] if result["final_scores"] else 0.0,
        result["final_scores"][-1]["final_score"] if result["final_scores"] else 0.0
    )
    
    return result["final_scores"]


if __name__ == "__main__":
    import json
    from internal.config.paths_config import RAW_PROSPECTIVE_INDIVIDUALS_PATH
    
    with open(RAW_PROSPECTIVE_INDIVIDUALS_PATH, "r", encoding="utf-8") as f:
        prospects = json.load(f)
    
    scored = asyncio.run(score_prospects(prospects[5:8]))
    
    print("\n" + "="*80)
    print("LEADS SCORING RESULTS")
    print("="*80)
    for i, result in enumerate(scored, 1):
        print(f"\n{i}. {result['name']} (ID: {result['prospect_id']})")
        print(f"   Final Score: {result['final_score']:.3f}")
        print(f"   Points Score: {result['points_score']:.3f} | LLM Score: {result['llm_score']:.3f}")
        print(f"   LLM Reasoning: {result['llm_reasoning']}")
        platforms = result['prospect_data'].get('platforms', [])
        print(f"   Platforms: {', '.join(platforms) if platforms else 'N/A'}")

