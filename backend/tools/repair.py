import os
import re
import asyncio
from pathlib import Path
from tools.project_map import ProjectMap
from persona_logger import narrate

MOCK_PATTERNS = [
    r"TODO:",
    r"FIXME:",
    r"implementation pending",
    r"\bskeleton\b",
    r"\bmock_",
    r"sample data",
    r"example\.com"
]

def RUN_REPAIR_TASK(task_text: str, project_map: ProjectMap = None, module_dir: str = None) -> str:
    """
    Uses ProjectMap to locate broken logic, then calls the LLM to fix ONLY the
    identified issues in each broken file. Targeted repair — does NOT rewrite
    unrelated code. Scope is restricted to module_dir when provided.
    """
    if project_map is None:
        project_map = ProjectMap()
    
    root_dir = Path(project_map.root_dir)
    target_files = []
    
    # 1. ANALYZE TASK for file hints — scoped to module_dir when provided
    _scope_root = Path(module_dir).resolve() if module_dir else None
    words = task_text.replace(",", " ").replace(";", " ").split()
    for word in words:
        if "." in word:
            found = project_map.find_file_by_name(word)
            if found:
                for f in found:
                    abs_f = (root_dir / f).resolve()
                    if _scope_root and not str(abs_f).startswith(str(_scope_root)):
                        narrate("Alex Rivera", f"SCOPE GUARD: Skipping out-of-module file: {f}")
                        continue
                    target_files.append(f)
    
    # 2. SCAN FOR MOCKS — scoped to module_dir only to prevent cross-module contamination
    if "mock" in task_text.lower() or "real" in task_text.lower() or "fix" in task_text.lower():
        narrate("Mira Kessler", "Scanning for mock patterns and placeholders...")
        if module_dir:
            scan_dir = Path(module_dir)
        else:
            scan_dir = root_dir / "backend" / "modules"
        SKIP_DIRS = {"node_modules", "venv", ".git", "__pycache__", "dist", "build"}
        if scan_dir.exists():
            for root, dirs, files in os.walk(scan_dir):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for file in files:
                    if file.endswith((".py", ".ts", ".tsx")):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()
                                for pattern in MOCK_PATTERNS:
                                    if re.search(pattern, content, re.IGNORECASE):
                                        rel_path = os.path.relpath(file_path, root_dir)
                                        target_files.append(rel_path)
                                        break
                        except Exception:
                            continue

    if not target_files:
        return "ERROR: No broken or mocked files identified for repair."

    # Remove duplicates and normalize
    target_files = sorted(list(set([str(f).replace("\\", "/") for f in target_files])))
    narrate("Caleb Monroe", f"Targeting {len(target_files)} files for deep repair and de-mocking.")

    # 3. REPAIR: Read each broken file, call the LLM to rewrite it clean
    repaired = []
    failed = []

    from core.llm_client import call_llm
    from core.config import Config as _RepairConfig

    # Repair calls go to Qwen Plus (fast, precise, no Flash fallbacks).
    # Flash variants are hard-blocked — they produce low-fidelity skeleton
    # patches that are the exact opposite of what targeted repair needs.
    _rcfg = _RepairConfig()
    _repair_model = _rcfg.MODEL_QWEN_PLUS
    _repair_blocked = [
        _rcfg.GEMINI_MODEL_31_FLASH_LITE,
        _rcfg.GEMINI_MODEL_31_FLASH,
        _rcfg.GEMINI_MODEL_30_FLASH,
        _rcfg.GEMINI_MODEL_25_FLASH,
    ]

    repair_system = (
        "You are Alex Rivera, a specialist debugger. "
        "You receive a file containing specific bugs, mocks, or placeholders that need fixing. "
        "Make ONLY the targeted changes required to fix the identified issues. "
        "DO NOT rewrite or rearrange working code. DO NOT change logic that is not broken. "
        "Preserve all existing imports, variable names, function signatures, and structure. "
        "Replace ONLY the specific mock/broken sections with real production logic. "
        "Return ONLY the raw file content with the minimal targeted fix applied. No markdown, no preamble."
    )

    for rel_path in target_files:
        abs_path = (root_dir / rel_path).resolve()
        if _scope_root and not str(abs_path).startswith(str(_scope_root)):
            narrate("Alex Rivera", f"SCOPE GUARD (write): Blocked write to out-of-module path: {rel_path}")
            failed.append(rel_path)
            continue
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                broken_content = f.read()

            repair_prompt = (
                f"TASK: {task_text}\n\n"
                f"FILE: {rel_path}\n\n"
                f"CURRENT CONTENT:\n{broken_content}\n\n"
                "Fix ONLY the specific mock/placeholder/broken sections identified in TASK above. "
                "Keep all working code exactly as-is. Return the complete file with only those targeted fixes applied."
            )

            narrate("Alex Rivera", f"Repairing {rel_path}...")
            result = call_llm(
                model_name=_repair_model,
                prompt=repair_prompt,
                system_instruction=repair_system,
                persona_name="Alex Rivera",
                blocked_models=_repair_blocked,
            )
            fixed_content = result.get("text", "").strip()

            # Strip accidental markdown fences
            if fixed_content.startswith("```"):
                fixed_content = re.sub(r'^```(?:[\w]*)?\n?', '', fixed_content)
                fixed_content = re.sub(r'\n?```$', '', fixed_content).strip()

            _min_size = max(500, int(len(broken_content) * 0.5))
            if fixed_content and len(fixed_content) >= _min_size:
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(fixed_content)
                narrate("Alex Rivera", f"SUCCESS: {rel_path} repaired ({len(fixed_content)} chars).")
                repaired.append(rel_path)
            else:
                narrate("Alex Rivera", f"WARNING: LLM returned truncated/empty content for {rel_path} ({len(fixed_content)} chars vs required {_min_size}). Skipping write to protect file.")
                failed.append(rel_path)

        except Exception as e:
            narrate("Alex Rivera", f"ERROR repairing {rel_path}: {e}")
            failed.append(rel_path)

    summary = f"REPAIR COMPLETE: {len(repaired)} repaired, {len(failed)} failed."
    if repaired:
        summary += f" Repaired: {', '.join(repaired)}."
    if failed:
        summary += f" Failed: {', '.join(failed)}."
    return summary


