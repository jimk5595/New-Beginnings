from fastapi import APIRouter
from core.gemini_client import GeminiClient

router = APIRouter()

@router.post("/generate")
def generate(payload: dict):
    prompt = payload.get("prompt", "")
    model = payload.get("model", None)
    client = GeminiClient(model=model)
    output = client.generate(prompt)
    return {"response": output}
