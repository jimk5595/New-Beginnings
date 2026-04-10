import os
import json
import logging
from core.config import Config
from persona_logger import narrate
from tools.expansion import RUN_EXPANSION_TASK
from tools.repair import RUN_REPAIR_TASK
from tools.integration import RUN_INTEGRATION_TASK
from tools.system_health import run_system_health_check
from tools.project_map import ProjectMap

logger = logging.getLogger("Toolset")
config = Config()

def tool_run_expansion(task_text: str, module_name: str = None) -> str:
    """Creates a new module directory structure based on the task description."""
    return RUN_EXPANSION_TASK(task_text, module_name=module_name)

def tool_run_repair(repair_text: str) -> str:
    """Identifies and targets broken or mocked files for repair."""
    return RUN_REPAIR_TASK(repair_text)

def tool_run_integration(integration_text: str, module_name: str = None) -> str:
    """Syncs modules, validates them, and updates the system manifest."""
    return RUN_INTEGRATION_TASK(integration_text, module_name=module_name)

def tool_run_health_check() -> str:
    """Runs a full system health and integrity check."""
    return run_system_health_check()

def FS_LIST_DIR(path: str) -> str:
    """Lists files and directories in a given path relative to project root."""
    try:
        project_root = str(ProjectMap().root_dir).replace('\\', '/')
        full_path = os.path.join(project_root, path).replace('\\', '/')
        if not os.path.exists(full_path):
            return f"Error: Path {path} does not exist."
        items = os.listdir(full_path)
        return json.dumps(items)
    except Exception as e:
        return f"Error: {str(e)}"

def FS_READ_FILE(path: str) -> str:
    """Reads the content of a file at the given path relative to project root."""
    try:
        project_root = str(ProjectMap().root_dir).replace('\\', '/')
        full_path = os.path.join(project_root, path).replace('\\', '/')
        if not os.path.exists(full_path):
            return f"Error: File {path} not found."
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error: {str(e)}"

def FS_WRITE_FILE(path: str, content: str) -> str:
    """Writes content to a file at the given path."""
    try:
        from eliza_file_guard import audit_file_operation
        audit_file_operation(path)
        project_root = str(ProjectMap().root_dir).replace('\\', '/')
        full_path = os.path.join(project_root, path).replace('\\', '/')
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Success: Wrote to {path}"
    except Exception as e:
        return f"Error: {str(e)}"

def FS_APPEND_FILE(path: str, content: str) -> str:
    """Appends content to a file."""
    try:
        from eliza_file_guard import audit_file_operation
        audit_file_operation(path)
        project_root = str(ProjectMap().root_dir).replace('\\', '/')
        full_path = os.path.join(project_root, path).replace('\\', '/')
        with open(full_path, "a", encoding="utf-8") as f:
            f.write(content)
        return f"Success: Appended to {path}"
    except Exception as e:
        return f"Error: {str(e)}"

def LOAD_PERSONA(persona_id: str) -> str:
    """Retrieves metadata and instructions for a specific persona."""
    try:
        from persona_manager import persona_manager
        persona_manager.load_personas()
        persona = persona_manager.registry.get(persona_id)
        if not persona:
            return f"Error: Persona {persona_id} not found."
        return json.dumps(persona)
    except Exception as e:
        return f"Error: {str(e)}"

def postgres_execute(query: str) -> str:
    """Executes a SQL query on the system database."""
    try:
        import psycopg2
        from config import settings
        conn = psycopg2.connect(settings.DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute(query)
        if query.strip().upper().startswith("SELECT"):
            results = cursor.fetchall()
            conn.close()
            return json.dumps(results, default=str)
        else:
            conn.commit()
            conn.close()
            return "Success: Query executed."
    except Exception as e:
        return f"Error: {str(e)}"

def RUN_BUILD_SCRIPT(module_name: str = None) -> str:
    """Triggers the esbuild and backend registration pipeline."""
    try:
        import subprocess
        import sys
        # Dynamic path detection using ProjectMap
        project_root = str(ProjectMap().root_dir).replace('\\', '/')
        backend_dir = os.path.join(project_root, "backend").replace('\\', '/')
        creation_flags = 0x08000000 if os.name == 'nt' else 0
        cmd = [sys.executable, os.path.join(backend_dir, "build.py")]
        if module_name:
            cmd.extend(["--module", module_name])
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=creation_flags)
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error: {str(e)}"

def FS_GET_PROJECT_MAP() -> str:
    """Returns a structured map of the entire project (modules, routes, APIs)."""
    try:
        project_map = ProjectMap().to_dict()
        return json.dumps(project_map)
    except Exception as e:
        return f"Error: {str(e)}"

AVAILABLE_TOOLS = [
    tool_run_expansion, tool_run_repair, tool_run_integration, 
    tool_run_health_check, FS_LIST_DIR, FS_READ_FILE, FS_WRITE_FILE, FS_APPEND_FILE,
    LOAD_PERSONA, postgres_execute, RUN_BUILD_SCRIPT, FS_GET_PROJECT_MAP
]
