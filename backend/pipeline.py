from models import PipelineRequest, PipelineResponse
from planner import generate_plan
from validator import validate_plan
from executor import execute_plan

def run_pipeline(request: PipelineRequest) -> PipelineResponse:
    plan = generate_plan(request.prompt)
    if not validate_plan(plan):
        return PipelineResponse(output="Invalid plan")
    executed_plan = execute_plan(plan, request.model)
    results = [step.result for step in executed_plan.steps if step.result]
    return PipelineResponse(output="\n".join(results), steps=executed_plan.steps)
