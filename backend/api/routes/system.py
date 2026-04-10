from fastapi import APIRouter
from task_models import PipelineRequest, PipelineResponse
from core.orchestrator import unified_orchestrator
from core.config import Config
import time

router = APIRouter()
start_time = time.time()
config = Config()

@router.get("/logs")
async def get_logs():
    try:
        from memory_system.memory_core import MemoryEngine
        engine = MemoryEngine()
        rows = engine.retrieve_context("build_registry", limit=50)
        logs = [
            {
                "id": row.get("id", idx),
                "message": row.get("project_name", ""),
                "detail": row.get("file_structure_map", ""),
                "timestamp": str(row.get("timestamp", "")),
            }
            for idx, row in enumerate(rows)
        ]
        return {"logs": logs}
    except Exception as e:
        return {"error": str(e), "logs": []}

@router.get("/tasks")
async def get_tasks():
    """Returns active background tasks from the orchestrator."""
    tasks = []
    for task_id, info in unified_orchestrator.active_tasks.items():
        tasks.append({
            "id": task_id,
            "name": info.get("text", "Unknown task")[:80],
            "status": info.get("status", "unknown"),
            "assigned_to": info.get("assigned_to", ""),
        })
    return {"tasks": tasks}

@router.get("/memory/status")
async def get_memory_status():
    """Returns live memory engine statistics."""
    try:
        from memory_system.memory_core import MemoryEngine
        engine = MemoryEngine()
        stats = engine.get_stats() if hasattr(engine, "get_stats") else {}
        return {
            "status": "healthy",
            "total_nodes": stats.get("total_nodes", "N/A"),
            "indexed_relations": stats.get("indexed_relations", "N/A"),
            "last_vacuum": stats.get("last_vacuum", "N/A"),
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@router.post("/run", response_model=PipelineResponse)
async def run_pipeline_endpoint(request: PipelineRequest) -> PipelineResponse:
    """Unified task execution via the orchestrator."""
    result = await unified_orchestrator.handle_task(request.prompt)
    return PipelineResponse(output=result.get("response", ""), steps=None)
