import json
import os
from typing import Tuple, List, Dict, Any, Optional

# Constants
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "module_schema.json")

def safe_load_json(path: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Loads JSON safely from a file path.
    Returns (data, error_message).
    """
    try:
        if not os.path.exists(path):
            return None, f"File not found: {path}"
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data, None
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON format: {str(e)}"
    except Exception as e:
        return None, f"Error reading file: {str(e)}"

def validate_module_json(path_to_module_json: str) -> Tuple[bool, List[str]]:
    """
    Validates a module.json file against the system schema.
    Returns (is_valid, errors).
    """
    errors = []
    
    # 1. Load the module.json
    data, error = safe_load_json(path_to_module_json)
    if error:
        errors.append(error)
        return False, errors

    # 2. Load the schema for reference
    schema, schema_error = safe_load_json(SCHEMA_PATH)
    if schema_error:
        errors.append(f"Internal Error: Could not load schema - {schema_error}")
        return False, errors

    # 3. Validate required fields and types
    required_fields = schema.get("required", [])
    properties = schema.get("properties", {})

    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: '{field}'")
            continue
        
        # Type validation
        expected_type = properties.get(field, {}).get("type")
        actual_value = data.get(field)
        
        if expected_type == "string" and not isinstance(actual_value, str):
            errors.append(f"Field '{field}' must be a string")
        elif expected_type == "object" and not isinstance(actual_value, dict):
            errors.append(f"Field '{field}' must be an object")

    # 4. Validate Enum for status
    if "status" in data:
        valid_statuses = properties.get("status", {}).get("enum", [])
        if data["status"] not in valid_statuses:
            errors.append(f"Invalid status '{data['status']}'. Must be one of: {', '.join(valid_statuses)}")

    # 5. Validate Entrypoint extension
    if "entrypoint" in data and isinstance(data["entrypoint"], str):
        if not data["entrypoint"].endswith(".py"):
            errors.append(f"Entrypoint '{data['entrypoint']}' must point to a .py file")

    # 6. Validate Entrypoint path existence
    if "entrypoint" in data and not errors:
        module_dir = os.path.dirname(path_to_module_json)
        entrypoint_path = os.path.join(module_dir, data["entrypoint"])
        if not os.path.exists(entrypoint_path):
            errors.append(f"Entrypoint file not found: {entrypoint_path}")

    # 7. Validate metadata type if present
    if "metadata" in data and not isinstance(data["metadata"], dict):
        errors.append("Field 'metadata' must be an object")

    return len(errors) == 0, errors
