import os
import json
import logging
import importlib.util
import sys
from typing import Dict, Any, List

# Ensure parent directory is in path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from validator import validate_module
from persona_logger import narrate
from core.system_status import system_monitor

# Initialize logger
logger = logging.getLogger("IntegrationEngine")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [INTEGRATION] %(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Global REGISTRY
REGISTRY: Dict[str, Dict[str, Any]] = {}

# Paths relative to the project root
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULES_DIR = os.path.join(BASE_DIR, "modules")

def discover_modules() -> List[str]:
    """Scans the modules/ directory for folders containing module.json."""
    narrate("Integrity Monitor", "Scanning for modules...")
    if not os.path.exists(MODULES_DIR):
        narrate("Integrity Monitor", f"WARNING: Modules directory not found at {MODULES_DIR}")
        return []
    
    module_folders = []
    for folder in os.listdir(MODULES_DIR):
        folder_path = os.path.join(MODULES_DIR, folder)
        if os.path.isdir(folder_path):
            if os.path.exists(os.path.join(folder_path, "module.json")):
                module_folders.append(folder)
                narrate("Integrity Monitor", f"Discovered module candidate: {folder}")
            else:
                logger.debug(f"Skipping folder {folder}: module.json not found")
    
    return module_folders

def clear_module_cache(module_folder: str):
    """Deep clears sys.modules for a specific module and its potential sub-imports."""
    to_delete = []
    # Search for the module and anything nested under it
    # Modules are loaded as module_{name}
    target_prefix = f"module_{module_folder}"
    for key in sys.modules:
        if key == target_prefix or key.startswith(f"{target_prefix}."):
            to_delete.append(key)
    
    for key in to_delete:
        del sys.modules[key]
    
    # Also handle the folder-based import if backend.modules.folder was used
    folder_prefix = f"modules.{module_folder}"
    to_delete_folder = []
    for key in sys.modules:
        if key == folder_prefix or key.startswith(f"{folder_prefix}."):
            to_delete_folder.append(key)
    
    for key in to_delete_folder:
        del sys.modules[key]

def load_module_entrypoint(module_folder: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Dynamically imports the entrypoint Python file and calls register()."""
    module_name = config["name"]
    entrypoint_rel_path = config["entrypoint"]
    entrypoint_abs_path = os.path.join(MODULES_DIR, module_folder, entrypoint_rel_path)
    
    try:
        # Load module specific .env if it exists
        module_env = os.path.join(MODULES_DIR, module_folder, ".env")
        if os.path.exists(module_env):
            from dotenv import load_dotenv
            load_dotenv(module_env, override=True)

        # Requirement: Fresh imports (no stale Python import cache)
        clear_module_cache(module_folder)

        module_key = f"module_{module_folder}"
        spec = importlib.util.spec_from_file_location(module_key, entrypoint_abs_path)
        if spec is None or spec.loader is None:
            system_monitor.update_loader(module_folder, success=False, error="Spec/Loader is None")
            raise ImportError(f"Could not load spec for module at {entrypoint_abs_path}")
        
        # Import module
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_key] = module
        spec.loader.exec_module(module)
        
        # Check for register() function
        if not hasattr(module, "register"):
            system_monitor.update_loader(module_folder, success=False, error="Missing register()")
            raise AttributeError(f"Module '{module_name}' entrypoint missing required 'register()' function")
        
        # Execute register()
        result = module.register()
        
        # Flexibly handle dictionary or direct router return
        if isinstance(result, dict):
            metadata = result
        else:
            # Assume it returned the router directly
            metadata = {"router": result}
            
        system_monitor.update_loader(module_folder, success=True)
        narrate("Integrity Monitor", f"Successfully loaded and registered module: {module_name}")
        return metadata
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        system_monitor.update_loader(module_folder, success=False, error=f"{str(e)}\n{error_details}")
        narrate("Integrity Monitor", f"ERROR: Failed to load entrypoint for module '{module_name}': {str(e)}")
        logger.error(f"Import Error for {module_name}:\n{error_details}")
        raise

def run_discovery_and_registration():
    """Main lifecycle loop for discovering, validating, and loading modules."""
    global REGISTRY
    # Build into a new dict first — atomically replace at the end to avoid
    # returning an empty registry to concurrent API requests during re-scan.
    new_registry: Dict[str, Any] = {}

    module_folders = discover_modules()
    
    for folder in module_folders:
        module_path = os.path.join(MODULES_DIR, folder)
        json_path = os.path.join(module_path, "module.json")
        
        # SKIP if build lock is present — this prevents the Integrity Monitor from
        # racing with the Lead Engineer during sequential construction.
        if os.path.exists(os.path.join(module_path, ".building")):
            continue

        try:
            if not os.path.exists(json_path):
                continue

            with open(json_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 1. EARLY REGISTRY UPDATE (Requirement: Updates happen BEFORE validator)
            # This ensures the persona can see the candidate in SystemStatus
            system_monitor.update_registry(folder, config.get("status", "pending"), {})

            # 2. LOAD ENTRYPOINT (Requirement: Fresh import before validation)
            try:
                metadata = load_module_entrypoint(folder, config)
                
                # 3. VALIDATE (Requirement: Use pre-loaded metadata)
                # Pass metadata to validator so it doesn't re-import and create stale objects
                if not validate_module(folder, metadata=metadata, check_live=False):
                    narrate("Integrity Monitor", f"Module '{folder}' failed validation. Recording as error for repair.")
                    new_registry[folder] = {
                        "name": config.get("name", folder),
                        "status": "error",
                        "module_path": module_path,
                        "metadata": {}
                    }
                    system_monitor.update_registry(folder, "error", {}, errors=["Validation failed"])
                    continue

                # 4. FINAL REGISTRY COMMIT (into new_registry — not yet live)
                new_registry[folder] = {
                    "name": config.get("name", folder),
                    "description": config.get("description", ""),
                    "version": config.get("version", "1.0.0"),
                    "ui_link": config.get("ui_link", "index.html"),
                    "language": config.get("language", "python"),
                    "status": config.get("status", "active"),
                    "entrypoint": config.get("entrypoint", "app.py"),
                    "personas": config.get("personas", []),
                    "module_path": module_path,
                    "metadata": metadata
                }
                system_monitor.update_registry(folder, config.get("status", "active"), metadata)
            except Exception as e:
                system_monitor.update_registry(folder, config.get("status", "error"), {}, errors=[str(e)])
                continue
                
        except Exception as e:
            narrate("Integrity Monitor", f"CRITICAL: Error processing module '{folder}': {str(e)}")

    # Atomic registry swap — concurrent requests keep seeing the old registry until
    # this single assignment completes (GIL ensures it is effectively atomic in CPython).
    REGISTRY = new_registry

def get_registry() -> Dict[str, Any]:
    """Exposes the complete REGISTRY to the system."""
    return REGISTRY

def get_active_modules() -> Dict[str, Any]:
    """Returns only modules that have an 'active' status."""
    return {name: info for name, info in REGISTRY.items() if info["status"] == "active"}

if __name__ == "__main__":
    run_discovery_and_registration()
