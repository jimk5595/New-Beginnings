# persona_executor.py
# Executes tasks assigned to personas.
# Currently a stub — returns placeholder output for each persona.

from typing import Dict, Any


class PersonaExecutor:
    def execute(self, task: str, persona: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a task for a given persona.
        This is a stub for now — real logic can be added later.
        """

        name = persona.get("name", "Unknown Persona")
        role = persona.get("role", "Unknown Role")

        return {
            "task": task,
            "executed_by": name,
            "role": role,
            "status": "completed",
            "notes": f"{name} has completed the task using the current stub executor."
        }


# ---------------------------------------------------------
# GLOBAL INSTANCE
# ---------------------------------------------------------
persona_executor = PersonaExecutor()