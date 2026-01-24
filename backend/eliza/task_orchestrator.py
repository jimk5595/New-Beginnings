from eliza_core import ElizaCore
import sys
import os

# Add parent directory to sys.path to import from root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from persona_pipeline import run_persona_pipeline
from ..models import PipelineRequest
from persona import Persona

class TaskOrchestrator:
    def __init__(self):
        self.eliza = ElizaCore()
        # Define the Architect Persona as per instruction
        self.architect = Persona(
            name="Architect",
            description="Expert in system design and architecture.",
            system_prompt="You are the Lead Architect. Provide technical, modular blueprints for standalone creative tools."
        )

    def execute(self, plan, task_text):
        """
        Iterates through the provided plan steps, executes them using the 
        persona pipeline, and analyzes the user's original task using ElizaCore.
        """
        # Debug logging
        with open("eliza_debug.log", "a") as f:
            f.write(f"DEBUG: task_text='{task_text}'\n")

        executed_steps = []

        for step in plan:
            # Carry out instructions on local disk by running the persona pipeline for each step
            # We treat each step description as a prompt for the persona
            request = PipelineRequest(model="default", prompt=step["detail"])
            pipeline_result = run_persona_pipeline(request, self.architect)
            
            result = {
                "id": step["id"],
                "action": step["action"],
                "status": "done",
                "output": pipeline_result.output
            }
            executed_steps.append(result)

        # Analyze the user's original input using ElizaCore
        analysis = self.eliza.analyze_input(task_text)
        eliza_response = self.eliza.respond(analysis)

        return {
            "steps": executed_steps,
            "eliza": eliza_response
        }
