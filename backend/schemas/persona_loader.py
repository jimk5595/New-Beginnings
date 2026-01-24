# persona_loader.py
# Loads, validates, and exposes persona data from the central registry.

from typing import Dict, Any
from personas import PERSONAS


class PersonaLoader:
    def __init__(self, registry: Dict[str, Dict[str, Any]] = None):
        self.registry = registry or PERSONAS
        self._validate_registry()

    # ---------------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------------
    def _validate_registry(self):
        if not isinstance(self.registry, dict):
            raise ValueError("Persona registry must be a dictionary.")

        for key, persona in self.registry.items():
            required_fields = ["name", "role", "department", "personality", "responsibilities"]

            for field in required_fields:
                if field not in persona:
                    raise ValueError(f"Persona '{key}' is missing required field: {field}")

            if not isinstance(persona["personality"], dict):
                raise ValueError(f"Persona '{key}' has invalid personality format.")

            if not isinstance(persona["responsibilities"], list):
                raise ValueError(f"Persona '{key}' responsibilities must be a list.")

    # ---------------------------------------------------------
    # ACCESSORS
    # ---------------------------------------------------------
    def get_persona(self, key: str) -> Dict[str, Any]:
        """Return a persona by its registry key."""
        persona = self.registry.get(key)
        if not persona:
            raise KeyError(f"Persona '{key}' not found in registry.")
        return persona

    def list_personas(self):
        """Return a list of all persona keys."""
        return list(self.registry.keys())

    def get_by_role(self, role: str):
        """Return all personas matching a specific role."""
        return {k: v for k, v in self.registry.items() if v["role"].lower() == role.lower()}

    def get_by_department(self, department: str):
        """Return all personas in a specific department."""
        return {
            k: v for k, v in self.registry.items()
            if v["department"].lower() == department.lower()
        }


# ---------------------------------------------------------
# GLOBAL LOADER INSTANCE
# ---------------------------------------------------------
persona_loader = PersonaLoader()