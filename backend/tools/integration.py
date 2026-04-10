import os
import re
import json
import sys
import subprocess
from pathlib import Path
from tools.project_map import ProjectMap
from persona_logger import narrate

def RUN_INTEGRATION_TASK(task_text: str, project_map: ProjectMap = None, module_name: str = None) -> str:
    """
    Unified Integration: Build, Validate, and Register using core engine.
    """
    if project_map is None:
        project_map = ProjectMap()
    
    root_path = Path(project_map.root_dir)
    backend_dir = root_path / "backend"
    manifest_path = backend_dir / "system_manifest.json"

    if not module_name:
        match = re.search(r'(?:integrate|validate|build)\s+([a-z0-9\-_]+)', task_text.lower())
        module_name = match.group(1) if match else None

    if not module_name:
        return "ERROR: No module name provided for integration."

    narrate("Juniper Ryle", f"Starting integration for: {module_name}")

    # 0. Seed personas into manifest BEFORE build.py runs.
    #    Priority: extracted .md files > existing manifest entry.
    #    build.py reads the manifest to inject the chat bubble.
    try:
        with open(manifest_path, "r", encoding="utf-8") as _f:
            _manifest = json.load(_f)
        existing_mod = _manifest.get("modules", {}).get(module_name, {})

        # Check if extracted .md persona files exist for this module
        _persona_dir = backend_dir / "personas" / module_name
        _extracted = []
        if _persona_dir.exists():
            for _md in sorted(_persona_dir.glob("*.md")):
                _txt = _md.read_text(encoding="utf-8", errors="replace")
                _pn, _pr = "", ""
                for _ln in _txt.splitlines():
                    if _ln.startswith("Name:") and not _pn:
                        _pn = _ln.split(":", 1)[1].strip()
                    if _ln.startswith("Role:") and not _pr:
                        _pr = _ln.split(":", 1)[1].strip()
                if _pn and _pr:
                    _pid = re.sub(r'[^a-z0-9]+', '_', _pn.lower()).strip('_')
                    _extracted.append({"id": _pid, "name": _pn, "role": _pr})

        _seed_personas = _extracted or existing_mod.get("personas") or []
        _manifest.setdefault("modules", {})[module_name] = {
            **existing_mod,
            "name": existing_mod.get("name", module_name),
            "status": "active",
            "personas": _seed_personas,
        }
        with open(manifest_path, "w", encoding="utf-8") as _f:
            json.dump(_manifest, _f, indent=4)
        _src = f"personas/{module_name}/ ({len(_extracted)} files)" if _extracted else "none found"
        narrate("Naomi Kade", f"Pre-seeded {len(_seed_personas)} persona(s) for '{module_name}' from {_src}.")
    except Exception as _pe:
        narrate("Naomi Kade", f"Non-fatal: could not pre-seed personas: {_pe}")

    # 1. Run Build Script (esbuild + file sync)
    try:
        creation_flags = 0x08000000 if os.name == 'nt' else 0
        proc = subprocess.run(
            [sys.executable, str(backend_dir / "build.py"), "--module", module_name],
            capture_output=True,
            text=True,
            creationflags=creation_flags,
            timeout=300
        )
        # Always surface build output so failures are visible in server logs
        if proc.stdout and proc.stdout.strip():
            for line in proc.stdout.strip().splitlines():
                narrate("Integrity Monitor", f"[build] {line}")
        if proc.stderr and proc.stderr.strip():
            for line in proc.stderr.strip().splitlines():
                narrate("Integrity Monitor", f"[build:err] {line}")

        built_js = root_path / "backend" / "static" / "built" / "modules" / module_name / "index.js"
        if proc.returncode != 0 or not built_js.exists():
            reason = "esbuild exited non-zero" if proc.returncode != 0 else "index.js not produced"
            err_detail = ((proc.stdout or "") + (proc.stderr or ""))[:600].strip()
            narrate("Dr. Mira Kessler", f"CRITICAL: Build failed for '{module_name}' — {reason}. Detail: {err_detail}")
            return f"ERROR: Bundle failed for {module_name} ({reason}). Detail: {err_detail}"
        narrate("Juniper Ryle", f"Build successful for {module_name}")
    except subprocess.TimeoutExpired:
        return f"ERROR: Build timed out for {module_name} (esbuild > 300s). Module files are on disk — run build.py manually."
    except Exception as e:
        return f"ERROR: Build failed for {module_name}: {e}"

    # 2. Use IntegrationEngine for discovery, validation, and registration
    try:
        from core.integration_engine import run_discovery_and_registration, get_registry
        
        # Trigger core engine re-scan
        run_discovery_and_registration()
        
        registry = get_registry()
        if module_name not in registry:
            return f"ERROR: Module {module_name} failed core integration (check logs for Dr. Mira Kessler)."
        
        mod_info = registry[module_name]
        if mod_info.get("status") == "error":
            return f"ERROR: Module {module_name} failed validation during integration."

        # 3. Update system_manifest.json for persistence
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        existing = manifest.get("modules", {}).get(module_name, {})

        # Priority: 1) Extracted .md files in backend/personas/<module_name>/
        #           2) Personas from module.json (mod_info)
        #           3) Existing manifest entry (preserved across re-builds)
        #           4) Empty list — never inject unrelated system personas
        persona_dir = backend_dir / "personas" / module_name
        extracted_personas = []
        if persona_dir.exists():
            for md_file in sorted(persona_dir.glob("*.md")):
                md_text = md_file.read_text(encoding="utf-8", errors="replace")
                p_name = ""
                p_role = ""
                for line in md_text.splitlines():
                    if line.startswith("Name:") and not p_name:
                        p_name = line.split(":", 1)[1].strip()
                    if line.startswith("Role:") and not p_role:
                        p_role = line.split(":", 1)[1].strip()
                if p_name and p_role:
                    p_id = re.sub(r'[^a-z0-9]+', '_', p_name.lower()).strip('_')
                    extracted_personas.append({"id": p_id, "name": p_name, "role": p_role})
            if extracted_personas:
                narrate("Naomi Kade", f"Using {len(extracted_personas)} extracted persona(s) from personas/{module_name}/ for chat bubble.")

        resolved_personas = (
            extracted_personas
            or mod_info.get("personas")
            or existing.get("personas")
            or []
        )

        manifest.setdefault("modules", {})[module_name] = {
            "name": mod_info.get("name", module_name),
            "description": mod_info.get("description", ""),
            "path": f"backend/modules/{module_name}",
            "entrypoint": mod_info.get("entrypoint", "app.py"),
            "ui_link": mod_info.get("ui_link", "index.html"),
            "status": "active",
            "personas": resolved_personas,
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=4)
            
        # 4. Mount routes on the live app
        try:
            import sys as _sys
            _main = _sys.modules.get("__main__")
            if _main and hasattr(_main, "load_modules_from_registry"):
                _main.load_modules_from_registry()
                narrate("Isaac Moreno", f"Routes live: /api/{module_name} is now mounted via __main__.")
            else:
                # Fallback: Try to hit the local refresh endpoint if the server is running
                try:
                    import httpx
                    # Use a short timeout so we don't hang if the server is not up
                    with httpx.Client(timeout=2.0) as client:
                        resp = client.get("http://127.0.0.1:8000/api/system/refresh")
                        if resp.status_code == 200:
                            narrate("Isaac Moreno", f"Routes live: /api/{module_name} is now mounted via API refresh.")
                        else:
                            narrate("Isaac Moreno", f"Route mount warning: API refresh returned {resp.status_code}")
                except Exception as _httpe:
                    narrate("Isaac Moreno", f"Route mount info: Could not reach live API for refresh (expected if server is starting).")
        except Exception as _e:
            narrate("Isaac Moreno", f"Route mount warning (non-fatal): {_e}")

        narrate("Dr. Mira Kessler", f"SUCCESS: '{module_name}' is now fully integrated and registered.")
        return f"SUCCESS: Integrated {module_name}"

    except Exception as e:
        logger_err = f"ERROR: Integration engine failed: {e}"
        narrate("Dr. Mira Kessler", logger_err)
        return logger_err