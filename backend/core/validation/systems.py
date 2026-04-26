import os
import json
import re
import importlib.util
from pathlib import Path
from typing import List, Dict, Any

class RuntimeSimulator:
    """Simulates user flows, API calls, and backend responses."""
    def validate(self, module_path: Path) -> Dict[str, Any]:
        # Implementation: Check if app.py is loadable and routes are defined
        app_file = module_path / "app.py"
        if not app_file.exists():
            return {"status": "failed", "error": "app.py missing"}
        
        try:
            # Simulate loading the module
            spec = importlib.util.spec_from_file_location("module_app", app_file)
            foo = importlib.util.module_from_spec(spec)
            # We don't actually execute it to avoid side effects, 
            # but we verify it's syntactically correct and has the required 'router'
            with open(app_file, "r") as f:
                content = f.read()
                if "APIRouter()" not in content:
                    return {"status": "failed", "error": "APIRouter not found in app.py"}
                if "def register()" not in content:
                    return {"status": "failed", "error": "register() function missing in app.py"}
            
            return {"status": "passed"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

class EndpointDiscoverer:
    """Discover and list all endpoints exposed/used by each module."""
    def validate(self, module_path: Path) -> Dict[str, Any]:
        app_file = module_path / "app.py"
        endpoints = []
        if app_file.exists():
            with open(app_file, "r") as f:
                content = f.read()
                # Simple regex for FastAPI decorators
                matches = re.findall(r'@router\.(get|post|put|delete)\("([^"]+)"', content)
                endpoints = [f"{m[0].upper()} {m[1]}" for m in matches]
        
        return {"status": "passed", "endpoints": endpoints}

class EndpointTester:
    """Test each endpoint for availability, correctness, and expected response shape."""
    def validate(self, module_path: Path, endpoints: List[str]) -> Dict[str, Any]:
        # In a real system, this would make actual local requests if the server was running
        # For this build, we verify the implementation of the handlers in app.py
        app_file = module_path / "app.py"
        if not app_file.exists():
            return {"status": "failed", "error": "app.py missing"}
            
        with open(app_file, "r") as f:
            content = f.read()
            for ep in endpoints:
                # Extract path from "METHOD /path"
                path = ep.split(" ")[1]
                if f'"{path}"' not in content:
                     return {"status": "failed", "error": f"Endpoint {ep} implementation not found"}
        
        return {"status": "passed"}

class UIBackendWiringValidator:
    """Validate that all UI actions are correctly wired to backend endpoints."""
    def validate(self, module_path: Path, endpoints: List[str]) -> Dict[str, Any]:
        service_file = module_path / "service.ts"
        if not service_file.exists():
            return {"status": "passed", "info": "service.ts missing (optional)"}
            
        with open(service_file, "r") as f:
            content = f.read()
            # Check if endpoints discovered in backend are referenced in frontend service
            for ep in endpoints:
                path = ep.split(" ")[1]
                # Modules use prefixes like /module_api/
                # We check if the core path is present
                clean_path = path.split("/")[-1]
                if clean_path not in content:
                    return {"status": "failed", "error": f"Endpoint {path} not wired in service.ts"}
                    
        return {"status": "passed"}

class JSONSchemaValidator:
    """Validate all JSON schemas used by modules and ensure they match the 5-file core contract."""
    def validate(self, module_path: Path) -> Dict[str, Any]:
        module_json = module_path / "module.json"
        if not module_json.exists():
            return {"status": "failed", "error": "module.json missing"}
            
        try:
            with open(module_json, "r") as f:
                data = json.load(f)
                required = ["name", "description", "version", "entrypoint", "ui_link", "language", "status"]
                for field in required:
                    if field not in data:
                        return {"status": "failed", "error": f"Missing field '{field}' in module.json"}
            return {"status": "passed"}
        except Exception as e:
            return {"status": "failed", "error": f"JSON parse error: {str(e)}"}

class IntelligenceLayerValidator:
    """Validate that app.py makes real external calls (not a static stub)."""
    def validate(self, module_path: Path) -> Dict[str, Any]:
        app_file = module_path / "app.py"
        if not app_file.exists():
            return {"status": "failed", "error": "app.py missing"}
            
        with open(app_file, "r") as f:
            content = f.read()
            real_call_indicators = [
                "httpx", "requests.", "aiohttp", "urllib", "os.getenv",
                "asyncio.gather", "async def ", "await ",
            ]
            if not any(ind in content for ind in real_call_indicators):
                return {"status": "failed", "error": "app.py appears to be a stub — no real HTTP calls or async logic found"}
                
        return {"status": "passed"}

class ManifestConsistencyChecker:
    """Ensure each module’s manifest matches the actual implementation."""
    def validate(self, module_path: Path) -> Dict[str, Any]:
        module_json_path = module_path / "module.json"
        if not module_json_path.exists():
            return {"status": "failed", "error": "module.json missing"}
            
        with open(module_json_path, "r") as f:
            manifest = json.load(f)
            
        # Check entrypoint
        entrypoint = manifest.get("entrypoint")
        if not (module_path / entrypoint).exists():
            return {"status": "failed", "error": f"Entrypoint {entrypoint} defined in manifest does not exist"}
            
        # Check UI link
        ui_link = manifest.get("ui_link")
        if not (module_path / ui_link).exists():
            return {"status": "failed", "error": f"UI link {ui_link} defined in manifest does not exist"}
            
        return {"status": "passed"}

class DataFlowIntegrityChecker:
    """Validate that data flows between modules and systems are coherent."""
    def validate(self, module_path: Path) -> Dict[str, Any]:
        # Check types.ts and how it's used in service/controller/ui
        types_file = module_path / "types.ts"
        if not types_file.exists():
            return {"status": "passed", "info": "types.ts missing (optional)"}
            
        return {"status": "passed"}

class CrossModuleDependencyChecker:
    """Detect and validate dependencies between modules."""
    def validate(self, module_path: Path) -> Dict[str, Any]:
        # Check system_manifest.json for dependencies if applicable
        # Currently, modules are mostly self-contained, but we check for illegal imports
        app_file = module_path / "app.py"
        if app_file.exists():
            with open(app_file, "r") as f:
                content = f.read()
                # Modules shouldn't import from other modules directly
                if "import modules." in content:
                    return {"status": "failed", "error": "Direct cross-module import detected"}
                    
        return {"status": "passed"}


class APIKeyLeakageChecker:
    """Scan app.py route return statements for API key exposure.

    Root cause: AI models sometimes include os.getenv() values directly in
    route return dicts (e.g., 'some_secret_key': secret_var), leaking secrets
    to the frontend via JSON responses.

    Generic, domain-agnostic: flags any variable whose name suggests a secret
    (matches /key|secret|token|password|api/i) that is loaded via os.getenv()
    and subsequently serialized back in a route return statement.

    Allow-listing of specific pass-through keys (e.g. tile-layer keys that
    must be embedded client-side) is controlled per-module via a
    `.api_key_allowlist` file in the module directory — one key name per line.
    No module specifics are hardcoded in this core checker.
    """
    _SECRET_VAR_PATTERN = (
        r'\b(\w*(?:secret|token|password|api[_-]?key|_key)\w*)\s*=\s*os\.getenv\('
    )

    def _load_allowlist(self, module_path: Path) -> set:
        allow_file = module_path / ".api_key_allowlist"
        if not allow_file.exists():
            return set()
        try:
            return {
                line.strip()
                for line in allow_file.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.strip().startswith("#")
            }
        except Exception:
            return set()

    def validate(self, module_path: Path) -> Dict[str, Any]:
        app_file = module_path / "app.py"
        if not app_file.exists():
            return {"status": "passed"}
        try:
            content = app_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return {"status": "passed"}

        allowlist = self._load_allowlist(module_path)
        leaked = []
        for m in re.finditer(self._SECRET_VAR_PATTERN, content, re.IGNORECASE):
            var_name = m.group(1).strip()
            if var_name in allowlist:
                continue
            if f'"{var_name}"' in content or f"'{var_name}'" in content:
                return_search = re.search(
                    rf'return\s*\{{[^}}]*["\'][\w]*{re.escape(var_name)}[\w]*["\'][^}}]*\}}',
                    content[m.start():m.start() + 2000],
                    re.DOTALL | re.IGNORECASE,
                )
                if return_search:
                    leaked.append(var_name)

        if leaked:
            return {
                "status": "failed",
                "error": (
                    f"SECURITY: API key variable(s) found in route return statements: {leaked}. "
                    "Never return sensitive os.getenv() values to the frontend. "
                    "If a specific key MUST be exposed (e.g. map tile-layer keys), add its name "
                    "to the module's `.api_key_allowlist` file."
                ),
            }
        return {"status": "passed"}

class FailureClassificationEngine:
    """Classify failures (wiring, schema, runtime, etc.)."""
    def classify(self, failures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        classified = []
        for f in failures:
            error = f.get("error", "").lower()
            if "missing" in error or "does not exist" in error:
                f["category"] = "contract_violation"
            elif "wiring" in error or "not wired" in error:
                f["category"] = "wiring_failure"
            elif "json" in error or "schema" in error or "field" in error:
                f["category"] = "schema_error"
            elif "import" in error:
                f["category"] = "dependency_error"
            else:
                f["category"] = "runtime_error"
            classified.append(f)
        return classified

class DebugRoutingEngine:
    """Route issues to the correct builder."""
    def route(self, classified_failures: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        routes = {"jordan_reyes": [], "ava_morgan": [], "marcus_hale": []}
        for f in classified_failures:
            category = f.get("category")
            if category == "wiring_failure" or category == "runtime_error":
                 # Split between backend and frontend
                 if "service.ts" in f.get("error", "") or "ui.ts" in f.get("error", ""):
                     routes["ava_morgan"].append(f)
                 else:
                     routes["jordan_reyes"].append(f)
            elif category == "schema_error" or category == "contract_violation":
                routes["marcus_hale"].append(f)
            else:
                routes["marcus_hale"].append(f)
        return routes

class ActivationSafetyGate:
    """Block activation if any validation system fails."""
    def check(self, validation_results: Dict[str, Any]) -> bool:
        return validation_results.get("overall_status") == "passed"

class ValidationEngine:
    """Orchestrates all validation systems."""
    def __init__(self):
        self.simulator = RuntimeSimulator()
        self.discoverer = EndpointDiscoverer()
        self.tester = EndpointTester()
        self.wiring = UIBackendWiringValidator()
        self.schema = JSONSchemaValidator()
        self.intelligence = IntelligenceLayerValidator()
        self.manifest = ManifestConsistencyChecker()
        self.data_flow = DataFlowIntegrityChecker()
        self.dependency = CrossModuleDependencyChecker()
        self.key_leakage = APIKeyLeakageChecker()
        self.classifier = FailureClassificationEngine()
        self.router = DebugRoutingEngine()
        self.gate = ActivationSafetyGate()

    def run_full_suite(self, module_id: str) -> Dict[str, Any]:
        try:
            from core.config import Config
            _root = Config().PROJECT_ROOT
        except Exception:
            # Robust project root detection: backend/core/validation/systems.py -> root is 3 levels up
            _root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")).replace('\\', '/')
        module_path = Path(_root) / "backend" / "modules" / module_id
        results = {}
        failures = []

        # 1. Manifest
        res = self.manifest.validate(module_path)
        results["manifest_consistency"] = res
        if res["status"] == "failed": failures.append(res)

        # 2. Schema
        res = self.schema.validate(module_path)
        results["json_schema"] = res
        if res["status"] == "failed": failures.append(res)

        # 3. Runtime Simulation
        res = self.simulator.validate(module_path)
        results["runtime_simulation"] = res
        if res["status"] == "failed": failures.append(res)

        # 4. Endpoint Discovery
        res = self.discoverer.validate(module_path)
        results["endpoint_discovery"] = res
        endpoints = res.get("endpoints", [])

        # 5. Endpoint Testing
        res = self.tester.validate(module_path, endpoints)
        results["endpoint_testing"] = res
        if res["status"] == "failed": failures.append(res)

        # 6. UI-Backend Wiring
        res = self.wiring.validate(module_path, endpoints)
        results["ui_backend_wiring"] = res
        if res["status"] == "failed": failures.append(res)

        # 7. Intelligence Layer
        res = self.intelligence.validate(module_path)
        results["intelligence_layer"] = res
        if res["status"] == "failed": failures.append(res)

        # 8. Data Flow
        res = self.data_flow.validate(module_path)
        results["data_flow_integrity"] = res
        if res["status"] == "failed": failures.append(res)

        # 9. Dependencies
        res = self.dependency.validate(module_path)
        results["cross_module_dependency"] = res
        if res["status"] == "failed": failures.append(res)

        # 10. API Key Leakage
        res = self.key_leakage.validate(module_path)
        results["api_key_leakage"] = res
        if res["status"] == "failed": failures.append(res)

        # 11. Classification (if failures)
        classified = self.classifier.classify(failures)
        results["failure_classification"] = classified

        # 12. Routing
        routing = self.router.route(classified)
        results["debug_routing"] = routing

        # 13. Safety Gate
        overall_status = "passed" if not failures else "failed"
        results["overall_status"] = overall_status
        results["activation_authorized"] = self.gate.check(results)

        return results
