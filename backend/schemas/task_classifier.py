# task_classifier.py
# Deterministically classifies tasks into lifecycle-aware categories.

import re
from typing import Dict

class TaskClassifier:
    def __init__(self):
        self.keyword_map = self._build_keyword_map()

    # ---------------------------------------------------------
    # KEYWORD → CATEGORY MAP (FALLBACK ONLY)
    # ---------------------------------------------------------
    def _build_keyword_map(self) -> Dict[str, str]:
        # These are ONLY used as a last resort,
        # after lifecycle / error / system-aware checks.
        return {
            "api": "backend",
            "database": "backend",
            "db": "backend",
            "endpoint": "backend",

            "ui": "frontend",
            "button": "frontend",
            "component": "frontend",
            "react": "frontend",

            "integration": "integration",
            "connect": "integration",
            "hook up": "integration",
            "add to dashboard": "integration",

            "status": "system",
            "system state": "system",
            "system status": "system",

            "debug": "debugging",
            "stack trace": "debugging",
            "traceback": "debugging",
            "log": "debugging",
        }

    # ---------------------------------------------------------
    # CLASSIFY TASK (ASYNC)
    # ---------------------------------------------------------
    async def classify(self, task: str) -> str:
        """
        Returns the category of a task based on intent, lifecycle,
        and error context. Defaults to 'debugging' for system/log text.
        If ambiguous, uses Gemini for deep reasoning classification.
        """
        task_lower = task.lower().strip()

        # 0. CONVERSATIONAL FAST-PATH — only scan the first 300 chars so long build
        #    prompts with embedded words like "explain" don't get misclassified.
        task_head = task_lower[:300]
        conversational_signals = [
            # Questions & opinions
            "what do you think", "how does it look", "can you explain", "how to",
            "why did you", "why are you", "what are you doing", "tell me about",
            "can you describe", "what is your", "how would you", "who are you",
            "what's happening", "help me understand", "walk me through",
            "do you think", "thoughts on", "give me your", "is it possible",
            "how are you", "what's your take", "what does this mean",
            "can you chat", "let's talk", "i have a question", "quick question",
            "how long", "estimate", "roadmap", "strategy", "plan for",
            # Evaluation / review / discussion
            "is this acceptable", "is that acceptable", "is it acceptable",
            "was that acceptable", "was this acceptable",
            "is this okay", "is that okay", "is this good", "is that good",
            "does this look", "does that look", "what about", "should i",
            "should we", "can we", "would it be", "would you recommend",
            "what's wrong", "what went wrong", "why is it", "why isn't",
            "why doesn't", "why won't", "what happened", "what's the issue",
            "review this", "review that", "evaluate", "assess", "check this",
            "look at this", "look at that", "is there a problem", "any issues",
            "is eliza", "are you", "did you", "have you", "was eliza",
            "can eliza", "will eliza", "why did eliza", "why is eliza",
            # Brainstorming / hypothetical
            "imagine", "what if", "hypothetically", "let's say", "suppose",
            "could we", "might it be", "wonder if",
            # Intent to discuss, not build
            "i want to understand", "i want to know", "i want to check",
            "i want to ask", "i want to talk", "i want to discuss",
            "i want to see", "i want to review", "i want to find out",
            "tell me", "explain to me", "show me how", "walk me through",
            # Explicit chat / no-build signals
            "just chatting", "just chat", "just talking", "just talk",
            "do not build", "don't build", "dont build",
            "no building", "not building", "we are just",
            "what do you suggest", "what do you recommend",
            "what inspired", "what do you think about",
        ]
        if any(s in task_head for s in conversational_signals) or "?" in task_head:
            return "conversational"

        # 1. HARD ROUTES (Rules-based for speed)
        # Build guard / validation / schema / module.json / entrypoint
        repair_triggers = [
            "build guard failure",
            "build guard violations found",
            "build aborted",
            "schema error",
            "schema violation",
            "module.json",
            "entrypoint",
            "failed validation",
            "validation failed",
            "could not load module entrypoint spec",
            "missing file",
            "mandatory files missing",
            "failed: could not load module",
            "failed: could not load module entrypoint",
        ]
        if any(kw in task_lower for kw in repair_triggers):
            return "repair"

        # Explicit analysis/reporting intent (HIGHEST PRIORITY after repairs)
        analysis_triggers = [
            "analyze the system", "analyze code", "analyze files", "check the code", 
            "find the problem", "report back", "tell me why", "investigate", 
            "dont make changes", "do not make changes", "just report", "can you analyze",
            "report on the system", "system report", "check the status"
        ]
        if any(kw in task_lower for kw in analysis_triggers) and not any(kw in task_lower[:100] for kw in ["build a ", "build the ", "create a ", "create the ", "generate a ", "generate the "]):
            return "system"

        # Explicit build success/failure logs
        build_log_triggers = [
            "--- starting build process ---",
            "running build guard",
            "building frontend core",
            "building modules",
            "build complete",
            "esbuild pipeline",
        ]
        if any(kw in task_lower for kw in build_log_triggers):
            return "build"

        # Generic error / traceback / log noise → debugging/repair
        if any(kw in task_lower for kw in ["traceback", "exception", "error:", "failed", "failure"]):
            # If it's clearly about modules / build / schema, treat as repair
            if any(kw in task_lower for kw in ["module", "module.json", "build", "schema", "entrypoint"]):
                return "repair"
            return "debugging"

        # If it looks like raw logs (INFO:/WARNING:/ERROR:) → debugging
        if any(prefix in task_lower for prefix in ["info:", "warning:", "error:", "debug:"]):
            return "debugging"

        # 2. EXPLICIT USER INTENT: TARGETED PATCH (small, specific change to existing module)
        patch_intent = [
            "tweak", "small change", "minor change", "quick change",
            "just change", "just update", "only change", "only update",
            "change the color", "change the style", "change the text",
            "change the label", "change the font", "change the icon",
            "update the header", "update the footer", "update the button",
            "update the title", "update the nav", "update the sidebar",
            "adjust the", "modify the",
        ]
        patch_blockers = ["new module", "rebuild", "new feature", "create a", "build a", "generate a"]
        if any(kw in task_lower for kw in patch_intent) and not any(kw in task_lower for kw in patch_blockers):
            return "patch"

        # 2b. EXPLICIT USER INTENT: REPAIR / FIX
        repair_intent = [
            "fix this", "fix that", "repair this", "repair that",
            "fix the module", "repair the module", "fix the build",
            "repair the build", "fix the json", "repair the json",
            "fix module.json", "repair module.json", "fix the error",
            "repair the error",
        ]
        if any(kw in task_lower for kw in repair_intent):
            return "repair"

        # 3. EXPLICIT USER INTENT: BUILD / REBUILD
        build_intent = [
            "run the build", "run build", "rebuild", "build the project",
            "build the frontend", "build the backend", "execute build script",
            "execute script", "run esbuild", "start the build", "build process",
            "build a ", "build the ", "create a ", "create the ", "generate a ", "generate the "
        ]
        if any(kw in task_lower for kw in build_intent):
            return "build"

        # 4. EXPLICIT USER INTENT: EXPANSION / NEW MODULE
        # ONLY trigger if the prompt starts with a build command or contains an unambiguous build verb.
        # This prevents "how long will your engineering team take" from triggering a build.
        build_prefixes = ["build ", "create ", "generate ", "make ", "setup ", "start "]
        is_explicit_build = any(task_lower.startswith(p) for p in build_prefixes)

        if ("software engineer" in task_lower or "engineering team" in task_lower) and is_explicit_build:
            return "complex_build"
        
        if ("web development" in task_lower or "web dev" in task_lower or "dropshipping" in task_lower or "store" in task_lower) and is_explicit_build:
            return "web_build"

        expansion_intent = [
            "create a new module", "make a new module", "add a new module",
            "expand this module", "add a feature", "add new feature",
            "extend this", "expansion task", "expansion plan",
            "build a complete", "build a new", "create a module",
            "start expansion", "build a polished", "build a module",
        ]
        if any(kw in task_lower for kw in expansion_intent):
            return "expansion"

        # 5. EXPLICIT USER INTENT: INTEGRATION
        integration_intent = [
            "integrate this", "hook this up", "connect this",
            "wire this into the dashboard", "add to dashboard",
            "expose this in the ui",
        ]
        if any(kw in task_lower for kw in integration_intent):
            return "integration"

        # 6. BACKEND / FRONTEND SPECIFIC
        if any(kw in task_lower for kw in ["api endpoint", "backend route", "fastapi", "python api", "service layer"]):
            return "backend"

        if any(kw in task_lower for kw in ["react component", "tsx", "frontend view", "ui component", "dashboard tile"]):
            return "frontend"

        # 7. SYSTEM / STATUS
        if any(kw in task_lower for kw in ["system status", "system state", "what is running", "what modules are loaded", "list modules"]):
            return "system"

        # 8. FALLBACK KEYWORD MAP (SOFT HINTS)
        # Use word boundary matching to prevent substring false positives
        # (e.g. "ui" matching inside "build", "require", etc.)
        for keyword, category in self.keyword_map.items():
            if re.search(rf'\b{re.escape(keyword)}\b', task_lower):
                return category

        # 9. GEMINI FALLBACK (For complex or vague requests)
        try:
            from llm_router import call_llm_async
            from core.config import Config
            config = Config()
            prompt = f"Classify this task into one category: conversational, build, expansion, patch, repair, integration, backend, frontend, system, debugging, or executive. Use 'patch' for small targeted changes to existing modules (tweak, adjust, change X in module Y). TASK: {task}"
            instr = "You are a high-speed intent classifier. Return ONLY the category name in lowercase. Use 'conversational' for any chat, questions, opinions, or discussion that is not a technical action. Use 'patch' for small targeted changes to existing module files."
            ai_res = await call_llm_async(config.GEMINI_MODEL_31_FLASH_LITE, prompt, system_instruction=instr)
            ai_res = ai_res.get("text", "").strip().lower()
            if ai_res in ["conversational", "build", "expansion", "patch", "repair", "integration", "backend", "frontend", "system", "debugging", "executive"]:
                return ai_res
        except:
            pass

        # 10. FINAL FALLBACKS
        if any(kw in task_lower for kw in ["module", "build", "json", "schema", "entrypoint", "uvicorn", "fastapi"]):
            return "debugging"

        # Default to conversational — Eliza will ask if the intent is unclear.
        # Never assume build intent for ambiguous requests.
        return "conversational"


# ---------------------------------------------------------
# GLOBAL INSTANCE
# ---------------------------------------------------------
task_classifier = TaskClassifier()
print("CLASSIFIER LOADED FROM:", __file__)
