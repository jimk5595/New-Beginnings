from fastapi import FastAPI
from models import PipelineRequest, PipelineResponse
from pipeline import run_pipeline

app = FastAPI()

@app.post("/run", response_model=PipelineResponse)
def run(request: PipelineRequest) -> PipelineResponse:
    return run_pipeline(request)
