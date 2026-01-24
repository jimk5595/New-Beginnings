from fastapi import APIRouter
from pydantic import BaseModel
from services.llm_service import LLMService
from services.persona_service import PersonaService

router = APIRouter()

class ChatRequest(BaseModel):
    persona: str
    message: str

@router.post("/chat", response_model=None)
async def chat_endpoint(payload: ChatRequest, llm):
    persona = PersonaService.instantiate(payload.persona)
    system_prompt = persona.system_prompt
    user_prompt = payload.message
    response = await llm.generate(system_prompt, user_prompt)
    return {"response": response}
