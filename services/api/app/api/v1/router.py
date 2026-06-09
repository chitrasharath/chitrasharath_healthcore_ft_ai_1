from fastapi import APIRouter

from app.domains.reporting.incidents.router import router as incidents_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(incidents_router)
