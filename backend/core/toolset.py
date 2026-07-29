import os
import json
import logging
from pathlib import Path
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
    """Identifies and targets broken or mocked files for repair. Scoped to CURRENT_MODULE when set."""
    module_name = os.environ.get("CURRENT_MODULE", "")
    module_dir = None
    if module_name:
        try:
            from tools.project_map import ProjectMap
            root = ProjectMap().root_dir
            candidate = root / "backend" / "modules" / module_name
            if candidate.exists():
                module_dir = str(candidate)
        except Exception:
            pass
    return RUN_REPAIR_TASK(repair_text, module_dir=module_dir)

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
        category = os.environ.get("CURRENT_TASK_CATEGORY", "")
        current_module = os.environ.get("CURRENT_MODULE", "")
        if category in ("patch", "repair") and current_module and not module_name:
            return (
                f"SCOPE GUARD: Full system rebuild is blocked during repair of '{current_module}'. "
                f"Call RUN_BUILD_SCRIPT(module_name='{current_module}') to rebuild only that module."
            )
        if category in ("patch", "repair") and current_module and module_name and module_name != current_module:
            return (
                f"SCOPE GUARD: Cannot build module '{module_name}' during repair of '{current_module}'. "
                f"Only '{current_module}' can be rebuilt in this task scope."
            )
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

def FS_SEARCH_IN_FILE(path: str, pattern: str, context_lines: int = 3) -> str:
    """Search for a regex pattern in a file, returning matching lines with surrounding context. Use this to locate specific code, variable names, error patterns, or function definitions without reading the entire file."""
    try:
        import re as _re
        project_root = str(ProjectMap().root_dir).replace('\\', '/')
        full_path = os.path.join(project_root, path).replace('\\', '/')
        if not os.path.exists(full_path):
            return f"Error: File {path} not found."
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        results = []
        for i, line in enumerate(lines):
            if _re.search(pattern, line):
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                block = []
                for j in range(start, end):
                    prefix = ">>> " if j == i else "    "
                    block.append(f"{prefix}L{j+1}: {lines[j].rstrip()}")
                results.append("\n".join(block))
        if not results:
            return f"No matches for pattern '{pattern}' in {path}."
        return f"Found {len(results)} match(es) in {path}:\n\n" + "\n\n---\n\n".join(results)
    except Exception as e:
        return f"Error: {str(e)}"


def FS_READ_FILE_LINES(path: str, start_line: int, end_line: int) -> str:
    """Read a specific line range from a file (1-indexed, inclusive). Use this for targeted inspection of a known section of code — much faster than reading the whole file when you know the line numbers."""
    try:
        project_root = str(ProjectMap().root_dir).replace('\\', '/')
        full_path = os.path.join(project_root, path).replace('\\', '/')
        if not os.path.exists(full_path):
            return f"Error: File {path} not found."
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        total = len(lines)
        s = max(0, start_line - 1)
        e = min(total, end_line)
        if s >= total:
            return f"Error: start_line {start_line} exceeds file length ({total} lines)."
        selected = lines[s:e]
        numbered = [f"L{s+1+i}: {line.rstrip()}" for i, line in enumerate(selected)]
        return f"{path} lines {start_line}–{min(end_line, total)} (of {total}):\n\n" + "\n".join(numbered)
    except Exception as e:
        return f"Error: {str(e)}"


