from dataclasses import dataclass
from typing import List, Optional

class TaskType:
    THINK = "THINK"
    WRITE = "WRITE"
    RESEARCH = "RESEARCH"
    CODE = "CODE"
    PLAN = "PLAN"
    EXECUTE = "EXECUTE"
    FS_CREATE_DIR = "FS_CREATE_DIR"
    FS_WRITE_FILE = "FS_WRITE_FILE"
    FS_READ_FILE = "FS_READ_FILE"
    FS_DELETE = "FS_DELETE"
    RESPONSE = "RESPONSE"

class StepStatus:
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"

@dataclass
class Step:
    id: int
    type: str
    description: str
    status: str = StepStatus.PENDING
    result: Optional[str] = None

@dataclass
class Plan:
    steps: List[Step]

@dataclass
class PipelineRequest:
    model: str
    prompt: str
    task_type: Optional[str] = None

@dataclass
class PipelineResponse:
    output: str
    steps: Optional[List[Step]] = None
