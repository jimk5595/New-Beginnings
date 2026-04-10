from fastapi import APIRouter
from persona_manager import persona_manager

router = APIRouter()

@router.get("/personas")
async def list_personas():
    if not persona_manager.initialized:
        persona_manager.load_personas()
    return {"personas": list(persona_manager.registry.keys())}
