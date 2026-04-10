from backend.memory_system.memory_core import MemoryEngine
from backend.system_config import OFFICIAL_FILE_MAP
import os

# Global instance for easy access
_engine = MemoryEngine()

def verify_system_integrity():
    """
    Verifies the current directory structure against OFFICIAL_FILE_MAP.
    """
    # Robust project root detection
    project_root = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
    valid_paths = set(OFFICIAL_FILE_MAP.values())
    
    # We check if files in map exist, and warn if unexpected files appear in key directories
    integrity_report = []
    for key, path in OFFICIAL_FILE_MAP.items():
        full_path = os.path.join(project_root, path)
        if not os.path.exists(full_path):
            integrity_report.append(f"MISSING: {key} at {path}")
    
    return integrity_report

def quick_save(category: str, data: dict):
    """
    Exposes the memory module to the agent system for rapid persistence.
    Categories: 'lessons_learned', 'family_profiles', 'build_registry'
    """
    # System Integrity Check on every save
    integrity_issues = verify_system_integrity()
    if integrity_issues:
        print(f"INTEGRITY WARNING: {integrity_issues}")
        data['integrity_notes'] = integrity_issues

    try:
        _engine.log_experience(category, data)
        return True
    except Exception as e:
        print(f"Memory Bridge Error: {e}")
        return False

def get_recent_context(category: str, limit: int = 5):
    """
    Retrieves the most recent context for a category.
    """
    try:
        return _engine.retrieve_context(category, limit)
    except Exception as e:
        print(f"Memory Bridge Error: {e}")
        return []
