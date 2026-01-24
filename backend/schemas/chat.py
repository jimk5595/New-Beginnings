from pydantic import BaseModel

class ChatRequest(BaseModel):
    persona: str
    message: str

class ChatResponse(BaseModel):
    response: str
