from __future__ import annotations

from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_current_request: ContextVar[Request | None] = ContextVar(
    "company_tools_request", default=None
)


def get_current_request() -> Request | None:
    return _current_request.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        token = _current_request.set(request)
        try:
            return await call_next(request)
        finally:
            _current_request.reset(token)
