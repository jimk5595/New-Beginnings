import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from memory_system.memory_core import MemoryEngine

def initialize_memory():
    engine = MemoryEngine()

    engine.log_experience("lessons_learned", {
        "module_name": "core",
        "mistake": "Consultant Drift",
        "fix": "Integration of direct file-system actions and the Working and Right directive.",
        "status": "resolved"
    })

    engine.log_experience("build_registry", {
        "project_name": "Core Infrastructure",
        "map": "Git linked, PostgreSQL memory active, .gitignore implemented."
    })

    engine.log_experience("family_profiles", {
        "relation": "system",
        "detail": "This system is designed for long-term growth with the family, focusing on memory persistence and evolving intelligence."
    })

    print("Memory initialized successfully in PostgreSQL.")

if __name__ == "__main__":
    initialize_memory()
