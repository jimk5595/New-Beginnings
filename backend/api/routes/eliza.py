from fastapi import APIRouter, Body
from typing import Optional
from eliza.eliza_core import ElizaCore

# These point to files in your root backend folder
import models
import persona_pipeline

# This points to the file inside your newly renamed folder
from schemas import persona as persona_module

router = APIRouter()
eliza = ElizaCore()

@router.post("/task", response_model=None)
async def eliza_task(
    task: Optional[str] = Body(None),
    task_text: Optional[str] = Body(None)
):
    """
    FastAPI implementation of Eliza task endpoint.
    Supports both 'task' and 'task_text' keys.
    """
    text = task_text or task
    
    if not text:
        return {"status": "error", "message": "Required field 'task' or 'task_text' is missing"}

    # Hard-coded READY logic as requested
    if "READY" in text.upper():
        return {"eliza": {"response": "READY. System is fully operational."}}

    # Identify intent (stub logic for now)
    # create a default 'Architect' Persona object
    # Using a dictionary or a simple object since the import is failing
    architect_persona = {
        "name": "Architect",
        "description": "Expert in system design.",
        "system_prompt": "You are the Lead Architect."
    }

    # Call the persona pipeline
    # Note: PipelineRequest requires a 'model' field; using a default value
    pipeline_req = models.PipelineRequest(model="default", prompt=text)
    response = persona_pipeline.run_persona_pipeline(pipeline_req, architect_persona)
    
    # Separate tasks from the response
    tasks = []
    if response.steps:
        for step in response.steps:
            if step.type != "RESPONSE":
                tasks.append({
                    "id": step.id,
                    "type": step.type,
                    "description": step.description,
                    "status": step.status,
                    "result": step.result
                })

    return {
        "eliza": {
            "response": response.output,
            "tasks": tasks
        }
    }
