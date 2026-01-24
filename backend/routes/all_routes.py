from routes.persona_router import router as persona_router
from core.router import router as core_router

ROUTES = [
    ("/core", core_router),
    ("/personas", persona_router)
]
