# eliza_orchestrator.py
# Eliza's executive layer: understands natural language, classifies tasks,
# delegates them, and responds conversationally.

from typing import Dict, Any
from task_classifier import task_classifier
from task_orchestrator import task_orchestrator


class ElizaOrchestrator:
    def __init__(self):
        self.classifier = task_classifier
        self.orchestrator = task_orchestrator

    # ---------------------------------------------------------
    # NATURAL LANGUAGE PROCESSING
    # ---------------------------------------------------------
    def _extract_task(self, message: str) -> str:
        """
        Extracts the actionable part of a human-language message.
        For now, this is simple: return the message itself.
        """
        return message.strip()

    # ---------------------------------------------------------
    # MAIN ENTRY POINT
    # ---------------------------------------------------------
    def handle(self, message: str) -> Dict[str, Any]:
        """
        Eliza receives a natural language message,
        interprets it, classifies it, and delegates it.
        """

        # Step 1: Extract the task from human language
        task = self._extract_task(message)

        # Step 2: Determine the task category
        category = self.classifier.classify(task)

        # Step 3: Delegate the task to the correct persona
        result = self.orchestrator.handle_task(task, category)

        # Step 4: Add Eliza's conversational response
        result["eliza_response"] = self._build_eliza_response(
            task=task,
            category=category,
            persona=result["assigned_to"]
        )

        return result

    # ---------------------------------------------------------
    # ELIZA'S PERSONALITY RESPONSE
    # ---------------------------------------------------------
    def _build_eliza_response(self, task: str, category: str, persona: str) -> str:
        """
        Generates a conversational, personality-driven response from Eliza.
        """

        return (
            f"Oh, I see what you're asking. '{task}' falls under {category}, "
            f"so I’m assigning it to {persona}. "
            f"Don't worry — I'll keep them on track. I always do."
        )


# ---------------------------------------------------------
# GLOBAL INSTANCE
# ---------------------------------------------------------
eliza_orchestrator = ElizaOrchestrator()