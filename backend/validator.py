import json
import os
import sys
import argparse
import logging
from typing import Dict, Any, List, Optional
from persona_logger import narrate

# Initialize logger
logger = logging.getLogger("Validator")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [VALIDATOR] %(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Global paths for robust validation
backend_dir = os.path.dirname(os.path.abspath(__file__))

def validate_module(module_name: str, metadata: Dict[str, Any] = None, check_live: bool = False) -> bool:
    """
    Performs structural and functional validation of a module using BuildGate.
    """
    from schemas.build_gate import build_gate
    module_path = os.path.join(backend_dir, 'modules', module_name)
    
    narrate("Dr. Mira Kessler", f"Validating integrity of '{module_name}'...")
    
    if not os.path.exists(module_path):
        narrate("Marcus Hale", f"FAILED: Directory {module_name} not found.")
        return False
        
    # Read files into a blob for BuildGate
    blob = {}
    try:
        for filename in os.listdir(module_path):
            file_path = os.path.join(module_path, filename)
            if os.path.isfile(file_path):
                # Only read relevant files for validation to avoid huge blobs
                if filename in build_gate.REQUIRED_FILES or filename.endswith((".py", ".tsx", ".html", ".json")):
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        blob[filename] = f.read()
    except Exception as e:
        narrate("Dr. Mira Kessler", f"FAILED: Could not read module files: {e}")
        return False

    # Perform static structural validation
    is_valid, errors = build_gate.validate_blob(module_name, blob)
    
    if not is_valid:
        narrate("Dr. Mira Kessler", f"FAILED Structural Integrity: {'; '.join(errors)}")
        return False

    # Optional metadata-driven check (e.g. if IntegrationEngine already loaded a router)
    if metadata and "router" not in metadata and "app" not in metadata:
         narrate("Dr. Mira Kessler", f"WARNING: Module '{module_name}' metadata missing router/app object.")

    # Check that the JS bundle was actually produced by esbuild
    built_js = os.path.join(backend_dir, "static", "built", "modules", module_name, "index.js")
    if not os.path.exists(built_js):
        narrate("Dr. Mira Kessler", f"FAILED: Bundle missing for '{module_name}' — index.js not found in static/built.")
        return False

    narrate("Dr. Mira Kessler", f"SUCCESS: '{module_name}' passed validation.")
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("module", help="Module name to validate")
    parser.add_argument("--live", action="store_true", help="Perform live functional checks")
    args = parser.parse_args()
    
    if validate_module(args.module, check_live=args.live):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()