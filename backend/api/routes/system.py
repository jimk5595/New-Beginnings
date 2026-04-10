from fastapi import APIRouter
from task_models import PipelineRequest, PipelineResponse
from core.orchestrator import unified_orchestrator
from core.config import Config
import sqlite3
import os
import time

router = APIRouter()
start_time = time.time()
config = Config()

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "database", "system_growth.db")

@router.get("/logs")
async def get_logs():
    if not os.path.exists(_DB_PATH):
        return {"logs": []}
    try:
        conn = sqlite3.connect(_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, task, timestamp FROM build_registry ORDER BY timestamp DESC LIMIT 50")
        rows = cursor.fetchall()
        conn.close()
        logs = [{"id": row[0], "message": row[1], "timestamp": row[2]} for row in rows]
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
