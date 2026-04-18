import os
import json
import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import asdict

from schemas.task_classifier import task_classifier
from schemas.delegation_engine import delegation_engine
from llm_router import call_gemini_with_tools, call_llm_async, stop_all_builds
from persona_logger import narrate
from core.config import Config
from core.protocol import REASONING_PROTOCOL
from task_models import PipelineRequest, PipelineResponse

logger = logging.getLogger("UnifiedOrchestrator")
logger.setLevel(logging.INFO)

class UnifiedOrchestrator:
    """
    The central executive layer of the NewBeginnings AI System.
    Consolidates classification, delegation, and execution into a single, high-fidelity engine.
    Now supports background execution for multi-department multitasking and continuous Daemons.
    """
    def __init__(self):
        self.classifier = task_classifier
        self.delegation = delegation_engine
        self.config = Config()
        self.active_tasks = {} # task_id -> task_status
        self._background_tasks = {} # task_id -> task_object
        self._daemons = {} # daemon_id -> task_object
        self._pending_notifications: Dict[str, list] = {} # session_id -> [messages]
        
        # Async restore daemons — only schedule if an event loop is already running
        # (import-time instantiation happens before uvicorn's loop starts)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._restore_daemons())
        except RuntimeError:
            pass

    async def _restore_daemons(self):
        """Restores active daemons from system state on startup."""
        try:
            from memory_system.memory_core import MemoryEngine
            engine = MemoryEngine()
            states = engine.list_state()
            
            for key, value in states.items():
                if key.startswith("daemon_active_"):
                    daemon_id = key.replace("daemon_active_", "")
                    data = json.loads(value)
                    
                    narrate("Integrity Monitor", f"Restoring persistent daemon: {daemon_id} ({data['assigned_to']})")
                    
                    # Prepare instruction
                    sys_instr = self._build_system_instruction(data["orch_data"]["persona_details"], data["category"], data["is_technical"])
                    
                    # Re-launch loop
                    task = asyncio.create_task(self._run_daemon_loop(
                        daemon_id, data["text"], sys_instr, data["category"], 
                        data["assigned_to"], data["orch_data"], data["is_technical"]
                    ))
                    self._daemons[daemon_id] = task
                    self.active_tasks[daemon_id] = {"status": "RUNNING_DAEMON", "category": data["category"], "assigned_to": data["assigned_to"], "prompt": data["text"]}
                    
        except Exception as e:
            logger.error(f"Failed to restore daemons: {e}")

    async def handle_task(self, text: str, session_id: str = "default", background: bool = False, daemon: bool = False, attachments: List[str] = None, forced_persona: str = None, user_name: str = "default") -> Dict[str, Any]:
        """
        Main entry point for handling any user request.
        Tier 3: Recursive Compaction (Local) integrated for long-term memory.
        """
        text = (text or "").strip()
        if not text and not attachments:
            text = "[empty message — user sent no input]"

        # Tier 3: Prepare memory context
        from memory_system.history_manager import get_history_manager
        history_mgr = get_history_manager(session_id)
        memory_context = history_mgr.get_full_context()
        
        # Inject memory into the current prompt
        original_text = text
        if memory_context:
            text = f"{memory_context}\nCURRENT_USER_INPUT: {text}"

        # 1. INTENT CLASSIFICATION
        category = await self.classifier.classify(original_text)
        narrate("Eliza", f"Classified task as: '{category}'")

        # ... (rest of the logic remains same, but using 'text' for LLM calls)

        # 1.5 AUTO-DETECT DAEMON / BACKGROUND / STOP INTENT
        text_lower = text.lower()

        # Conversational Fast-path: If the classifier explicitly said 'conversational',
        # skip all auto-daemon/background logic to prevent misfires.
        if category == "conversational":
            # Just check for explicit stop commands even in conversational mode
            if text_lower.strip() in ("stop", "stop everything", "cancel"):
                stop_all_builds() # Global signal for sequential loops
                count_bt = len(self._background_tasks)
                count_d = len(self._daemons)
                for tid in list(self._background_tasks.keys()): await self.stop_task(tid)
                for did in list(self._daemons.keys()): await self.stop_daemon(did)
                return {"response": "Standing down. All processes halted.", "status": "STOPPED"}
            
            # DETECT PERSONA NAME IN CONVERSATIONAL PROMPT
            # If the user says "Marcus, why..." it should go to Marcus, not Eliza.
            # CRITICAL: Only scan the user's CURRENT message (original_text), NOT
            # the history-injected 'text'. Scanning chat history causes persona
            # re-routing when the LLM's previous response mentions another persona
            # name (e.g. "I am the System Integrity Monitor").
            target_persona_id = "eliza"
            _user_msg_lower = original_text.lower()
            if self.delegation.loader:
                all_personas = self.delegation.loader.get_all_persona_names()
                sorted_personas = sorted(all_personas, key=lambda p: len(p["name"]), reverse=True)
                
                for p in sorted_personas:
                    pname = p["name"].lower()
                    pid = p["id"].lower()
                    first_name = pname.split()[0] if " " in pname else pname
                    
                    if pname in _user_msg_lower or (len(first_name) > 2 and first_name in _user_msg_lower):
                        target_persona_id = p["id"]
                        narrate("Eliza", f"Persona name detection: routing conversational request to {p['name']}.")
                        break
            
            # Direct conversational path
            orch_data = self._get_orchestration_data(text, category)
            
            # Override delegation if name was detected
            if target_persona_id != "eliza":
                try:
                    p = self.delegation.loader.get_persona(target_persona_id)
                    p_details = p.to_dict() if hasattr(p, "to_dict") else vars(p)
                    orch_data["assigned_to"] = p_details.get("name", target_persona_id)
                    orch_data["persona_details"] = p_details
                except Exception:
                    pass

            persona = orch_data["persona_details"]
            assigned_to = orch_data["assigned_to"]
            sys_instr = self._build_system_instruction(persona, category, False, user_name=user_name)
            return await self._execute_task_direct(text, sys_instr, category, assigned_to, orch_data, False, attachments=attachments, session_id=session_id, user_name=user_name)

        # CRITICAL: Use original_text (user's current message only) for all intent
        # detection below. Using text_lower (which includes chat history) causes
        # false triggers when past conversations mention "stop", "build", etc.
        _user_lower = original_text.lower().strip()

        # STATUS QUERY: "what's running", "what are you working on", "list tasks"
        status_signals = [
            "what's running", "whats running", "what are you working on",
            "what is running", "list tasks", "active tasks", "current tasks",
            "what's happening", "what are you doing", "what's being built",
            "show tasks", "task status", "build status",
        ]
        if any(kw in _user_lower for kw in status_signals):
            return {"response": self._summarize_active_tasks(), "status": "STATUS"}

        # STOP INTENT: natural phrasing, with optional persona targeting
        stop_signals = [
            "stop the build", "stop the task", "stop building", "stop that",
            "cancel the build", "cancel the task", "cancel that", "cancel it",
            "halt the build", "halt that", "abort the build", "abort that",
            "kill the build", "kill that task", "terminate the build",
            "never mind", "nevermind", "forget it", "forget the build",
            "stand down", "pause the build", "stop everything", "stop all",
            "stop stop stop", "kill server", "shut down",
        ]
        if any(kw in _user_lower for kw in stop_signals):
            stop_all_builds()
            if "everything" in _user_lower or "all" in _user_lower or _user_lower == "stop":
                count_bt = len(self._background_tasks)
                count_d = len(self._daemons)
                
                for tid in list(self._background_tasks.keys()):
                    await self.stop_task(tid)
                for did in list(self._daemons.keys()):
                    await self.stop_daemon(did)
                
                return {"response": f"All active processes stopped ({count_bt} tasks, {count_d} daemons). Standing down.", "status": "STOPPED"}

            tid, info = self._find_target_task(_user_lower, status_filter="IN_PROGRESS")
            if tid:
                assigned = info.get("assigned_to", "the builder")
                await self.stop_task(tid)
                return {"response": f"Stopped. {assigned}'s task has been cancelled.", "status": "STOPPED"}
            running_count = sum(1 for i in self.active_tasks.values() if i.get("status") == "IN_PROGRESS")
            if running_count > 1:
                return {"response": f"Multiple tasks are running. Which one?\n{self._summarize_active_tasks()}", "status": "AMBIGUOUS"}
            return {"response": "No active build tasks found.", "status": "IDLE"}

        # UPDATE INTENT: mid-build instruction change, with optional persona targeting
        update_signals = [
            "actually", "instead", "change that to", "change it to",
            "modify that", "modify the build", "update the build", "update that",
            "add to that", "add to the build", "also add", "also include",
            "make it", "make that", "i meant", "correction:",
        ]
        is_update = any(kw in _user_lower for kw in update_signals)
        if is_update:
            tid, info = self._find_target_task(_user_lower, status_filter="IN_PROGRESS")
            if tid:
                old_prompt = self.active_tasks[tid]["prompt"]
                assigned = info.get("assigned_to", "the builder")
                narrate("Eliza", f"Update intent detected — retargeting {assigned} (task {tid[:8]}).")
                await self.stop_task(tid)
                new_text = f"OLD INSTRUCTIONS: {old_prompt}\n\nNEW UPDATE: {text}\n\nCombine these and proceed with the high-fidelity build."
                return await self.handle_task(new_text, background=True, attachments=attachments)
            running_count = sum(1 for i in self.active_tasks.values() if i.get("status") == "IN_PROGRESS")
            if running_count > 1:
                return {"response": f"Multiple tasks running — which one should I update?\n{self._summarize_active_tasks()}", "status": "AMBIGUOUS"}

        # Auto-Daemon: Only activate for explicit persistent/continuous monitoring requests.
        # GUARD: Conversational/Build/Expansion/Patch/Repair tasks must NEVER be auto-daemons.
        # CRITICAL: Use original_text only — scanning chat history causes false triggers
        # when past conversations mention "monitor", "analytics", etc.
        _orig_lower = original_text.lower()
        # Require explicit multi-word intent phrases — single words like "monitor" or "watch"
        # appear in casual conversation and must NOT create persistent LLM-calling daemons.
        daemon_keywords = [
            "run continuously", "keep running", "run 24/7", "always on",
            "start a daemon", "start daemon", "launch daemon",
            "persistent monitor", "continuously monitor", "continuously watch",
            "keep monitoring", "keep watching", "keep tracking",
        ]
        _is_build_task = category in ("build", "expansion", "complex_build", "web_build")
        _is_conversational = category == "conversational"
        _is_maintenance = category in ("patch", "repair")
        if any(kw in _orig_lower for kw in daemon_keywords) and not daemon and not _is_build_task and not _is_conversational and not _is_maintenance:
            daemon = True
            narrate("Eliza", "Executive Decision: Detected monitoring/persistent intent. Auto-activating Daemon mode.")

        # Auto-Background: Build, Create, Generate, Complex
        build_keywords = ["build a", "create a", "generate a", "make a", "new module", "complex build"]
        if any(kw in _orig_lower for kw in build_keywords) and not background and not daemon and not _is_conversational:
            background = True
            narrate("Eliza", "Executive Decision: Detected build/construction intent. Auto-activating Background mode.")

        # 2. DELEGATION & PERSONA SELECTION
        orch_data = self._get_orchestration_data(text, category)
        persona = orch_data["persona_details"]
        assigned_to = orch_data["assigned_to"]

        # If the caller explicitly selected a persona (e.g. from a module chat bubble),
        # override delegation and route directly to that persona for conversational tasks.
        if forced_persona and category not in ("build", "complex_build", "web_build", "expansion", "patch", "repair"):
            try:
                fp = self.delegation.loader.get_persona(forced_persona)
                if fp:
                    fp_details = fp.to_dict() if hasattr(fp, "to_dict") else vars(fp)
                    persona = fp_details
                    assigned_to = fp_details.get("name", forced_persona)
                    orch_data["assigned_to"] = assigned_to
                    orch_data["persona_details"] = fp_details
                    narrate("Eliza", f"Direct persona override: routing to {assigned_to} as requested.")
            except Exception:
                pass

        narrate("Eliza", f"Delegating '{category}' task to {assigned_to} ({persona.get('role', 'Specialist')})")
        
        # 3. TECHNICAL vs CONVERSATIONAL ROUTING
        technical_categories = ["build", "complex_build", "web_build", "expansion", "patch", "repair", "integration", "system", "architecture"]
        # "conversational" is always non-technical regardless of what else is detected
        is_technical = category in technical_categories

        # Prepare System Instruction
        narrate("Marcus Hale", f"Building high-fidelity instruction set for {assigned_to}...")
        sys_instr = self._build_system_instruction(persona, category, is_technical, user_name=user_name)

        if daemon:
            import uuid
            daemon_id = f"daemon_{str(uuid.uuid4())[:8]}"
            self.active_tasks[daemon_id] = {"status": "RUNNING_DAEMON", "category": category, "assigned_to": assigned_to, "prompt": text}
            
            # Initiate a persistent loop
            task = asyncio.create_task(self._run_daemon_loop(daemon_id, text, sys_instr, category, assigned_to, orch_data, is_technical, session_id=session_id))
            self._daemons[daemon_id] = task
            
            # Save daemon state to memory for persistence across restarts
            try:
                from memory_system.memory_core import MemoryEngine
                engine = MemoryEngine()
                import time
                engine.set_state(f"daemon_active_{daemon_id}", json.dumps({
                    "text": text,
                    "category": category,
                    "assigned_to": assigned_to,
                    "orch_data": orch_data,
                    "is_technical": is_technical,
                    "start_time": time.time(),
                    "session_id": session_id
                }))
            except Exception:
                pass
                
            return {
                "daemon_id": daemon_id,
                "status": "DAEMON_STARTED",
                "message": f"Persistent daemon '{category}' for {assigned_to} is now active.",
                "response": f"{assigned_to} is now running continuously for '{original_text[:2000].strip()}'. Send 'stop' to halt it."
            }

        if background:
            import uuid
            task_id = str(uuid.uuid4())
            self.active_tasks[task_id] = {"status": "IN_PROGRESS", "category": category, "assigned_to": assigned_to, "prompt": text}
            
            # Fire and forget into the background
            task = asyncio.create_task(self._execute_task_background(task_id, text, sys_instr, category, assigned_to, orch_data, is_technical, attachments=attachments, session_id=session_id))
            self._background_tasks[task_id] = task
            
            return {
                "task_id": task_id,
                "status": "QUEUED",
                "message": f"Task '{category}' delegated to {assigned_to} is running in the background.",
                "response": f"Delegating to {assigned_to}: '{original_text[:2000].strip()}'. Running in background — I'll report back when done."
            }

        return await self._execute_task_direct(text, sys_instr, category, assigned_to, orch_data, is_technical, attachments=attachments, session_id=session_id, user_name=user_name)

    async def _run_daemon_loop(self, daemon_id: str, text: str, sys_instr: str, category: str, assigned_to: str, orch_data: dict, is_technical: bool, session_id: str = "default"):
        """Continuous execution loop for 'Always-On' monitoring."""
        narrate(assigned_to, f"DAEMON ACTIVATED: Starting continuous monitoring for '{category}'...")
        import time
        
        while daemon_id in self._daemons:
            try:
                # Perform the periodic check/action
                # For daemons, we modify the prompt to focus on 'Current Monitoring State'
                monitoring_prompt = f"DAEMON STATUS CHECK: {text}\n\nPerform your current monitoring cycle. Analyze the latest data and identify any changes or new opportunities. If significant findings occur, report them. Otherwise, confirm 'All systems stable'."
                
                result_data = await self._execute_task_direct(monitoring_prompt, sys_instr, category, assigned_to, orch_data, is_technical, session_id=session_id)
                
                # Update task state with latest result
                self.active_tasks[daemon_id]["last_run"] = time.time()
                self.active_tasks[daemon_id]["last_result"] = result_data["response"]["text"]
                
                # Check for significant findings to share with other departments
                if "significant" in result_data["response"]["text"].lower() or "opportunity" in result_data["response"]["text"].lower():
                    from memory_system.memory_core import MemoryEngine
                    engine = MemoryEngine()
                    engine.share_insight(
                        source=orch_data["persona_details"].get("domain", "general"),
                        target=None, # Public broadcast
                        insight_type="DAEMON_ALERT",
                        content=result_data["response"],
                        metadata={"daemon_id": daemon_id, "category": category}
                    )
                
                # Log heartbeat
                logger.info(f"Daemon {daemon_id} ({assigned_to}) completed monitoring cycle.")
                
            except Exception as e:
                logger.error(f"Daemon {daemon_id} encountered error: {e}")
                await asyncio.sleep(60) # Back off on error
                
            # Configurable wait period (Default 30 minutes for monitoring)
            await asyncio.sleep(1800) 

    async def stop_daemon(self, daemon_id: str):
        """Manually terminates a persistent daemon."""
        if daemon_id in self._daemons:
            task = self._daemons.pop(daemon_id)
            task.cancel()
            self.active_tasks[daemon_id]["status"] = "STOPPED"
            
            # Remove from persistent state
            try:
                from memory_system.memory_core import MemoryEngine
                engine = MemoryEngine()
                engine.delete_state(f"daemon_active_{daemon_id}")
            except Exception:
                pass
                
            narrate("Eliza", f"Daemon {daemon_id} has been successfully terminated.")
            return True
        return False

    async def _execute_task_direct(self, text: str, sys_instr: str, category: str, assigned_to: str, orch_data: dict, is_technical: bool, attachments: List[str] = None, session_id: str = "default", user_name: str = "default") -> Dict[str, Any]:
        """Synchronous execution (waits for result)."""
        from memory_system.history_manager import get_history_manager
        history_mgr = get_history_manager(session_id)
        session_history = history_mgr.get_history()

        if is_technical:
            narrate("Eliza", f"Orchestrating technical action for '{text[:100]}...' via {assigned_to}...")
            result_dict = await call_gemini_with_tools(
                prompt=text,
                system_instruction=sys_instr,
                category=category,
                persona_name=assigned_to,
                clear_history=True,
                attachments=attachments,
                history=session_history
            )
            _user_hist_msg = text.rsplit("CURRENT_USER_INPUT:", 1)[-1].strip() if "CURRENT_USER_INPUT:" in text else text
            history_mgr.add_message("user", _user_hist_msg)
            history_mgr.add_message("assistant", result_dict.get("text", ""), thought_signature=result_dict.get("thought_signature"))
            return {
                "response": result_dict,
                "category": category,
                "assigned_to": assigned_to,
                "status": "COMPLETED",
                "orchestration": orch_data
            }
        
        narrate("Eliza", f"Processing conversational response as {assigned_to}...")
        response_dict = await call_gemini_with_tools(
            prompt=text,
            system_instruction=sys_instr,
            category=category,
            persona_name=assigned_to,
            clear_history=True,
            attachments=attachments,
            history=session_history
        )
        _user_hist_msg = text.rsplit("CURRENT_USER_INPUT:", 1)[-1].strip() if "CURRENT_USER_INPUT:" in text else text
        history_mgr.add_message("user", _user_hist_msg)
        assistant_text = response_dict.get("text", "")
        history_mgr.add_message("assistant", assistant_text, thought_signature=response_dict.get("thought_signature"))

        # Fire async memory extraction for conversational turns if we know who's talking
        if user_name and user_name.lower() not in ("default", "unknown", ""):
            recent_turns = [
                {"role": "user", "content": text},
                {"role": "assistant", "content": assistant_text}
            ]
            try:
                from memory_system.memory_extractor import extract_and_store_memory
                asyncio.create_task(extract_and_store_memory(
                    user_name=user_name,
                    conversation_turns=recent_turns,
                    session_id=session_id
                ))
            except Exception as e:
                logger.debug(f"Memory extraction task could not be scheduled: {e}")

        return {
            "response": response_dict,
            "category": category,
            "assigned_to": assigned_to,
            "status": "OK",
            "orchestration": orch_data
        }

    async def _execute_task_background(self, task_id: str, text: str, sys_instr: str, category: str, assigned_to: str, orch_data: dict, is_technical: bool, attachments: List[str] = None, session_id: str = "default"):
        """Asynchronous execution (runs in background)."""
        try:
            result_data = await self._execute_task_direct(text, sys_instr, category, assigned_to, orch_data, is_technical, attachments=attachments, session_id=session_id)
            self.active_tasks[task_id]["status"] = "COMPLETED"
            self.active_tasks[task_id]["result"] = result_data["response"]
            
            # Log completion to memory
            try:
                from memory_system.memory_core import MemoryEngine
                engine = MemoryEngine()
                engine.log_persona_activity(
                    name=assigned_to,
                    role=orch_data["persona_details"].get("role", "Specialist"),
                    category=category,
                    module="Background Worker",
                    description=f"COMPLETED BACKGROUND TASK: {text[:200]}"
                )
            except Exception:
                pass
                
            narrate("Eliza", f"SUCCESS: Background task {task_id} ({category}) completed by {assigned_to}.")
            # Push a chat notification so the frontend can display build completion
            completion_text = result_data.get("response", "")
            if isinstance(completion_text, dict):
                completion_text = completion_text.get("text", str(completion_text))
            notification_msg = f"✅ {assigned_to} has completed the {category} task. {completion_text[:8000] if completion_text else 'All files written and module is now active.'}"
            if session_id not in self._pending_notifications:
                self._pending_notifications[session_id] = []
            self._pending_notifications[session_id].append({
                "sender": "eliza",
                "text": notification_msg,
                "assigned_to": assigned_to,
            })
        except asyncio.CancelledError:
            narrate("Integrity Monitor", f"Task {task_id} was cancelled by user.")
        except Exception as e:
            logger.error(f"Background task {task_id} failed: {e}")
            self.active_tasks[task_id]["status"] = "FAILED"
            self.active_tasks[task_id]["error"] = str(e)
            narrate("Integrity Monitor", f"CRITICAL: Background task {task_id} failed for {assigned_to}: {str(e)}")
        finally:
            if task_id in self._background_tasks:
                del self._background_tasks[task_id]

    async def stop_task(self, task_id: str):
        """Manually cancels an active background task."""
        if task_id in self._background_tasks:
            task = self._background_tasks[task_id]
            task.cancel()
            self.active_tasks[task_id]["status"] = "STOPPED"
            return True
        return False

    def _find_target_task(self, text_lower: str, status_filter: str = "IN_PROGRESS") -> tuple:
        """
        Find a specific active task by matching persona name words from the user's message.
        Returns (task_id, task_info) or (None, None).
        Falls back to the single active task when only one exists.
        If multiple tasks are active and none match, returns (None, None) so the caller
        can ask the user to clarify.
        """
        active = {tid: info for tid, info in self.active_tasks.items()
                  if info.get("status") == status_filter}
        if not active:
            return None, None

        # Try to match by persona name — split "Marcus Hale" → ["marcus", "hale"]
        for tid, info in active.items():
            assigned = info.get("assigned_to", "").lower().replace("_", " ")
            name_parts = [p for p in assigned.split() if len(p) > 2]
            if any(part in text_lower for part in name_parts):
                return tid, info

        # Also match by category keyword (e.g. "stop web", "stop video", "stop build")
        for tid, info in active.items():
            cat = info.get("category", "").lower().replace("_", " ")
            cat_parts = [p for p in cat.split() if len(p) > 2]
            if any(part in text_lower for part in cat_parts):
                return tid, info

        # Single task — unambiguous, return it
        if len(active) == 1:
            tid = list(active.keys())[0]
            return tid, active[tid]

        # Multiple tasks, no match — caller must handle ambiguity
        return None, None

    def _summarize_active_tasks(self) -> str:
        """Returns a human-readable list of all currently running tasks."""
        running = {tid: info for tid, info in self.active_tasks.items()
                   if info.get("status") in ("IN_PROGRESS", "RUNNING_DAEMON")}
        if not running:
            return "No tasks are currently running."
        lines = []
        for tid, info in running.items():
            label = "Daemon" if info.get("status") == "RUNNING_DAEMON" else "Build"
            lines.append(f"• [{label}] {info.get('assigned_to', 'Unknown')} — {info.get('category', '?')} (id: {tid[:8]})")
        return "Currently running:\n" + "\n".join(lines)

    def _get_orchestration_data(self, task: str, category: str) -> Dict[str, Any]:
        """Maps a category to persona details and instructions (Logic from TaskOrchestrator)."""
        category_clean = category.lower().strip()
        delegation_result = self.delegation.delegate(category)
        
        if isinstance(delegation_result, dict) and "delegate_to" in delegation_result:
            persona_key = delegation_result.get("delegate_to")
            persona = self.delegation.loader.get_persona(persona_key)
            
            persona_details = {}
            if hasattr(persona, "to_dict"):
                persona_details = persona.to_dict()
            elif hasattr(persona, "__dict__"):
                persona_details = {k: v for k, v in vars(persona).items() if not k.startswith('_')}
            else:
                persona_details = {"name": str(persona)}

            response = {
                "task": task,
                "category": category_clean,
                "assigned_to": persona.name if hasattr(persona, "name") else str(persona),
                "persona_details": persona_details
            }
            
            if "rules" in delegation_result:
                response["rules"] = delegation_result["rules"]
            if "instructions" in delegation_result:
                response["instructions"] = delegation_result["instructions"]
                
            return response

        persona = delegation_result
        persona_details = {}
        if hasattr(persona, "to_dict"):
            persona_details = persona.to_dict()
        elif hasattr(persona, "__dict__"):
            persona_details = {k: v for k, v in vars(persona).items() if not k.startswith('_')}
        else:
            persona_details = {"name": str(persona)}

        return {
            "task": task,
            "category": category_clean,
            "assigned_to": persona.name if hasattr(persona, "name") else str(persona),
            "persona_details": persona_details
        }

    def _build_system_instruction(self, persona: dict, category: str, is_technical: bool, user_name: str = "default") -> str:
        """Constructs the persona-specific instructions for the LLM."""
        name = persona.get('name', 'Eliza')
        role = persona.get('role') or persona.get('description', 'AI Assistant')
        domain = persona.get('domain', 'general expertise')
        
        # Load Platform Rules, Reference Links, and Cross-Department Insights
        # Only injected for technical tasks — conversational calls don't need these heavy payloads
        resources_info = ""
        if is_technical:
            try:
                rules_path = os.path.join(self.config.PROJECT_ROOT, "backend", "resources", "rules.md")
                if os.path.exists(rules_path):
                    with open(rules_path, "r", encoding="utf-8") as f:
                        resources_info += f"\n\n### PLATFORM RULES ###\n{f.read()}\n"

                ref_links_path = persona.get("system_resources_path") or os.path.join(
                    self.config.PROJECT_ROOT, "backend", "resources", "reference_links"
                )
                if os.path.exists(ref_links_path):
                    with open(ref_links_path, "r", encoding="utf-8") as f:
                        resources_info += f"\n\n### AUTHORITATIVE REFERENCE LINKS ###\n{f.read()}\n"

            except Exception as e:
                logger.error(f"Failed to load resources: {e}")

        # Cross-department insights injected for all tasks but capped at 3 for chat
        try:
            from memory_system.memory_core import MemoryEngine
            engine = MemoryEngine()
            insight_limit = 5 if is_technical else 2
            insights = engine.get_insights(target_department=domain, limit=insight_limit)
            if insights:
                resources_info += "\n### SHARED CROSS-DEPARTMENT INSIGHTS ###\n"
                for ins in insights:
                    resources_info += f"- [From {ins['source_department']}]: {ins['content']}\n"
        except Exception as e:
            logger.error(f"Failed to load insights: {e}")

        # Persistent memory — person context + platform vision, injected for ALL tasks
        try:
            from memory_system.memory_core import MemoryEngine
            engine = MemoryEngine()
            memory_block = ""

            # Who is this person? Load their full context if we know them
            known_user = user_name if (user_name and user_name.lower() not in ("default", "unknown", "")) else None

            # Fallback: load legacy family_profiles for backwards compatibility
            legacy_profiles = engine.retrieve_context("family_profiles", limit=20)

            if known_user:
                person_ctx = engine.get_full_person_context(known_user)
                if person_ctx:
                    memory_block += f"\n### YOUR MEMORY OF THIS PERSON ###\n{person_ctx}\n"
            elif legacy_profiles:
                memory_block += "\n### KNOWN PEOPLE (from records) ###\n"
                memory_block += "You KNOW these people. Do NOT claim ignorance if they are listed here:\n"
                for p in legacy_profiles:
                    memory_block += f"- {p['relation']}: {p['detail']}\n"

            # Platform vision — always inject so Eliza understands the bigger picture
            vision_entries = engine.get_platform_vision()
            if vision_entries:
                memory_block += "\n### PLATFORM VISION (Jim's documented vision) ###\n"
                memory_block += "This is what the platform is building toward. Reference this when relevant:\n"
                for v in vision_entries:
                    memory_block += f"[{v['category']}]: {v['content']}\n"

            if memory_block:
                resources_info += memory_block + "##################################################\n"
        except Exception as e:
            logger.error(f"Failed to load persistent memory: {e}")

        # Inject full persona profile (contracts, domain expertise, creativity rules)
        # Persona.to_dict() uses 'system_prompt'; raw markdown registry uses 'full_content' — check both.
        persona_profile = persona.get("full_content", "") or persona.get("system_prompt", "")
        persona_section = f"\n\n### YOUR PERSONA PROFILE ###\n{persona_profile}\n" if persona_profile else ""

        # Persona.to_dict() stores tone/style in 'style'; raw markdown registry stores it in 'personality'.
        personality_str = persona.get('style') or persona.get('personality') or 'Professional and direct.'

        base_instr = (
            f"You are {name}, {role}. "
            f"Personality: {personality_str} "
            f"CREATIVITY: You possess a deep sense of creativity within your domain of {domain}. "
            "Apply innovative thinking, aesthetic excellence, and creative problem-solving to all tasks while remaining strictly within your functional boundaries. "
            f"{persona_section}"
            f"{resources_info}"
        )

        if category == "patch":
            patch_protocol = (
                "\n\nPATCH PROTOCOL — TARGETED CHANGE ONLY:\n"
                "You are making a SMALL, SURGICAL change to an existing module. DO NOT rewrite entire files.\n"
                "MANDATORY STEPS — follow in order:\n"
                "1. Use FS_GET_PROJECT_MAP or FS_LIST_DIR to locate the module directory if you are unsure of the path.\n"
                "2. Use FS_READ_FILE to read the current file you need to change.\n"
                "3. Identify ONLY the specific lines that need to change based on the user's request.\n"
                "4. Use FS_WRITE_FILE to save the file with ONLY that targeted change applied — everything else must remain identical.\n"
                "5. After writing, call RUN_BUILD_SCRIPT with the module_name to rebuild ONLY that single module. DO NOT run a full system build.\n"
                "CRITICAL RULES:\n"
                "- DO NOT rewrite the whole file. Surgical precision only.\n"
                "- DO NOT touch files that are not related to the requested change.\n"
                "- DO NOT run a full rebuild. Only RUN_BUILD_SCRIPT(module_name=<the specific module>).\n"
                "- If the change is backend-only (app.py), no rebuild is needed — the server reloads automatically.\n"
            )
            return f"{base_instr}{patch_protocol}\n\n{REASONING_PROTOCOL}"

        if is_technical:
            technical_protocols = (
                f"\n\nTECHNICAL PROTOCOL (Category: {category}):\n"
                "1. NO SKELETONS OR MOCKS: Every file must contain complete, production-ready logic. DO NOT use 'placeholder', 'mock', or 'simulated' logic.\n"
                "2. AMBITION & PRIDE: Treat every build as a high-fidelity masterpiece. Your reputation is tied to the quality of this code.\n"
                "3. THE 100% RULE: 100% functional, 100% complete, 100% integrated. No partial implementations.\n"
                "4. DYNAMIC API KEY EXTRACTION: You MUST extract all API keys, tokens, and endpoints directly from the user's prompt. DO NOT ask for them if they are provided.\n"
                "5. .ENV ENFORCEMENT: All extracted API keys and external config MUST be placed in a .env file. Format: KEY=VALUE. Backend code MUST use os.getenv('KEY') to retrieve them.\n"
                "6. SEQUENTIAL CONSTRUCTION: The system will request each file one-by-one. Provide ONLY the logic for the specific file requested.\n"
                "7. UI/UX: Use Lucide icons and Tailwind. Ensure high-fidelity visuals with Recharts or other libraries for data visualization."
            )
            return f"{base_instr}{technical_protocols}\n\n{REASONING_PROTOCOL}"
        
        conversational_protocols = (
            "\n\nCONVERSATIONAL PROTOCOL:\n"
            "Be helpful, natural, and stay in character. "
            "Do NOT expose internal reasoning or system contracts unless directly relevant. "
            "If the user asks about the system status or files, use your tools to provide accurate info."
        )
        return f"{base_instr}{conversational_protocols}"

# Global instance
unified_orchestrator = UnifiedOrchestrator()
