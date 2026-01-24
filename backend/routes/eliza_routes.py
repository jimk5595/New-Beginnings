# eliza_routes.py
# HTTP route exposing Eliza's persona system to the backend API.

from fastapi import APIRouter
from pydantic import BaseModel
from eliza_controller import eliza_controller

router = APIRouter()


# ---------------------------------------------------------
# REQUEST MODEL
# ---------------------------------------------------------
class ElizaTaskRequest(BaseModel):
    message: str


# ---------------------------------------------------------
# ROUTE: PROCESS TASK
# ---------------------------------------------------------
@router.post("/eliza/task")
def process_eliza_task(request: ElizaTaskRequest):
    """
    Accepts a natural-language message and processes it through Eliza.
    """
    result = eliza_controller.process(request.message)
    return result