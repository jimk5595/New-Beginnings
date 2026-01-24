from fastapi import APIRouter
from personas.factory import PERSONA_REGISTRY

router = APIRouter()

@router.get("/personas")
async def list_personas():
    return {"personas": list(PERSONA_REGISTRY.keys())}
