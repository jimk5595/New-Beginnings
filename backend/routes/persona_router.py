from fastapi import APIRouter
from services.persona_service import PersonaService

router = APIRouter()

@router.post("/run")
def run_persona(payload: dict):
    persona = payload.get("persona", "")
    prompt = payload.get("prompt", "")
    model = payload.get("model", None)
    service = PersonaService(model=model)
    output = service.run(persona, prompt)
    return {"response": output}
