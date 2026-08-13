from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.domains.agent.memory.nodes import (
    memory_consent_check_node,
    memory_propose_node,
    memory_read_node,
)
from app.domains.agent.nodes import (
    classify_node,
    compose_node,
    external_content_node,
    gather_node,
    honest_fallback_node,
    incident_tool_node,
    input_guards_node,
    inventory_tool_node,
    observability_node,
    output_guards_node,
    receive_question,
    retrieve_node,
)
from app.domains.agent.routing import (
    after_external_content,
    after_input_guards,
    after_memory_consent,
    after_receive,
    route_intent,
)
from app.domains.agent.state import AgentState


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("receive_question", receive_question)
    builder.add_node("memory_consent_check", memory_consent_check_node)
    builder.add_node("input_guards", input_guards_node)
    builder.add_node("memory_read", memory_read_node)
    builder.add_node("classify", classify_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("incident_tool", incident_tool_node)
    builder.add_node("inventory_tool", inventory_tool_node)
    builder.add_node("gather", gather_node)
    builder.add_node("external_content", external_content_node)
    builder.add_node("compose", compose_node)
    builder.add_node("honest_fallback", honest_fallback_node)
    builder.add_node("output_guards", output_guards_node)
    builder.add_node("memory_propose", memory_propose_node)
    builder.add_node("observability", observability_node)

    builder.set_entry_point("receive_question")
    builder.add_conditional_edges(
        "receive_question",
        after_receive,
        {"memory_consent_check": "memory_consent_check", "end": END},
    )
    builder.add_conditional_edges(
        "memory_consent_check",
        after_memory_consent,
        {"input_guards": "input_guards", "observability": "observability"},
    )
    builder.add_conditional_edges(
        "input_guards",
        after_input_guards,
        {"memory_read": "memory_read", "observability": "observability"},
    )
    builder.add_edge("memory_read", "classify")
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
    builder.add_edge("gather", "external_content")
    builder.add_conditional_edges(
        "external_content",
        after_external_content,
        {
            "compose": "compose",
            "honest_fallback": "honest_fallback",
            "end": END,
        },
    )
    builder.add_edge("compose", "output_guards")
    builder.add_edge("honest_fallback", "output_guards")
    builder.add_edge("output_guards", "memory_propose")
    builder.add_edge("memory_propose", "observability")
    builder.add_edge("observability", END)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


compiled_graph = build_graph()
