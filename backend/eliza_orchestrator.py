from models import PipelineRequest, PipelineResponse
from persona_library import (
    eliza_core_persona,
    eliza_coo_persona,
    eliza_build_persona
)
from persona_pipeline import run_persona_pipeline

def run_eliza_orchestrator(request: PipelineRequest) -> PipelineResponse:
    if request.task_type == "core":
        persona = eliza_core_persona
    elif request.task_type == "coo":
        persona = eliza_coo_persona
    elif request.task_type == "build":
        persona = eliza_build_persona
    else:
        return PipelineResponse(output="Unknown task type")
    return run_persona_pipeline(request, persona)
