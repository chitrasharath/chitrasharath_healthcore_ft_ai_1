from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import StreamableHTTPASGIApp
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.routing import Mount

from company_tools import auth
from company_tools.config import get_settings, require_config
from company_tools.request_context import RequestContextMiddleware
from company_tools.tools import register_incident_tools, register_inventory_tools

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("company_tools")


def create_app() -> Starlette:
    """Build Starlette ASGI app: PRM + Streamable HTTP MCP behind mcpauth bearer."""
    settings = require_config()
    auth.init_auth(settings)

    mcp = FastMCP("company-tools")
    register_incident_tools(mcp)
    register_inventory_tools(mcp)

    # Initialize StreamableHTTPSessionManager (created by streamable_http_app).
    _ = mcp.streamable_http_app()
    session_manager = mcp._session_manager
    if session_manager is None:
        raise RuntimeError("StreamableHTTPSessionManager was not initialized")

    streamable_asgi = StreamableHTTPASGIApp(session_manager)
    bearer_cls = auth.bearer_middleware_class(settings)
    mcp_middleware = [
        Middleware(RequestContextMiddleware),
        Middleware(auth.WwwAuthenticateMiddleware, resource=settings.oidc_resource),
        Middleware(bearer_cls),
    ]

    @asynccontextmanager
    async def lifespan(_app: Starlette):
        async with session_manager.run():
            yield

    return Starlette(
        routes=[
            auth.protected_resource_metadata_route(settings),
            auth.get_mcp_auth().metadata_route(),
            Mount("/mcp", app=streamable_asgi, middleware=mcp_middleware),
        ],
        lifespan=lifespan,
    )


def main() -> None:
    try:
        settings = require_config()
        app = create_app()
    except SystemExit:
        raise
    except Exception as exc:
        logger.exception("Fatal startup error: %s", exc)
        sys.exit(1)

    logger.info(
        "Starting company-tools MCP on %s:%s (resource=%s)",
        settings.mcp_host,
        settings.mcp_port,
        settings.oidc_resource,
    )
    uvicorn.run(
        app,
        host=settings.mcp_host,
        port=settings.mcp_port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
