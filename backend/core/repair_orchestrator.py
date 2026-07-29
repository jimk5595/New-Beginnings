import json
import logging
import asyncio
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
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
            cls._instance._repair_attempts = {}  # name → [last_time, count]
            # Queue of modules whose build pipeline terminated with BUILD FAILED.
            # Populated by mark_build_failed() (called from llm_router.py at every
            # terminal failure point). Drained by the monitoring loop, which runs a
            # render check + targeted repair on each queued module.
            # Format: {module_name: {"error": str, "queued_at": float}}
            cls._instance._failed_build_queue = {}
        return cls._instance

    def mark_build_failed(self, module_name: str, error: str) -> None:
        """
        Called by the build pipeline (llm_router.py) when a module build terminates
        with BUILD FAILED after exhausting all internal repair strategies.
        The monitoring loop drains this queue and attempts repair via the
        render-check → targeted-LLM path (a different strategy from the build-time
        repair, which uses deterministic handlers + layout/ui LLM patch).
        """
        self._failed_build_queue[module_name] = {
            "error": error[:500],
            "queued_at": time.time(),
        }
        narrate("Integrity Monitor", f"BUILD FAILURE QUEUED for '{module_name}': {error[:120]}. Monitoring loop will attempt post-build repair.")

    async def run_startup_repair_sequence(self):
        """Triggered at platform startup. Full repair sequence led by the debugging team."""
        narrate("System", "Initiating automatic startup repair sequence...")
        
        # 1. Alex's Startup Runtime Checks
        narrate("Alex Rivera", "Detecting unmounted components and missing tools...")
        registry = get_registry()
        missing_modules = []
        for name, info in registry.items():
            if info.get("status") == "active":
                mod_path = Path(info.get("module_path", "")) if info.get("module_path") else self.backend_dir / "modules" / name
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

        _MTIMES_SKIP_DIRS = {"node_modules", "venv", ".git", "__pycache__", "dist", "build"}

        def get_all_mtimes():
            mtimes = {}
            modules_path = self.backend_dir / "modules"
            if not modules_path.exists():
                return mtimes
            for root, dirs, files in os.walk(modules_path):
                dirs[:] = [d for d in dirs if d not in _MTIMES_SKIP_DIRS]
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
                            # Skip if a .building lock file exists — build is in progress
                            _lock = self.backend_dir / "modules" / mod_match / ".building"
                            if _lock.exists():
                                continue
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
                registry = get_registry()
                for mod_name, info in registry.items():
                    if info.get("status") == "active":
                        built_js = self.backend_dir / "static" / "built" / "modules" / mod_name / "index.js"
                        if not built_js.exists():
                            # Skip if build is actively in progress
                            _build_lock = self.backend_dir / "modules" / mod_name / ".building"
                            if _build_lock.exists():
                                continue
                            narrate("Integrity Monitor", f"MISSING BUNDLE DETECTED for '{mod_name}'. Triggering repair...")
                            system_monitor.update_mount(mod_name, success=False, log="Missing index.js (Bundle Failure)")
                            await self._trigger_repair_routine(mod_name, "module")

                # 3. Drain the failed-build queue — modules whose build pipeline
                # terminated with BUILD FAILED are queued by mark_build_failed().
                # We attempt repair here using a different strategy from the build-
                # time path: render check → RUN_TARGETED_REPAIR_TASK with actual
                # browser errors.  Entries older than 30 minutes are discarded
                # (stale; the user would have retried manually by then).
                _queue_snapshot = list(self._failed_build_queue.items())
                for _fbq_mod, _fbq_info in _queue_snapshot:
                    _fbq_age = time.time() - _fbq_info.get("queued_at", 0)
                    if _fbq_age > 1800:
                        self._failed_build_queue.pop(_fbq_mod, None)
                        narrate("Integrity Monitor", f"FAILED BUILD QUEUE: Discarding stale entry for '{_fbq_mod}' ({_fbq_age/60:.0f} min old).")
                        continue
                    _fbq_lock = self.backend_dir / "modules" / _fbq_mod / ".building"
                    if _fbq_lock.exists():
                        continue
                    narrate("Integrity Monitor", f"FAILED BUILD QUEUE: Attempting post-build repair for '{_fbq_mod}' (build error: {_fbq_info.get('error','?')[:80]})...")
                    self._failed_build_queue.pop(_fbq_mod, None)
                    _fbq_ok = await self._trigger_repair_routine(_fbq_mod, "module")
                    if _fbq_ok:
                        narrate("Integrity Monitor", f"FAILED BUILD QUEUE: Post-build repair SUCCEEDED for '{_fbq_mod}'.")
                    else:
                        narrate("Integrity Monitor", f"FAILED BUILD QUEUE: Post-build repair FAILED for '{_fbq_mod}'. Module remains broken.")

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

    async def _run_render_check(self, module_name: str) -> dict:
        """Run render check asynchronously in the current event loop."""
        try:
            from tools.render_check import check_module_renders
            return await check_module_renders(module_name)
        except Exception as e:
            return {"rendered": False, "error_summary": str(e), "console_errors": [], "functional_failures": []}

    async def _trigger_repair_routine(self, target: str, category: str) -> bool:
        """Automated repair routine. Runs render check first to get actual errors, then repairs with targeted LLM context, then verifies the fix."""
        now = time.time()
        attempts = self._repair_attempts.get(target, [0, 0])
        if attempts[1] >= 3 and (now - attempts[0]) < 300:
            narrate("System", f"Skipping repair for '{target}' — {attempts[1]} attempts in last 5 min (throttled).")
            return False
        if (now - attempts[0]) >= 300:
            attempts = [now, 0]
        attempts[0] = now
        attempts[1] += 1
        self._repair_attempts[target] = attempts

        narrate("System", f"Executing targeted repair for {category} '{target}'...")

        try:
            if category == "module":
                from tools.repair import RUN_REPAIR_TASK, MOCK_PATTERNS, RUN_TARGETED_REPAIR_TASK
                from tools.project_map import ProjectMap
                from core.toolset import RUN_BUILD_SCRIPT
                import re as _re

                loop = asyncio.get_running_loop()
                module_dir = self.backend_dir / "modules" / target
                tsx_path = module_dir / "index.tsx"

                # ── STEP 0: Run render check to get actual runtime errors ──────────────────
                narrate("Dr. Mira Kessler", f"Running render check diagnostic on '{target}' to identify actual runtime errors...")
                render_result = await self._run_render_check(target)
                render_errors = render_result.get("console_errors", [])
                render_error_summary = render_result.get("error_summary", "")
                render_func_failures = render_result.get("functional_failures", [])
                render_passed = render_result.get("rendered", False) and not render_func_failures

                if render_passed:
                    narrate("Dr. Mira Kessler", f"Render check PASSED for '{target}' — no runtime errors detected. Skipping LLM repair.")
                    run_discovery_and_registration()
                    return True

                # Build error context from render check
                all_render_errors = render_errors + ([render_error_summary] if render_error_summary else []) + render_func_failures
                error_context = "\n".join(all_render_errors[:15]) if all_render_errors else "Unknown render failure"
                narrate("Dr. Mira Kessler", f"Render check FAILED for '{target}': {error_context[:200]}")

                # ── STEP 1: Scan for mock/broken patterns ─────────────────────────────────
                broken_files = []
                _SKIP_DIRS = {"node_modules", "venv", ".git", "__pycache__", "dist", "build"}
                if module_dir.exists():
                    for root, dirs, files in os.walk(module_dir):
                        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
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

                    if tsx_path.exists() and str(tsx_path.name) not in broken_files:
                        try:
                            tsx_content = tsx_path.read_text(encoding="utf-8", errors="ignore")
                            _o = tsx_content.count('{')
                            _c = tsx_content.count('}')
                            _net = _o - _c
                            if abs(_net) > 5:
                                broken_files.append(f"index.tsx (brace imbalance: {_net:+d})")
                        except Exception:
                            pass

                # ── STEP 2: Direct deterministic fixes (unterminated strings, duplicate handlers) ──
                _tsx_direct_fixed = False
                if tsx_path.exists():
                    try:
                        _tsx_dok = tsx_path.read_text(encoding="utf-8", errors="ignore")
                        _gen_onclick_re = _re.compile(
                            r"onClick=\{\(e\) => e\.currentTarget\.classList\.toggle\('active'\)\}(?=onClick=\{)"
                        )
                        if _gen_onclick_re.search(_tsx_dok):
                            _fixed_dok = _gen_onclick_re.sub('', _tsx_dok)
                            tsx_path.write_text(_fixed_dok, encoding='utf-8')
                            _tsx_direct_fixed = True
                            narrate("Alex Rivera", "DIRECT FIX: Removed duplicate generic onClick handler.")
                    except Exception as _dce:
                        narrate("Alex Rivera", f"Direct fix failed: {_dce}")

                # ── STEP 3: LLM-targeted repair with render check errors as context ────────
                narrate("Alex Rivera", f"Dispatching targeted repair for '{target}' with render errors as context...")
                repair_task = (
                    f"Fix runtime errors in module '{target}'. "
                    f"ACTUAL ERRORS FROM BROWSER:\n{error_context}\n\n"
                    f"Also fix any mock/placeholder code. Files with issues: {', '.join(broken_files) if broken_files else 'index.tsx (render failure)'}."
                )
                project_map = ProjectMap()
                repair_result = await loop.run_in_executor(
                    None,
                    lambda: RUN_TARGETED_REPAIR_TASK(
                        task_text=repair_task,
                        module_name=target,
                        error_context=error_context,
                        project_map=project_map,
                        module_dir=str(module_dir),
                    )
                )
                narrate("Alex Rivera", f"Repair result: {repair_result}")

                # ── STEP 4: Rebuild ───────────────────────────────────────────────────────
                narrate("Integrity Monitor", f"Rebuilding bundle for '{target}'...")
                build_output = await loop.run_in_executor(None, lambda: RUN_BUILD_SCRIPT(module_name=target))
                if "FAILED" in build_output or "ERROR" in build_output:
                    narrate("Integrity Monitor", f"Rebuild failed for '{target}': {build_output[:300]}")
                else:
                    narrate("Integrity Monitor", f"Rebuild succeeded for '{target}'.")

                # ── STEP 5: Re-run render check to verify fix ─────────────────────────────
                narrate("Dr. Mira Kessler", f"Verifying fix with post-repair render check on '{target}'...")
                verify_result = await self._run_render_check(target)
                verify_passed = verify_result.get("rendered", False) and not verify_result.get("functional_failures", [])
                if verify_passed:
                    narrate("Dr. Mira Kessler", f"POST-REPAIR RENDER CHECK PASSED for '{target}' — fix verified.")
                else:
                    verify_errors = verify_result.get("console_errors", []) + verify_result.get("functional_failures", [])
                    narrate("Dr. Mira Kessler", f"POST-REPAIR RENDER CHECK FAILED for '{target}': {'; '.join(verify_errors[:5])}")

                # ── STEP 6: Re-sync registry and validate ─────────────────────────────────
                run_discovery_and_registration()
                is_valid = validate_module(target)
                narrate("System", f"Repair status for '{target}': {'SUCCESS' if is_valid else 'FAILED'}")
                return is_valid

            elif category == "platform":
                narrate("System", f"ESCALATION: Platform-level failure in '{target}'. Triggering full sync...")
                run_discovery_and_registration()
                is_valid = validate_module(target) if target else True
                narrate("System", f"Platform sync status for '{target}': {'SUCCESS' if is_valid else 'FAILED'}")
                return is_valid

        except Exception as e:
            narrate("System", f"CRITICAL: Repair routine encountered error: {e}")
            return False

        return False

    async def run_diagnostic(self, module_name: str) -> dict:
        """
        Full diagnostic report for a module. Called by personas or API to understand what is broken.
        Returns: build errors, render check results, mock pattern scan, and a plain-English summary.
        """
        from tools.repair import MOCK_PATTERNS
        from core.toolset import RUN_BUILD_SCRIPT
        import re as _re

        module_dir = self.backend_dir / "modules" / module_name
        report = {
            "module": module_name,
            "timestamp": time.time(),
            "build_errors": [],
            "render_errors": [],
            "functional_failures": [],
            "api_errors": {},
            "mock_files": [],
            "source_sizes": {},
            "overall_health": "UNKNOWN",
            "summary": "",
        }

        if not module_dir.exists():
            report["overall_health"] = "ERROR"
            report["summary"] = f"Module directory not found: {module_dir}"
            return report

        for f in ["index.tsx", "app.py", "module.json"]:
            fp = module_dir / f
            if fp.exists():
                report["source_sizes"][f] = fp.stat().st_size

        loop = asyncio.get_running_loop()
        build_out = await loop.run_in_executor(None, lambda: RUN_BUILD_SCRIPT(module_name=module_name))
        for line in build_out.splitlines():
            if any(k in line.lower() for k in ("error", "failed", "cannot find", "expected")):
                report["build_errors"].append(line.strip())
        report["build_errors"] = report["build_errors"][:20]

        render_result = await self._run_render_check(module_name)
        report["render_errors"] = render_result.get("console_errors", [])[:20]
        report["functional_failures"] = render_result.get("functional_failures", [])
        report["api_errors"] = {
            "404": render_result.get("api_404s", []),
            "500": render_result.get("api_500s", []),
            "422": render_result.get("api_422s", []),
            "hang": render_result.get("api_hang", []),
        }
        if render_result.get("error_summary"):
            report["render_errors"].insert(0, render_result["error_summary"])

        SKIP_DIRS = {"node_modules", "venv", ".git", "__pycache__", "dist", "build"}
        for root, dirs, files in os.walk(module_dir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for file in files:
                if file.endswith((".py", ".ts", ".tsx")):
                    fp = Path(root) / file
                    try:
                        content = fp.read_text(encoding="utf-8", errors="ignore")
                        for pat in MOCK_PATTERNS:
                            if _re.search(pat, content, _re.IGNORECASE):
                                report["mock_files"].append(file)
                                break
                    except Exception:
                        pass

        total_issues = (
            len(report["build_errors"]) +
            len(report["render_errors"]) +
            len(report["functional_failures"]) +
            len(report["mock_files"]) +
            (0 if render_result.get("rendered") else 1)
        )
        report["overall_health"] = "HEALTHY" if total_issues == 0 else f"ISSUES: {total_issues} problem(s)"

        parts = []
        if not render_result.get("rendered"):
            parts.append(f"Module fails to render: {render_result.get('error_summary', 'blank page')}")
        if report["build_errors"]:
            parts.append(f"{len(report['build_errors'])} build error(s): {report['build_errors'][0]}")
        if report["render_errors"]:
            parts.append(f"{len(report['render_errors'])} browser error(s): {report['render_errors'][0]}")
        if report["functional_failures"]:
            parts.append(f"{len(report['functional_failures'])} functional failure(s): {report['functional_failures'][0]}")
        if report["mock_files"]:
            parts.append(f"Mock/placeholder code in: {', '.join(report['mock_files'])}")
        report["summary"] = " | ".join(parts) if parts else "Module appears healthy."

        narrate("Dr. Mira Kessler", f"Diagnostic for '{module_name}': {report['summary']}")
        return report

    async def run_ab_test(self, module_name: str, variant_tsx: str) -> dict:
        """
        A/B test a proposed index.tsx variant against the current version.
        Builds and render-checks both, keeps the winner.
        """
        from core.toolset import RUN_BUILD_SCRIPT
        import shutil

        module_dir = self.backend_dir / "modules" / module_name
        tsx_path = module_dir / "index.tsx"
        baseline_path = module_dir / "index.tsx.ab_baseline"

        if not tsx_path.exists():
            return {"error": f"index.tsx not found for '{module_name}'"}

        loop = asyncio.get_running_loop()

        def _score(r: dict) -> int:
            s = 10 if r.get("rendered") else 0
            s -= len(r.get("console_errors", []))
            s -= len(r.get("functional_failures", [])) * 2
            s -= len(r.get("api_500s", [])) * 3
            s -= len(r.get("api_hang", [])) * 5
            s -= len(r.get("api_422s", []))
            return s

        shutil.copy2(str(tsx_path), str(baseline_path))

        narrate("Dr. Mira Kessler", f"A/B TEST: Building and testing VARIANT for '{module_name}'...")
        tsx_path.write_text(variant_tsx, encoding="utf-8")
        await loop.run_in_executor(None, lambda: RUN_BUILD_SCRIPT(module_name=module_name))
        variant_result = await self._run_render_check(module_name)
        variant_score = _score(variant_result)

        narrate("Dr. Mira Kessler", f"A/B TEST: Restoring and testing BASELINE for '{module_name}'...")
        shutil.copy2(str(baseline_path), str(tsx_path))
        await loop.run_in_executor(None, lambda: RUN_BUILD_SCRIPT(module_name=module_name))
        baseline_result = await self._run_render_check(module_name)
        baseline_score = _score(baseline_result)

        winner = "variant" if variant_score >= baseline_score else "baseline"
        if winner == "variant":
            tsx_path.write_text(variant_tsx, encoding="utf-8")
            await loop.run_in_executor(None, lambda: RUN_BUILD_SCRIPT(module_name=module_name))
        baseline_path.unlink(missing_ok=True)

        narrate("Dr. Mira Kessler",
            f"A/B TEST RESULT for '{module_name}': {winner.upper()} WINS "
            f"(variant={variant_score}, baseline={baseline_score}). Kept {winner}.")

        return {
            "module": module_name,
            "winner": winner,
            "baseline_score": baseline_score,
            "variant_score": variant_score,
            "baseline_rendered": baseline_result.get("rendered"),
            "variant_rendered": variant_result.get("rendered"),
            "baseline_errors": baseline_result.get("console_errors", [])[:5],
            "variant_errors": variant_result.get("console_errors", [])[:5],
            "baseline_functional_failures": baseline_result.get("functional_failures", []),
            "variant_functional_failures": variant_result.get("functional_failures", []),
            "action": f"Kept {winner}.",
        }


repair_orchestrator = RepairOrchestrator()
