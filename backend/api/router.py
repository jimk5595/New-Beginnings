from fastapi import APIRouter
from api.routes.chat import router as chat_router
from api.routes.persona import router as persona_router
from api.routes.health import router as health_router
from api.routes.eliza import router as eliza_router
from api.routes.system import router as system_router
from api.routes.status import status_router

api_router = APIRouter()
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(persona_router, prefix="/personas", tags=["personas"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(eliza_router, prefix="/eliza", tags=["eliza"])
api_router.include_router(system_router, tags=["system"])
api_router.include_router(status_router, tags=["status"])
