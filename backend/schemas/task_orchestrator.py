# task_orchestrator.py
# Determines task category and routes it through the delegation engine.

from typing import Dict, Any
from delegation_engine import delegation_engine


class TaskOrchestrator:
    def __init__(self):
        self.delegation = delegation_engine

    # ---------------------------------------------------------
    # MAIN ENTRY POINT
    # ---------------------------------------------------------
    def handle_task(self, task: str, category: str) -> Dict[str, Any]:
        """
        Receives a task and a category string.
        Returns the persona responsible for handling it.
        """
        category = category.lower().strip()

        persona = self.delegation.delegate(category)

        return {
            "task": task,
            "category": category,
            "assigned_to": persona["name"],
            "persona_details": persona
        }

    # ---------------------------------------------------------
    # LIST AVAILABLE CATEGORIES
    # ---------------------------------------------------------
    def list_categories(self):
        return self.delegation.list_categories()


# ---------------------------------------------------------
# GLOBAL INSTANCE
# ---------------------------------------------------------
task_orchestrator = TaskOrchestrator()