def RUN_TARGETED_REPAIR_TASK(task_text: str, module_name: str, error_context: str, project_map: ProjectMap = None, module_dir: str = None) -> str:
    """
    Targeted repair using actual runtime error context from the render check.
    Unlike RUN_REPAIR_TASK (which hunts for mock patterns), this function:
    - Receives the exact browser error message (e.g. 'report is not defined at line 3591')
    - Reads the relevant source file(s)
    - Asks the LLM to fix ONLY the specific error described, with full error context
    - Writes back the fixed file
    """
    if project_map is None:
        project_map = ProjectMap()

    root_dir = Path(project_map.root_dir)
    _scope_root = Path(module_dir).resolve() if module_dir else None

    target_files = []
    if module_dir:
        mod_path = Path(module_dir)
        _fe_signals = (
            "react", "jsx", "hook", "useeffect", "usestate", "useref",
            "is not defined", "typeerror", "cannot read properties",
            "rules_compliance", "hooks after early return", "recharts",
            "leaflet", "svg", "component"
        )
        _be_signals = (
            "nameerror", "attributeerror", "fastapi", "route", "app.py",
            "python", "uvicorn", "starlette", "pydantic", "422", "500"
        )
        _err_lower = error_context.lower()
        _is_fe_only = any(s in _err_lower for s in _fe_signals) and not any(s in _err_lower for s in _be_signals)
        _is_be_only = any(s in _err_lower for s in _be_signals) and not any(s in _err_lower for s in _fe_signals)
        for candidate in ["index.tsx", "app.py"]:
            fp = mod_path / candidate
            if not fp.exists():
                continue
            if _is_fe_only and candidate == "app.py":
                narrate("Alex Rivera", f"TARGETED REPAIR: Skipping app.py — error signals are frontend-only ({error_context[:60]})")
                continue
            if _is_be_only and candidate == "index.tsx":
                narrate("Alex Rivera", f"TARGETED REPAIR: Skipping index.tsx — error signals are backend-only ({error_context[:60]})")
                continue
            rel = str(fp.relative_to(root_dir)).replace("\\", "/")
            target_files.append(rel)

    if not target_files:
        words = task_text.replace(",", " ").replace(";", " ").split()
        for word in words:
            if "." in word:
                found = project_map.find_file_by_name(word)
                if found:
                    for f in found:
                        abs_f = (root_dir / f).resolve()
                        if _scope_root and not str(abs_f).startswith(str(_scope_root)):
                            continue
                        target_files.append(f)

    if not target_files:
        return "ERROR: No target files identified for targeted repair."

    target_files = sorted(list(set([str(f).replace("\\", "/") for f in target_files])))
    narrate("Alex Rivera", f"Targeted repair: fixing {len(target_files)} file(s) based on error: {error_context[:100]}")

    from core.llm_client import call_llm
    from core.config import Config as _RepairConfig

    _rcfg = _RepairConfig()
    _repair_model = _rcfg.MODEL_QWEN_PLUS
    _repair_blocked = [
        _rcfg.GEMINI_MODEL_31_FLASH_LITE,
        _rcfg.GEMINI_MODEL_31_FLASH,
        _rcfg.GEMINI_MODEL_30_FLASH,
        _rcfg.GEMINI_MODEL_25_FLASH,
    ]

    repair_system = (
        "You are Alex Rivera, a specialist debugger with deep expertise in React, TypeScript, and Python. "
        "You receive a file along with the EXACT error message that occurred when this file was rendered in a browser. "
        "Your job: find the ROOT CAUSE of the specific error described and fix it with the minimum necessary change. "
        "Rules:\n"
        "- Fix ONLY the specific bug described in the error. Do not refactor unrelated code.\n"
        "- Preserve all existing imports, variable names, function signatures, and structure.\n"
        "- CROSS-SCOPE VARIABLE BUG: When the error is 'X is not defined' and X appears declared with `const X = ...` elsewhere "
        "in the file (inside a different component function or a different .map() callback), that is a CROSS-SCOPE bug — "
        "those other declarations are in separate function scopes and are NOT accessible at the error site. "
        "The fix is to ADD a local declaration of X inside the specific function/callback where the error occurs, "
        "using the same RHS pattern as the sibling declaration. NEVER assume that a `const X = ...` anywhere in the file "
        "makes X available in all other functions — JavaScript has function-level scoping.\n"
        "- For 'X is not defined' where X is truly not declared anywhere: add `const X: any = null;` at the top of the "
        "nearest enclosing component function.\n"
        "- For 'X.toLowerCase is not a function': wrap with String(X ?? '') before calling the method.\n"
        "- For geolocation errors: replace setError(...) callbacks with silent Lebanon KS fallback (lat=39.8283, lon=-98.5795).\n"
        "- Return ONLY the complete raw file content with the targeted fix applied. No markdown, no preamble, no explanation."
    )

    repaired = []
    failed = []

    for rel_path in target_files:
        abs_path = (root_dir / rel_path).resolve()
        if _scope_root and not str(abs_path).startswith(str(_scope_root)):
            narrate("Alex Rivera", f"SCOPE GUARD: Blocked write to {rel_path}")
            failed.append(rel_path)
            continue
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                broken_content = f.read()

            scope_context_lines = []
            if "is not defined" in error_context and rel_path.endswith((".tsx", ".ts")):
                undef_names = re.findall(r'([A-Za-z_$][\w$]*) is not defined', error_context)
                for undef_name in undef_names:
                    found_decls = re.findall(
                        r'[ \t]+const\s+' + re.escape(undef_name) + r'\s*=\s*([^\n;]{1,200})',
                        broken_content, re.MULTILINE
                    )
                    if found_decls:
                        scope_context_lines.append(
                            f"SCOPE NOTE: '{undef_name}' is declared {len(found_decls)} time(s) in SIBLING "
                            f"function scope(s) with RHS: {found_decls[0].strip()[:120]} — "
                            f"these are in different function scopes and NOT accessible at the error site. "
                            f"Add a local declaration inside the specific callback/component where the error occurs."
                        )
            scope_context = ("\n\nSCOPE ANALYSIS:\n" + "\n".join(scope_context_lines)) if scope_context_lines else ""

            repair_prompt = (
                f"MODULE: {module_name}\n"
                f"FILE: {rel_path}\n\n"
                f"EXACT RUNTIME ERROR(S) FROM BROWSER:\n{error_context}\n"
                f"{scope_context}\n\n"
                f"TASK: {task_text}\n\n"
                f"FILE CONTENT ({len(broken_content)} chars):\n{broken_content}\n\n"
                "Fix ONLY the specific error(s) listed above. "
                "Return the complete file with only those targeted fixes applied."
            )

            narrate("Alex Rivera", f"Targeted repair of {rel_path} for error: {error_context[:80]}...")
            result = call_llm(
                model_name=_repair_model,
                prompt=repair_prompt,
                system_instruction=repair_system,
                persona_name="Alex Rivera",
                blocked_models=_repair_blocked,
            )
            fixed_content = result.get("text", "").strip()

            if fixed_content.startswith("```"):
                fixed_content = re.sub(r'^```(?:[\w]*)?\n?', '', fixed_content)
                fixed_content = re.sub(r'\n?```$', '', fixed_content).strip()

            _min_size = max(500, int(len(broken_content) * 0.5))
            if fixed_content and len(fixed_content) >= _min_size:
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(fixed_content)
                narrate("Alex Rivera", f"TARGETED REPAIR SUCCESS: {rel_path} fixed ({len(fixed_content)} chars).")
                repaired.append(rel_path)
            else:
                narrate("Alex Rivera", f"WARNING: LLM returned truncated/empty content for {rel_path} ({len(fixed_content)} chars vs required {_min_size}). Skipping write to protect file.")
                failed.append(rel_path)

        except Exception as e:
            narrate("Alex Rivera", f"ERROR in targeted repair of {rel_path}: {e}")
            failed.append(rel_path)

    summary = f"TARGETED REPAIR COMPLETE: {len(repaired)} repaired, {len(failed)} failed."
    if repaired:
        summary += f" Fixed: {', '.join(repaired)}."
    if failed:
        summary += f" Failed: {', '.join(failed)}."
    return summary
