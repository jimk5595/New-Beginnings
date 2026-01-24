from fastapi import APIRouter
from models import PipelineRequest, PipelineResponse
from eliza_orchestrator import run_eliza_orchestrator

router = APIRouter()

@router.post("/run_eliza", response_model=PipelineResponse)
def run_eliza_route(request: PipelineRequest) -> PipelineResponse:
    return run_eliza_orchestrator(request)
