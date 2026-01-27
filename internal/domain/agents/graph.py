"""
LangGraph workflow creation for leads scoring
"""

from langgraph.graph import StateGraph, END
from internal.domain.agents.state import ScoringState
from internal.domain.agents.nodes import (
    points_scoring_node,
    llm_scoring_node,
    combine_scores_node,
)


def create_scoring_graph() -> StateGraph:
    """
    Create the LangGraph workflow for leads scoring
    
    Returns:
        Compiled StateGraph
    """
    workflow = StateGraph(ScoringState)

    workflow.add_node("points_scoring", points_scoring_node)
    workflow.add_node("llm_scoring", llm_scoring_node)
    workflow.add_node("combine_scores", combine_scores_node)

    workflow.set_entry_point("points_scoring")

    workflow.add_edge("points_scoring", "llm_scoring")
    workflow.add_edge("llm_scoring", "combine_scores")
    workflow.add_edge("combine_scores", END)
    
    return workflow.compile()

