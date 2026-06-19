from fastapi import APIRouter

from app.domains.auth.router import router as auth_router
from app.domains.users.router import router as users_router

from app.domains.procurement.suppliers.router import router as suppliers_router
from app.domains.reporting.incidents.router import router as incidents_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(incidents_router)
api_v1_router.include_router(suppliers_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
# Future: from fastapi import Depends
# from app.core.dependencies import get_current_user
# api_v1_router.include_router(suppliers_router, dependencies=[Depends(get_current_user)])
