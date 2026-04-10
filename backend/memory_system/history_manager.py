import json
import logging
import asyncio
from typing import List, Dict, Any
from core.config import Config
from providers.local_qwen_provider import LocalQwenProvider

logger = logging.getLogger("HistoryManager")
config = Config()

class HistoryManager:
    """
    Tier 3: Recursive Compaction (Local).
    Distills long chat history into a structured JSON 'State Object' using Qwen 14B
    when token thresholds are exceeded, maintaining long-term memory at low cost.
    """
    def __init__(self, session_id: str = "default", threshold: int = 10):
        self.session_id = session_id
        self.threshold = threshold
        self.history = []
        self.state_object = {}
        self._compacting = False
        self.local_model = LocalQwenProvider(model_id=config.MODEL_QWEN_14B, port=8001)

    def add_message(self, role: str, content: str, thought_signature: str = None):
        """Tier 3: Mirroring protocol stores thought_signature alongside message text."""
        msg = {"role": role, "content": content}
        if thought_signature:
            msg["thought_signature"] = thought_signature
        self.history.append(msg)
        if len(self.history) >= self.threshold:
            asyncio.create_task(self.compact())

    async def compact(self):
        """Distills history into a State Object using Local Qwen 14B."""
        if self._compacting:
            return
        self._compacting = True
        try:
            await self._do_compact()
        finally:
            self._compacting = False

    async def _do_compact(self):
        logger.info(f"Threshold reached ({len(self.history)}). Initializing Recursive Compaction...")
        
        history_str = json.dumps(self.history, indent=2)
        current_state = json.dumps(self.state_object, indent=2)
        
        system_prompt = (
            "You are a State Compaction Engine. Your task is to distill the provided chat history "
            "and the current state object into a single, highly-dense JSON 'State Object'. "
            "Preserve all critical technical decisions, user preferences, and pending tasks. "
            "Return ONLY the raw JSON object. No preamble, no postamble."
        )
        
        user_prompt = (
            f"CURRENT STATE OBJECT:\n{current_state}\n\n"
            f"NEW HISTORY TO DISTILL:\n{history_str}\n\n"
            "Produce the updated State Object JSON:"
        )
        
        try:
            compacted_json = await self.local_model.generate(system_prompt, user_prompt)
            compacted_json = (compacted_json or "").strip()
            if compacted_json.startswith("```"):
                import re
                compacted_json = re.sub(r'^```(?:json)?\n?', '', compacted_json)
                compacted_json = re.sub(r'\n?```$', '', compacted_json).strip()
            
            if not compacted_json or compacted_json.startswith("Error") or compacted_json.startswith("Exception"):
                logger.error(f"Compaction returned non-JSON response: {compacted_json[:200]}")
                self._fallback_compact()
                return

            self.state_object = json.loads(compacted_json)
            self.history = []
            logger.info("Recursive Compaction successful. State Object updated.")
        except json.JSONDecodeError as e:
            logger.error(f"Compaction failed (invalid JSON): {e}")
            self._fallback_compact()
        except Exception as e:
            logger.error(f"Compaction failed: {e}")
            self._fallback_compact()

    def _fallback_compact(self):
        """Deterministic fallback when AI compaction fails. Keeps the most recent
        messages and builds a minimal state object from the history."""
        keep = max(4, self.threshold // 2)
        old_msgs = self.history[:-keep] if len(self.history) > keep else []
        
        summary_parts = []
        for msg in old_msgs:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:200]
            summary_parts.append(f"{role}: {content}")
        
        if summary_parts:
            prev_summary = self.state_object.get("conversation_summary", "")
            new_summary = prev_summary + "\n" + "\n".join(summary_parts) if prev_summary else "\n".join(summary_parts)
            if len(new_summary) > 4000:
                new_summary = new_summary[-4000:]
            self.state_object["conversation_summary"] = new_summary
        
        self.history = self.history[-keep:]
        logger.info(f"Fallback compaction: kept {len(self.history)} recent messages, summarized {len(old_msgs)} older messages.")

    def get_full_context(self) -> str:
        """Returns the current state object and active history for injection."""
        context = ""
        if self.state_object:
            context += f"### TIER 3: RECURSIVE STATE OBJECT (COMPACTED) ###\n{json.dumps(self.state_object, indent=2)}\n\n"
        
        if self.history:
            context += "### ACTIVE CHAT HISTORY ###\n"
            for msg in self.history:
                sig_info = f" [TS: {msg['thought_signature']}]" if msg.get('thought_signature') else ""
                context += f"{msg['role'].upper()}: {msg['content']}{sig_info}\n"
        
        return context

    def get_history(self) -> List[Dict[str, Any]]:
        """Returns the raw history with signatures for Request Reconstruction."""
        return self.history

# Global registry of managers per session
_managers = {}

def get_history_manager(session_id: str = "default") -> HistoryManager:
    if session_id not in _managers:
        _managers[session_id] = HistoryManager(session_id=session_id)
    return _managers[session_id]
