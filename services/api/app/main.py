from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.db import supabase_engine
from app.domains.inventory import models as inventory_models  # noqa: F401

app = FastAPI(title="HealthCore API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router)


@app.on_event("startup")
def on_startup() -> None:
    if supabase_engine:
        SQLModel.metadata.create_all(supabase_engine)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
