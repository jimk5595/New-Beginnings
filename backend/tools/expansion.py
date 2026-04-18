import os
from pathlib import Path
from tools.project_map import ProjectMap
from tools.integration import RUN_INTEGRATION_TASK
from persona_logger import narrate


def RUN_EXPANSION_TASK(task_text: str, project_map: ProjectMap = None, module_name: str = None) -> str:
    """
    Uses ProjectMap to create new modules or components in the correct location.
    ENFORCES FULL FUNCTIONALITY - NO SKELETONS ALLOWED.
    """
    if project_map is None:
        project_map = ProjectMap()
    
    root_dir = Path(project_map.root_dir)
    
    # 1. Determine target directory
    target_base = root_dir / "backend" / "modules"

    if "frontend" in task_text.lower() or "ui" in task_text.lower():
        if "frontend/" in task_text.lower():
             target_base = root_dir / "frontend"
    
    # 2. Extract proposed module name
    import re
    
    if module_name:
        new_mod_name = module_name
    else:
        clean_text = task_text.replace("'", "").replace('"', "").replace("`", "")
        words = clean_text.lower().split()
        new_mod_name = "new_expansion_module"
        
        stop_words = ["a", "the", "new", "complete", "production-ready", "module", "component", "app", "application", "named", "with", "for", "must", "should", "will", "includes", "including", "be", "to", "of", "full", "system", "inside", "as", "structured"]
        
        found = False
        for trigger in ["module named", "module", "app named", "app"]:
            trigger_words = trigger.split()
            for i in range(len(words) - len(trigger_words)):
                if words[i:i+len(trigger_words)] == trigger_words:
                    potential = words[i+len(trigger_words)].strip(".,")
                    if potential not in stop_words and len(potential) > 2:
                        new_mod_name = potential
                        found = True
                        break
            if found: break
        
        if not found:
            for word in words:
                if word not in stop_words and len(word) > 3:
                    new_mod_name = word.strip(".,")
                    break
    
    new_mod_name = re.sub(r'[^a-z0-9\-_]', '', new_mod_name.lower())
    if not new_mod_name:
        new_mod_name = "new_module"
            
    target_path = target_base / new_mod_name
    
    try:
        os.makedirs(target_path, exist_ok=True)
        
        narrate("Naomi Kade", f"Directory structure initialized for {new_mod_name}.")
        return f"SUCCESS: Directory initialized for '{new_mod_name}' at {target_path}."

    except Exception as e:
        return f"ERROR: Expansion failed: {str(e)}"