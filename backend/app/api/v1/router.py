from fastapi import APIRouter

from app.api.v1 import auth, auth_sessions, dashboard, health, misc, projects, scans

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(auth_sessions.router)
api_router.include_router(projects.router)
api_router.include_router(scans.router)
api_router.include_router(dashboard.router)
api_router.include_router(misc.router)
