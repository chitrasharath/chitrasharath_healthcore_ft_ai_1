from __future__ import annotations

from fastapi import APIRouter

from app.domains.agent import service
from app.domains.agent.schemas import AgentQueryRequest, AgentQueryResponse

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/query", response_model=AgentQueryResponse)
def query_agent(body: AgentQueryRequest) -> AgentQueryResponse:
    return service.invoke_graph(body.question)
