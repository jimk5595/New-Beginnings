# delegation_engine.py
# Routes tasks to the correct persona using the persona loader.

from typing import Dict, Any
from persona_loader import persona_loader


class DelegationEngine:
    def __init__(self):
        self.loader = persona_loader
        self.routing_map = self._build_routing_map()

    # ---------------------------------------------------------
    # ROUTING MAP
    # ---------------------------------------------------------
    def _build_routing_map(self) -> Dict[str, str]:
        """
        Maps task categories to persona keys.
        Eliza oversees everything but delegates actual work.
        """
        return {
            "executive": "eliza",
            "build": "marcus_hale",
            "frontend": "ava_morgan",
            "backend": "jordan_reyes",
            "fullstack": "riley_chen",
            "review": "sophia_lane",
            "design": "adrian_wolfe",
            "ux": "maya_kincaid",
            "seo": "lena_ortiz",
            "cro": "lena_ortiz",
        }

    # ---------------------------------------------------------
    # DELEGATION LOGIC
    # ---------------------------------------------------------
    def delegate(self, task_category: str) -> Dict[str, Any]:
        """
        Returns the persona responsible for a given task category.
        """
        key = self.routing_map.get(task_category.lower())

        if not key:
            raise KeyError(f"No persona assigned for task category: {task_category}")

        return self.loader.get_persona(key)

    # ---------------------------------------------------------
    # LIST AVAILABLE CATEGORIES
    # ---------------------------------------------------------
    def list_categories(self):
        return list(self.routing_map.keys())


# ---------------------------------------------------------
# GLOBAL INSTANCE
# ---------------------------------------------------------
delegation_engine = DelegationEngine()