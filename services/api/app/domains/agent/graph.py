from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.domains.agent.nodes import (
    no_context_node,
    query_node,
    receive_question,
    retrieve_node,
)
from app.domains.agent.routing import after_receive, after_retrieve
from app.domains.agent.state import AgentState


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("receive_question", receive_question)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("query", query_node)
    builder.add_node("no_context", no_context_node)

    builder.set_entry_point("receive_question")
    builder.add_conditional_edges(
        "receive_question",
        after_receive,
        {"retrieve": "retrieve", "end": END},
    )
    builder.add_conditional_edges(
        "retrieve",
        after_retrieve,
        {"query": "query", "no_context": "no_context", "end": END},
    )
    builder.add_edge("query", END)
    builder.add_edge("no_context", END)

    # TODO: MemorySaver is in-process only — multi-worker Uvicorn does not share
    # checkpoints. Consider SqliteSaver/PostgresSaver if durable cross-worker
    # checkpointing is required.
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


# Compile once at import — structural errors surface at startup / collection.
compiled_graph = build_graph()
