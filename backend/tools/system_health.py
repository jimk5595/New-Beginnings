from pathlib import Path
import os
import importlib

def run_system_health_check():
    results = {}
    # Check personas folder
    personas_path = Path("backend/personas")
    if not personas_path.exists():
        personas_path = Path("personas") # Fallback for different working dirs
        
    results["personas_folder_exists"] = personas_path.exists()
    results["persona_files"] = [p.name for p in personas_path.glob("*.md")] if personas_path.exists() else []
    
    # Check key modules
    modules_to_check = ["llm_router", "validator", "models"]
    results["module_imports"] = {}
    
    for mod in modules_to_check:
        try:
            importlib.import_module(mod)
            results["module_imports"][mod] = "ok"
        except Exception as e:
            # Try with backend prefix
            try:
                importlib.import_module(f"backend.{mod}")
                results["module_imports"][mod] = "ok (with backend prefix)"
            except Exception as e2:
                results["module_imports"][mod] = f"error: {e2}"
                
    # Check schemas
    try:
        importlib.import_module("schemas.task_classifier")
        results["schemas_import"] = "ok"
    except Exception:
        try:
            importlib.import_module("backend.schemas.task_classifier")
            results["schemas_import"] = "ok (with backend prefix)"
        except Exception as e:
            results["schemas_import"] = f"error: {e}"
            
    return results