def RUN_RENDER_CHECK_DIAGNOSTIC(module_name: str) -> str:
    """Run a full headless browser render check on a built module. Returns a structured JSON report with: rendered status, console errors, uncaught JS exceptions, functional test failures (maps, buttons, nav), API errors (404/500/422), slow/hanging API routes. Use this to verify a fix worked or to diagnose what is broken."""
    try:
        import threading
        import asyncio as _asyncio
        from tools.render_check import check_module_renders
        result_holder = []
        exc_holder = []
        def _run():
            loop = _asyncio.new_event_loop()
            _asyncio.set_event_loop(loop)
            try:
                r = loop.run_until_complete(check_module_renders(module_name))
                result_holder.append(r)
            except Exception as ex:
                exc_holder.append(str(ex))
            finally:
                loop.close()
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout=90)
        if exc_holder:
            return json.dumps({"module": module_name, "error": exc_holder[0]})
        if not result_holder:
            return json.dumps({"module": module_name, "error": "Render check timed out after 90s"})
        r = result_holder[0]
        report = {
            "module": module_name,
            "rendered": r.get("rendered", False),
            "error_summary": r.get("error_summary", ""),
            "console_errors": r.get("console_errors", [])[:20],
            "functional_failures": r.get("functional_failures", []),
            "api_404s": r.get("api_404s", []),
            "api_500s": r.get("api_500s", []),
            "api_422s": r.get("api_422s", []),
            "api_slow": r.get("api_slow", []),
            "api_hang": r.get("api_hang", []),
            "root_html_length": r.get("root_html_length", 0),
            "diagnosis": (
                "PASS: Module renders correctly." if r.get("rendered") and not r.get("functional_failures")
                else f"FAIL: {r.get('error_summary') or 'Functional failures detected.'}"
            )
        }
        return json.dumps(report, indent=2)
    except Exception as e:
        return json.dumps({"module": module_name, "error": str(e)})


def RUN_MODULE_DIAGNOSTIC(module_name: str) -> str:
    """Full diagnostic on a module: (1) TypeScript/esbuild compile check, (2) headless render check, (3) mock/placeholder pattern scan. Returns a structured JSON report summarising all issues found. Use this as your first step when asked to debug or repair a module — it tells you exactly what is broken and where."""
    try:
        import re as _re
        from tools.render_check import check_module_renders
        from tools.repair import MOCK_PATTERNS
        from pathlib import Path as _Path
        import threading
        import asyncio as _asyncio

        project_root = str(ProjectMap().root_dir)
        module_dir = _Path(project_root) / "backend" / "modules" / module_name
        report = {
            "module": module_name,
            "build_errors": [],
            "render": {},
            "mock_files": [],
            "source_file_sizes": {},
            "overall_status": "UNKNOWN",
        }

        if not module_dir.exists():
            report["overall_status"] = "ERROR: module directory not found"
            return json.dumps(report, indent=2)

        for f in ["index.tsx", "app.py", "module.json"]:
            fp = module_dir / f
            if fp.exists():
                report["source_file_sizes"][f] = fp.stat().st_size

        build_out = RUN_BUILD_SCRIPT(module_name=module_name)
        build_errors = []
        for line in build_out.splitlines():
            if any(k in line.lower() for k in ("error", "failed", "cannot", "expected")):
                build_errors.append(line.strip())
        report["build_errors"] = build_errors[:20]

        SKIP_DIRS = {"node_modules", "venv", ".git", "__pycache__", "dist", "build"}
        mock_files = []
        for root, dirs, files in os.walk(module_dir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for file in files:
                if file.endswith((".py", ".ts", ".tsx")):
                    fp = _Path(root) / file
                    try:
                        content = fp.read_text(encoding="utf-8", errors="ignore")
                        for pat in MOCK_PATTERNS:
                            if _re.search(pat, content, _re.IGNORECASE):
                                mock_files.append(file)
                                break
                    except Exception:
                        pass
        report["mock_files"] = mock_files

        result_holder = []
        def _run():
            loop = _asyncio.new_event_loop()
            _asyncio.set_event_loop(loop)
            try:
                r = loop.run_until_complete(check_module_renders(module_name))
                result_holder.append(r)
            except Exception:
                pass
            finally:
                loop.close()
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout=90)

        if result_holder:
            r = result_holder[0]
            report["render"] = {
                "rendered": r.get("rendered", False),
                "error_summary": r.get("error_summary", ""),
                "console_errors": r.get("console_errors", [])[:20],
                "functional_failures": r.get("functional_failures", []),
                "api_404s": r.get("api_404s", []),
                "api_500s": r.get("api_500s", []),
                "api_422s": r.get("api_422s", []),
                "api_hang": r.get("api_hang", []),
            }
        else:
            report["render"] = {"error": "Render check timed out"}

        issues = len(build_errors) + len(mock_files) + (0 if report["render"].get("rendered") else 1) + len(report["render"].get("functional_failures", []))
        report["overall_status"] = "HEALTHY" if issues == 0 else f"ISSUES FOUND: {issues} problem(s) detected"
        return json.dumps(report, indent=2)
    except Exception as e:
        return json.dumps({"module": module_name, "error": str(e)})


