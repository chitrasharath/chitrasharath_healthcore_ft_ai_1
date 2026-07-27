from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import oauth2_scheme
from app.domains.agent import service
from app.domains.agent.schemas import AgentQueryRequest, AgentQueryResponse

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/query", response_model=AgentQueryResponse)
def query_agent(
    body: AgentQueryRequest,
    token: str = Depends(oauth2_scheme),
) -> AgentQueryResponse:
    # Forward caller JWT into graph state for tool HTTP calls — never log token.
    return service.invoke_graph(body.question, auth_token=token)
