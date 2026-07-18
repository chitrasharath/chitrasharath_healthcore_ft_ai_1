import logging
import sys
from pathlib import Path

# Repo root must be on sys.path before importing routers that use `data.pipelines`.
# Walk up so Docker (/app/services/api/app/...) and local checkouts both resolve.
def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "data" / "pipelines").is_dir():
            return parent
    return here.parents[3]


_REPO_ROOT = _repo_root()
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import SQLModel

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.db import supabase_engine
from app.domains.inventory import models as inventory_models  # noqa: F401
from app.domains.incidents import models as incident_models  # noqa: F401
from app.domains.jobs import models as job_models  # noqa: F401
from app.domains.async_tasks import models as async_tasks_models  # noqa: F401
from app.domains.telemetry import models as telemetry_models  # noqa: F401
from app.domains.telemetry import reporting_models as telemetry_reporting_models  # noqa: F401
from app.domains.telemetry.indexes import ensure_telemetry_indexes

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)
logging.getLogger("app.domains.telemetry").setLevel(logging.INFO)

app = FastAPI(title="HealthCore API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )


@app.on_event("startup")
def on_startup() -> None:
    if supabase_engine:
        SQLModel.metadata.create_all(supabase_engine)
        ensure_telemetry_indexes(supabase_engine)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
