import os
import re
import asyncio
from pathlib import Path
from tools.project_map import ProjectMap
from persona_logger import narrate

MOCK_PATTERNS = [
    r"random\.randint\(",
    r"random\.choice\(",
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
    
    # 1. ANALYZE TASK for file hints
    words = task_text.replace(",", " ").replace(";", " ").split()
    for word in words:
        if "." in word:
            found = project_map.find_file_by_name(word)
            if found:
                target_files.extend(found)
    
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
        abs_path = root_dir / rel_path
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
                model_name="default",
                prompt=repair_prompt,
                system_instruction=repair_system,
                persona_name="Alex Rivera"
            )
            fixed_content = result.get("text", "").strip()

            # Strip accidental markdown fences
            if fixed_content.startswith("```"):
                fixed_content = re.sub(r'^```(?:[\w]*)?\n?', '', fixed_content)
                fixed_content = re.sub(r'\n?```$', '', fixed_content).strip()

            if fixed_content and len(fixed_content) > 50:
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(fixed_content)
                narrate("Alex Rivera", f"SUCCESS: {rel_path} repaired ({len(fixed_content)} chars).")
                repaired.append(rel_path)
            else:
                narrate("Alex Rivera", f"WARNING: LLM returned empty content for {rel_path}. Skipping.")
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
