from fastapi import FastAPI
from models import PipelineRequest, PipelineResponse
from backend.persona import Persona
from persona_pipeline import run_persona_pipeline

app = FastAPI()

@app.post("/run_with_persona", response_model=PipelineResponse)
def run_with_persona(request: PipelineRequest, persona: Persona) -> PipelineResponse:
    return run_persona_pipeline(request, persona)
