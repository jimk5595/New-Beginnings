# unified_task_api.py
# Public entry point for the persona system.
# Other backend modules call this to process tasks through Eliza.

from typing import Dict, Any
from core.orchestrator import unified_orchestrator


async def process_task(message: str) -> Dict[str, Any]:
    """
    Main function the backend calls.
    Sends a natural-language message to Eliza and returns the result.
    """
    return await unified_orchestrator.handle_task(message)


# Optional helper for debugging or admin tools
def explain_categories():
    """
    Returns all available task categories.
    """
    return unified_orchestrator.classifier.keyword_map.keys()
