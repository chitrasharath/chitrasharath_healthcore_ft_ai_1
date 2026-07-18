from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.domains.auth.router import router as auth_router
from app.domains.users.router import router as users_router

from app.domains.procurement.suppliers.router import router as suppliers_router
from app.domains.reporting.incidents.router import router as incidents_router
from app.domains.incidents.router import router as incidents_mgmt_router
from app.domains.inventory.router import router as inventory_router
from app.domains.telemetry.router import router as telemetry_router
from app.domains.async_tasks.router import router as async_tasks_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(incidents_router, dependencies=[Depends(get_current_user)])
api_v1_router.include_router(incidents_mgmt_router, dependencies=[Depends(get_current_user)])
api_v1_router.include_router(suppliers_router, dependencies=[Depends(get_current_user)])
api_v1_router.include_router(inventory_router)
api_v1_router.include_router(telemetry_router)
api_v1_router.include_router(async_tasks_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
