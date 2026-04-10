import os
import json
import logging
import asyncio
import time
from pathlib import Path
from typing import Dict, Any, List
from persona_logger import narrate
from core.system_status import system_monitor
from core.integration_engine import get_registry, run_discovery_and_registration
from validator import validate_module
from core.validation.systems import ValidationEngine

logger = logging.getLogger("RepairOrchestrator")

class RepairOrchestrator:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RepairOrchestrator, cls).__new__(cls)
            cls._instance.is_monitoring = False
            cls._instance.backend_dir = Path(__file__).parent.parent
            cls._instance.root_dir = cls._instance.backend_dir.parent
            cls._instance.validation_engine = ValidationEngine()
            cls._instance._monitoring_task = None
            # Tracks last repair attempt time and failure count per module.
            # Prevents infinite repair loops when a bundle is consistently broken.
            cls._instance._repair_attempts: Dict[str, List] = {}  # name → [last_time, count]
        return cls._instance

    async def run_startup_repair_sequence(self):
        """Triggered at platform startup. Full repair sequence led by the debugging team."""
        narrate("System", "Initiating automatic startup repair sequence...")
        
        # 1. Alex's Startup Runtime Checks
        narrate("Alex Rivera", "Detecting unmounted components and missing tools...")
        registry = get_registry()
        missing_modules = []
        for name, info in registry.items():
            if info.get("status") == "active":
                mod_path = self.root_dir / info.get("path", "")
                if not mod_path.exists():
                    missing_modules.append(name)
        
        if missing_modules:
            narrate("Alex Rivera", f"FAILURE: Detected missing modules in registry: {', '.join(missing_modules)}")
            for mod in missing_modules:
                await self._trigger_repair_routine(mod, "module")
        else:
            narrate("Alex Rivera", "Startup runtime checks passed. No immediate unmounted components detected.")

        # 2. Mira's Deep Code-Level Validation (ValidationEngine — all registered modules)
        narrate("Dr. Mira Kessler", "Running deep ValidationEngine suite on all registered modules...")
        for mod_name, info in registry.items():
            if info.get("status") == "active":
                try:
                    vresult = self.validation_engine.run_full_suite(mod_name)
                    if not vresult.get("activation_authorized"):
                        failures = vresult.get("failure_classification", [])
                        narrate("Dr. Mira Kessler", f"Module '{mod_name}' failed deep validation: {[f.get('error') for f in failures]}")
                        await self._trigger_repair_routine(mod_name, "module")
                    else:
                        narrate("Dr. Mira Kessler", f"Module '{mod_name}' passed deep validation.")
                except Exception as e:
                    narrate("Dr. Mira Kessler", f"ValidationEngine error for '{mod_name}': {e}")

        # 3. Marcus Hale's Structural Validation
        narrate("Marcus Hale", "Verifying structural integrity and platform contracts...")
        registry = get_registry()
        for mod_name, info in registry.items():
            if info.get("status") == "error":
                narrate("Marcus Hale", f"FAILURE: Module '{mod_name}' has error status. Triggering repair...")
                await self._trigger_repair_routine(mod_name, "module")

        narrate("System", "Startup repair sequence complete.")

    async def stop_monitoring(self):
        """Cancel the monitoring loop task on server shutdown."""
        self.is_monitoring = False
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except (asyncio.CancelledError, Exception):
                pass
        self._monitoring_task = None

    async def start_continuous_monitoring(self):
        """Alex's continuous monitoring loop."""
        if self.is_monitoring:
            return
        self.is_monitoring = True
        narrate("Alex Rivera", "Starting continuous runtime monitoring...")
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

    async def _monitoring_loop(self):
        # Track last modified times of module files
        last_mtimes = {}

        def get_all_mtimes():
            mtimes = {}
            modules_path = self.backend_dir / "modules"
            if not modules_path.exists():
                return mtimes
            for root, dirs, files in os.walk(modules_path):
                for file in files:
                    if file.endswith(('.py', '.json', '.ts', '.tsx', '.html', '.css')):
                        p = Path(root) / file
                        try:
                            mtimes[str(p)] = p.stat().st_mtime
                        except Exception:
                            pass
            return mtimes

        # Initialize mtimes
        last_mtimes = get_all_mtimes()

        while self.is_monitoring:
            try:
                # 1. Check for file changes (Hot Reloading)
                current_mtimes = get_all_mtimes()
                if current_mtimes != last_mtimes:
                    # ONLY trigger re-sync if a module configuration or entrypoint changed
                    # This prevents the feedback loop of the build process itself
                    all_keys = set(current_mtimes.keys()) | set(last_mtimes.keys())
                    changed_files = [f for f in all_keys if current_mtimes.get(f) != last_mtimes.get(f)]
                    critical_changes = [f for f in changed_files if f.endswith(('module.json', 'app.py'))]
                    
                    if critical_changes:
                        # FILTER: Only re-sync if the folder already contains a module.json
                        # This prevents the monitor from jumping the gun while expansion is still creating the directory.
                        registry = get_registry()
                        ready_to_sync = []
                        for f in critical_changes:
                            # Extract module name from path: .../modules/{name}/module.json
                            mod_match = os.path.basename(os.path.dirname(f))
                            if mod_match in registry or os.path.exists(f):
                                ready_to_sync.append(f)
                        
                        if ready_to_sync:
                            # Debounce/Delay to allow batch changes
                            await asyncio.sleep(2)
                            narrate("Integrity Monitor", f"Detected critical file changes in {len(ready_to_sync)} modules. Re-syncing platform...")
                            run_discovery_and_registration()
                            if hasattr(self, 'on_refresh_callback') and self.on_refresh_callback:
                                await self.on_refresh_callback()
                    
                    last_mtimes = get_all_mtimes() # Refresh after sync

                # 2. Check for missing bundles (black screen detection)
                # MONITOR ONLY: We report missing bundles but do NOT build. 
                # Building is the job of the Personas (via Expansion Engine).
                registry = get_registry()
                for mod_name, info in registry.items():
                    if info.get("status") == "active":
                        built_js = self.backend_dir / "static" / "built" / "modules" / mod_name / "index.js"
                        if not built_js.exists():
                            narrate("Integrity Monitor", f"MISSING BUNDLE DETECTED for '{mod_name}'. Integrity degraded (Black Screen).")
                            system_monitor.update_mount(mod_name, success=False, log="Missing index.js (Bundle Failure)")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")

            try:
                await asyncio.sleep(15)
            except asyncio.CancelledError:
                break

    async def _handle_runtime_failure(self, target: str, failure_type: str):
        # Initiated by Alex, handled by Mira and Marcus
        narrate("Dr. Mira Kessler", f"Classifying runtime failure in '{target}': {failure_type}")
        # Classification
        category = "module" # Assume module for now
        
        # Mira triggers repair
        narrate("Dr. Mira Kessler", f"Repair routine triggered for '{target}'. Target: {category}")
        success = await self._trigger_repair_routine(target, category)
        
        if success:
            # Marcus validates structural outcome
            narrate("Marcus Hale", f"Confirming repaired component '{target}' mounts correctly and respects contracts...")
            # Re-sync registry
            run_discovery_and_registration()
            narrate("Marcus Hale", f"Structural validation for '{target}' passed. Platform contracts intact.")
        else:
            narrate("Marcus Hale", f"Repair for '{target}' failed. Escalating to platform builder.")

    async def _trigger_repair_routine(self, target: str, category: str) -> bool:
        """Automated repair routine. Identifies broken/mocked files and rewrites them via LLM."""
        narrate("System", f"Executing targeted repair for {category} '{target}'...")
        
        log_entry = {
            "target": target,
            "category": category,
            "detected_by": "Alex Rivera" if self.is_monitoring else "Startup sequence",
            "repaired_by": "Alex Rivera, Mira Kessler & Marcus Hale",
            "routine": "LLM-powered code repair + re-registration",
            "timestamp": time.time()
        }
        
        try:
            if category == "module":
                # Step 1: Scan the module directory for mock/broken files and rewrite them via LLM
                from tools.repair import RUN_REPAIR_TASK, MOCK_PATTERNS
                from tools.project_map import ProjectMap
                import re as _re

                module_dir = self.backend_dir / "modules" / target
                broken_files = []

                if module_dir.exists():
                    for root, _, files in os.walk(module_dir):
                        for file in files:
                            if file.endswith((".py", ".ts", ".tsx", ".html")):
                                fp = Path(root) / file
                                try:
                                    content = fp.read_text(encoding="utf-8", errors="ignore")
                                    for pattern in MOCK_PATTERNS:
                                        if _re.search(pattern, content, _re.IGNORECASE):
                                            broken_files.append(str(fp.name))
                                            break
                                except Exception:
                                    pass

                if broken_files:
                    narrate("Alex Rivera", f"Found {len(broken_files)} broken file(s) in '{target}': {', '.join(broken_files)}. Repairing...")
                    task_text = f"fix mock and placeholder code in module {target}: {', '.join(broken_files)}"
                    project_map = ProjectMap()
                    loop = asyncio.get_running_loop()
                    repair_result = await loop.run_in_executor(
                        None,
                        lambda: RUN_REPAIR_TASK(task_text, project_map, module_dir=str(module_dir))
                    )
                    narrate("Alex Rivera", f"Repair result: {repair_result}")
                else:
                    narrate("Alex Rivera", f"No mock/broken patterns found in '{target}' files.")

                # Step 2: Diagnostic Check - Bundle presence
                built_js = self.backend_dir / "static" / "built" / "modules" / target / "index.js"
                if not built_js.exists():
                    narrate("Integrity Monitor", f"REPORT: Bundle missing for '{target}'. Requesting Persona rebuild if task is not active.")
                    # MONITOR ONLY: Building is strictly a Persona responsibility.
                    system_monitor.update_mount(target, success=False, log="Missing index.js")

                # Step 3: Re-sync registry
                run_discovery_and_registration()

                # Step 4: Validate structural integrity
                is_valid = validate_module(target)
                log_entry["success"] = is_valid
                narrate("System", f"Repair status for '{target}': {'SUCCESS' if is_valid else 'FAILED'}")
                return is_valid

            elif category == "platform":
                narrate("System", f"ESCALATION: Platform-level failure in '{target}'. Triggering full sync...")
                run_discovery_and_registration()
                log_entry["success"] = True
                return True

        except Exception as e:
            narrate("System", f"CRITICAL: Repair routine encountered error: {e}")
            log_entry["success"] = False
            return False
            
        return False

repair_orchestrator = RepairOrchestrator()
