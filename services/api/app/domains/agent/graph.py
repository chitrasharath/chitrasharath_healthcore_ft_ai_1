from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.domains.agent.nodes import (
    classify_node,
    compose_node,
    gather_node,
    honest_fallback_node,
    incident_tool_node,
    inventory_tool_node,
    receive_question,
    retrieve_node,
)
from app.domains.agent.routing import after_gather, after_receive, route_intent
from app.domains.agent.state import AgentState


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("receive_question", receive_question)
    builder.add_node("classify", classify_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("incident_tool", incident_tool_node)
    builder.add_node("inventory_tool", inventory_tool_node)
    builder.add_node("gather", gather_node)
    builder.add_node("compose", compose_node)
    builder.add_node("honest_fallback", honest_fallback_node)

    builder.set_entry_point("receive_question")
    builder.add_conditional_edges(
        "receive_question",
        after_receive,
        {"classify": "classify", "end": END},
    )
    builder.add_conditional_edges(
        "classify",
        route_intent,
        {
            "retrieve": "retrieve",
            "incident_tool": "incident_tool",
            "inventory_tool": "inventory_tool",
        },
    )
    builder.add_edge("retrieve", "gather")
    builder.add_edge("incident_tool", "gather")
    builder.add_edge("inventory_tool", "gather")
    builder.add_conditional_edges(
        "gather",
        after_gather,
        {
            "compose": "compose",
            "honest_fallback": "honest_fallback",
            "end": END,
        },
    )
    builder.add_edge("compose", END)
    builder.add_edge("honest_fallback", END)

    # TODO: MemorySaver is in-process only — multi-worker Uvicorn does not share
    # checkpoints. Consider SqliteSaver/PostgresSaver if durable cross-worker
    # checkpointing is required.
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


# Compile once at import — structural errors surface at startup / collection.
compiled_graph = build_graph()
