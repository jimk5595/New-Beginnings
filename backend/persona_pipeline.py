from models import PipelineRequest, PipelineResponse
from schemas import persona as persona_module
import pipeline as local_pipeline

def run_persona_pipeline(request: PipelineRequest, persona: any) -> PipelineResponse:
    # Directly pass the prompt to the pipeline to avoid persona interference with the executor
    return local_pipeline.run_pipeline(request)