def RUN_AB_TEST(module_name: str, variant_index_tsx: str) -> str:
    """A/B test a code change on a module. Provide the full content of the proposed variant index.tsx. This tool: (1) saves the current index.tsx as baseline, (2) writes and builds the variant, (3) runs render check on variant, (4) restores and runs render check on baseline, (5) scores both versions (rendered + no errors = better), (6) automatically keeps the WINNER and discards the loser. Returns a comparison report so you can see which version won and why."""
    try:
        import shutil
        import threading
        import asyncio as _asyncio
        from pathlib import Path as _Path
        from tools.render_check import check_module_renders

        project_root = str(ProjectMap().root_dir)
        module_dir = _Path(project_root) / "backend" / "modules" / module_name
        tsx_path = module_dir / "index.tsx"
        baseline_path = module_dir / "index.tsx.ab_baseline"

        if not tsx_path.exists():
            return json.dumps({"error": f"index.tsx not found for module '{module_name}'"})

        def _render_check_sync():
            result_holder = []
            def _run():
                loop = _asyncio.new_event_loop()
                _asyncio.set_event_loop(loop)
                try:
                    r = loop.run_until_complete(check_module_renders(module_name))
                    result_holder.append(r)
                except Exception:
                    pass
                finally:
                    loop.close()
            t = threading.Thread(target=_run, daemon=True)
            t.start()
            t.join(timeout=90)
            return result_holder[0] if result_holder else {"rendered": False, "error_summary": "timeout"}

        def _score(r):
            score = 10 if r.get("rendered") else 0
            score -= len(r.get("console_errors", []))
            score -= len(r.get("functional_failures", [])) * 2
            score -= len(r.get("api_500s", [])) * 3
            score -= len(r.get("api_hang", [])) * 5
            score -= len(r.get("api_422s", []))
            return score

        shutil.copy2(str(tsx_path), str(baseline_path))

        tsx_path.write_text(variant_index_tsx, encoding="utf-8")
        build_out_v = RUN_BUILD_SCRIPT(module_name=module_name)
        variant_render = _render_check_sync()
        variant_score = _score(variant_render)

        shutil.copy2(str(baseline_path), str(tsx_path))
        build_out_b = RUN_BUILD_SCRIPT(module_name=module_name)
        baseline_render = _render_check_sync()
        baseline_score = _score(baseline_render)

        winner = "variant" if variant_score >= baseline_score else "baseline"

        if winner == "variant":
            tsx_path.write_text(variant_index_tsx, encoding="utf-8")
            RUN_BUILD_SCRIPT(module_name=module_name)
            baseline_path.unlink(missing_ok=True)
        else:
            baseline_path.unlink(missing_ok=True)

        return json.dumps({
            "module": module_name,
            "winner": winner,
            "baseline_score": baseline_score,
            "variant_score": variant_score,
            "baseline_rendered": baseline_render.get("rendered"),
            "variant_rendered": variant_render.get("rendered"),
            "baseline_errors": baseline_render.get("console_errors", [])[:5],
            "variant_errors": variant_render.get("console_errors", [])[:5],
            "baseline_functional_failures": baseline_render.get("functional_failures", []),
            "variant_functional_failures": variant_render.get("functional_failures", []),
            "action": f"Kept {winner} — {'variant was better or equal' if winner == 'variant' else 'baseline was better, variant discarded'}.",
        }, indent=2)
    except Exception as e:
        return json.dumps({"module": module_name, "error": str(e)})


AVAILABLE_TOOLS = [
    tool_run_expansion, tool_run_repair, tool_run_integration,
    tool_run_health_check, FS_LIST_DIR, FS_READ_FILE, FS_WRITE_FILE, FS_APPEND_FILE,
    LOAD_PERSONA, postgres_execute, RUN_BUILD_SCRIPT, FS_GET_PROJECT_MAP,
    FS_SEARCH_IN_FILE, FS_READ_FILE_LINES, RUN_RENDER_CHECK_DIAGNOSTIC,
    RUN_MODULE_DIAGNOSTIC, RUN_AB_TEST,
]
