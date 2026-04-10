import os
import logging
import traceback
import importlib.util
from typing import Dict, Any, Optional, Union
from .integration_engine import get_registry

# Initialize logger
logger = logging.getLogger("DelegationEngine")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [DELEGATION] %(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class DelegationEngine:
    """
    The Delegation Engine is responsible for routing tasks, 
    enforcing architecture rules, and maintaining system stability.
    """

    def get_status(self, module_name: str) -> str:
        """Returns the current lifecycle status of a module."""
        registry = get_registry()
        if module_name in registry:
            return registry[module_name].get("status", "unknown")
        return "not_found"

    def set_status(self, module_name: str, status: str):
        """Sets the lifecycle status of a module in the in-memory registry."""
        registry = get_registry()
        if module_name in registry:
            valid_statuses = ["uninitialized", "registered", "active", "failed"]
            if status in valid_statuses:
                registry[module_name]["status"] = status
                logger.info(f"Module '{module_name}' status updated to '{status}'")
            else:
                logger.error(f"Invalid status '{status}' for module '{module_name}'")
        else:
            logger.error(f"Cannot update status: Module '{module_name}' not found in registry")

    def validate_module(self, module_name: str) -> Dict[str, Any]:
        """Validates module integrity based on the plugin architecture contract."""
        registry = get_registry()
        if module_name not in registry:
            return {"valid": False, "error": f"Module '{module_name}' not found in registry"}
        
        module_info = registry[module_name]
        module_path = module_info.get("module_path")
        
        if not module_path or not os.path.exists(module_path):
            return {"valid": False, "error": f"Module directory for '{module_name}' does not exist"}
        
        json_path = os.path.join(module_path, "module.json")
        if not os.path.exists(json_path):
            return {"valid": False, "error": f"module.json missing for module '{module_name}'"}
            
        entrypoint_rel_path = module_info.get("entrypoint")
        if not entrypoint_rel_path:
            return {"valid": False, "error": f"No entrypoint defined for module '{module_name}'"}
            
        entrypoint_abs_path = os.path.join(module_path, entrypoint_rel_path)
        if not os.path.exists(entrypoint_abs_path):
            return {"valid": False, "error": f"Entrypoint file '{entrypoint_rel_path}' not found for module '{module_name}'"}
            
        return {"valid": True}

    def safe_call(self, module_name: str, function_name: str, *args, **kwargs) -> Any:
        """Executes a function from a module's entrypoint safely, handling exceptions."""
        registry = get_registry()
        if module_name not in registry:
            return {"error": f"Module '{module_name}' not found"}
            
        if registry[module_name]["status"] == "failed":
            return {"error": f"Execution aborted: Module '{module_name}' is in a failed state"}
            
        module_info = registry[module_name]
        entrypoint_path = os.path.join(module_info["module_path"], module_info["entrypoint"])
        
        try:
            spec = importlib.util.spec_from_file_location(f"delegate_{module_name}", entrypoint_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load spec for module {module_name}")
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if hasattr(module, function_name):
                func = getattr(module, function_name)
                logger.info(f"Calling {module_name}.{function_name}()...")
                return func(*args, **kwargs)
            else:
                raise AttributeError(f"Module '{module_name}' does not implement '{function_name}'")
                
        except Exception as e:
            error_msg = f"Fatal error during call to '{module_name}.{function_name}': {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.set_status(module_name, "failed")
            return {
                "status": "error",
                "module": module_name,
                "message": str(e),
                "traceback": traceback.format_exc()
            }

    def route_task(self, task: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Routes tasks to either a specific module or the platform core."""
        task_description = task if isinstance(task, str) else str(task.get("description", task))
        task_lower = task_description.lower()
        
        registry = get_registry()
        target_module = None
        
        # Identify target module from registry
        for module_name in registry:
            if module_name.lower() in task_lower:
                target_module = module_name
                break
        
        if target_module:
            # Enforce validation before routing
            validation = self.validate_module(target_module)
            if not validation["valid"]:
                self.set_status(target_module, "failed")
                return {
                    "status": "error",
                    "module": target_module,
                    "message": f"Validation failed: {validation['error']}"
                }
            
            logger.info(f"Routing task to module: {target_module}")
            return {
                "status": "routed",
                "target": target_module,
                "scope": f"modules/{target_module}/",
                "instructions": (
                    f"Task delegated to '{target_module}'. All operations must remain within "
                    f"the 'modules/{target_module}/' directory. Modification of core or other "
                    "modules is strictly prohibited."
                )
            }
        
        # Platform/Core task detection
        platform_keywords = ["core", "system", "platform", "global", "security", "integration", "dashboard"]
        if any(kw in task_lower for kw in platform_keywords) or not target_module:
            logger.info("Platform-level task detected")
            return {
                "status": "unauthorized",
                "message": "Platform-level operations require explicit user authorization.",
                "scope": "core"
            }

        return {"status": "unknown", "message": "Task target could not be determined."}

# Singleton instance for system-wide use
delegation_engine = DelegationEngine()

# Functional API wrappers
def route_task(task): return delegation_engine.route_task(task)
def set_status(module_name, status): return delegation_engine.set_status(module_name, status)
def get_status(module_name): return delegation_engine.get_status(module_name)
def validate_module(module_name): return delegation_engine.validate_module(module_name)
def safe_call(module_name, function_name, *args, **kwargs): 
    return delegation_engine.safe_call(module_name, function_name, *args, **kwargs)
