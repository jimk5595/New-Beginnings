# eliza_controller.py
# Top-level controller that unifies the entire persona system.
# This is the single entry point for interacting with Eliza.

from typing import Dict, Any
from models.eliza_orchestrator import eliza_orchestrator
from models.persona_executor import persona_executor


class ElizaController:
    def __init__(self):
        self.orchestrator = eliza_orchestrator
        self.executor = persona_executor

    # ---------------------------------------------------------
    # MAIN ENTRY POINT
    # ---------------------------------------------------------
    def process(self, message: str) -> Dict[str, Any]:
        """
        Full pipeline:
        1. Eliza interprets the human-language message
        2. Task is classified
        3. Task is delegated
        4. Persona executes the task (stub for now)
        5. Eliza responds conversationally
        """

        # Step 1–3: Orchestrator handles interpretation + classification + delegation
        orchestration_result = self.orchestrator.handle(message)

        task = orchestration_result["task"]
        persona = orchestration_result["persona_details"]

        # Step 4: Persona executes the task
        execution_result = self.executor.execute(task, persona)

        # Step 5: Combine everything into a unified response
        return {
            "input_message": message,
            "task": task,
            "category": orchestration_result["category"],
            "assigned_to": orchestration_result["assigned_to"],
            "eliza_response": orchestration_result["eliza_response"],
            "execution_result": execution_result
        }


# ---------------------------------------------------------
# GLOBAL INSTANCE
# ---------------------------------------------------------
eliza_controller = ElizaController()