from fastapi import FastAPI
from router.eliza_router import router as eliza_router
from models import PipelineRequest, PipelineResponse
from persona_library import (
    system_persona,
    eliza_persona,
    technical_persona,
    eliza_core_persona,
    eliza_coo_persona,
    eliza_build_persona
)
from persona_pipeline import run_persona_pipeline
from eliza_orchestrator import run_eliza_orchestrator

app = FastAPI()
app.include_router(eliza_router)
@app.post("/run_with_persona_name", response_model=PipelineResponse)
def run_with_persona_name(request: PipelineRequest, persona_name: str) -> PipelineResponse:
    if persona_name == "system":
        persona = system_persona
    elif persona_name == "eliza":
        persona = eliza_persona
    elif persona_name == "technical":
        persona = technical_persona
    elif persona_name == "elizacore":
        persona = eliza_core_persona
    elif persona_name == "elizacoo":
        persona = eliza_coo_persona
    elif persona_name == "elizabuild":
        persona = eliza_build_persona
    else:
        return PipelineResponse(output="Unknown persona")
    return run_persona_pipeline(request, persona)

@app.post("/run_eliza", response_model=PipelineResponse)
def run_eliza(request: PipelineRequest) -> PipelineResponse:
    return run_eliza_orchestrator(request)
