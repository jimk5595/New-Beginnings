import os
import psutil
import time
from typing import Dict, Any

class SystemStatusMonitor:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SystemStatusMonitor, cls).__new__(cls)
            cls._instance.state = {
                "registry_state": {},
                "loader_state": {},
                "validator_state": {},
                "mount_state": {},
                "build_gate_state": {},
                "asgi_state": {}
            }
        return cls._instance

    def update_registry(self, module_name: str, status: str, metadata: Dict[str, Any], errors: list = None):
        self.state["registry_state"][module_name] = {
            "status": status,
            "metadata_present": bool(metadata),
            "router_present": "router" in metadata if metadata else False,
            "errors": errors or [],
            "last_update": time.time()
        }

    def update_loader(self, module_name: str, success: bool, error: str = None, stale_cache: bool = False):
        self.state["loader_state"][module_name] = {
            "success": success,
            "error": error,
            "stale_import_cache": stale_cache,
            "timestamp": time.time()
        }

    def update_validator(self, module_name: str, url: str, status_code: int, body: str, timing: float):
        self.state["validator_state"][module_name] = {
            "url": url,
            "status_code": status_code,
            "response_snippet": body[:200] if body else None,
            "timing_ms": timing * 1000,
            "timestamp": time.time()
        }

    def update_mount(self, module_name: str, success: bool, log: str = None):
        self.state["mount_state"][module_name] = {
            "success": success,
            "log": log,
            "timestamp": time.time()
        }

    def update_build_gate(self, module_name: str, success: bool, reason: str = None):
        self.state["build_gate_state"][module_name] = {
            "success": success,
            "reason": reason,
            "timestamp": time.time()
        }

    def get_asgi_state(self, force: bool = False):
        # Only refresh once per 60 seconds unless forced
        current_time = time.time()
        last_update = self.state.get("asgi_state", {}).get("timestamp", 0)
        if not force and (current_time - last_update < 60):
            return self.state["asgi_state"]

        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if not proc.info or not proc.info.get('name'):
                        continue
                    if 'uvicorn' in proc.info['name'].lower() or 'python' in proc.info['name'].lower():
                        cmdline = proc.info.get('cmdline')
                        if cmdline and 'main:app' in ' '.join(cmdline):
                            processes.append({
                                "pid": proc.info['pid'],
                                "cmdline": cmdline
                            })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            # Fallback if psutil fails entirely
            pass
        
        self.state["asgi_state"] = {
            "process_count": len(processes),
            "processes": processes,
            "timestamp": current_time
        }
        return self.state["asgi_state"]

    def get_full_status(self, module_name: str = None) -> Dict[str, Any]:
        self.get_asgi_state()
        if module_name:
            return {
                "registry_state": self.state["registry_state"].get(module_name),
                "loader_state": self.state["loader_state"].get(module_name),
                "validator_state": self.state["validator_state"].get(module_name),
                "mount_state": self.state["mount_state"].get(module_name),
                "build_gate_state": self.state["build_gate_state"].get(module_name),
                "asgi_state": self.state["asgi_state"]
            }
        return self.state

system_monitor = SystemStatusMonitor()
