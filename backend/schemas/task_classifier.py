# task_classifier.py
# Automatically determines the category of a task based on keywords.

from typing import Dict


class TaskClassifier:
    def __init__(self):
        self.keyword_map = self._build_keyword_map()

    # ---------------------------------------------------------
    # KEYWORD → CATEGORY MAP
    # ---------------------------------------------------------
    def _build_keyword_map(self) -> Dict[str, str]:
        return {
            # BUILD / DEV
            "build": "build",
            "develop": "build",
            "feature": "build",
            "component": "build",

            # BACKEND
            "api": "backend",
            "database": "backend",
            "service": "backend",
            "endpoint": "backend",
            "model": "backend",

            # FRONTEND
            "ui": "frontend",
            "interface": "frontend",
            "button": "frontend",
            "layout": "frontend",
            "react": "frontend",

            # FULLSTACK
            "fullstack": "fullstack",
            "integration": "fullstack",

            # REVIEW
            "review": "review",
            "audit": "review",
            "check": "review",

            # DESIGN
            "design": "design",
            "mockup": "design",
            "visual": "design",

            # UX
            "ux": "ux",
            "flow": "ux",
            "wireframe": "ux",
            "usability": "ux",

            # SEO / CRO
            "seo": "seo",
            "keywords": "seo",
            "ranking": "seo",
            "cro": "cro",
            "conversion": "cro",
            "funnel": "cro",

            # EXECUTIVE
            "plan": "executive",
            "strategy": "executive",
            "overview": "executive",
            "roadmap": "executive",
        }

    # ---------------------------------------------------------
    # CLASSIFY TASK
    # ---------------------------------------------------------
    def classify(self, task: str) -> str:
        """
        Returns the category of a task based on keyword matching.
        Defaults to 'executive' if no match is found.
        """
        task_lower = task.lower()

        for keyword, category in self.keyword_map.items():
            if keyword in task_lower:
                return category

        return "executive"  # fallback category


# ---------------------------------------------------------
# GLOBAL INSTANCE
# ---------------------------------------------------------
task_classifier = TaskClassifier()