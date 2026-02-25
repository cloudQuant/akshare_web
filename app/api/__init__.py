"""
API router aggregation.

Combines all API route modules into a single router.
"""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.interfaces import router as interfaces_router
from app.api.tasks import router as tasks_router
from app.api.data import router as data_router
from app.api.tables import router as tables_router
from app.api.users import router as users_router
from app.api.scripts import router as scripts_router
from app.api.executions import router as executions_router
from app.api import settings as settings_api
from app.api.websocket import router as ws_router

api_router = APIRouter()

# Include all route modules
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(interfaces_router, prefix="/data/interfaces", tags=["Data Interfaces"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["Scheduled Tasks"])
api_router.include_router(data_router, prefix="/data", tags=["Data Acquisition"])
api_router.include_router(tables_router, prefix="/tables", tags=["Data Tables"])
api_router.include_router(users_router, prefix="/users", tags=["User Management"])
api_router.include_router(scripts_router, prefix="/scripts", tags=["Data Scripts"])
api_router.include_router(executions_router, prefix="/executions", tags=["Task Executions"])
api_router.include_router(settings_api.router, prefix="/settings", tags=["Settings"])
api_router.include_router(ws_router, tags=["WebSocket"])
