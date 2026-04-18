import os
from pathlib import Path
from typing import Dict, List, Optional

import time

class ProjectMap:
    _instance = None
    _last_scan = 0
    _scan_cache = {}

    def __new__(cls, root_dir: str = None):
        if cls._instance is None:
            cls._instance = super(ProjectMap, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self, root_dir: str = None):
        if self.initialized and time.time() - self._last_scan < 300: # 5 minute cache
            return
            
        if root_dir is None:
            # Try to find root by looking for backend/ from the current file's location
            current_file_path = Path(__file__).resolve()
            # If we are in backend/tools/project_map.py, root is 2 levels up
            candidate = current_file_path.parent.parent.parent
            if (candidate / "backend").exists():
                self.root_dir = candidate
            else:
                # Fallback to current working directory or its parent
                cwd = Path.cwd()
                if (cwd / "backend").exists():
                    self.root_dir = cwd
                elif (cwd.parent / "backend").exists():
                    self.root_dir = cwd.parent
                else:
                    # Final fallback: assume current file's parent's parent's parent
                    self.root_dir = candidate
        else:
            self.root_dir = Path(root_dir)
        
        # Normalize root_dir to absolute and resolve to avoid case issues
        if self.root_dir.exists():
            self.root_dir = self.root_dir.resolve()
        
        self.map = {
            "frontend_modules": {},
            "backend_modules": {},
            "ts_files": [],
            "routing_files": [],
            "api_endpoints": [],
            "component_folders": [],
            "utility_folders": []
        }
        self.exclude_dirs = ["node_modules", "venv", ".git", "dist", "build", "__pycache__", "static/built"]
        self.scan()
        self.initialized = True
        self._last_scan = time.time()

    def _should_skip(self, path: Path) -> bool:
        parts = path.parts
        return any(ex in parts for ex in self.exclude_dirs)

    def scan(self):
        # Scan Backend
        backend_dir = self.root_dir / "backend"
        if backend_dir.exists():
            self._scan_path(backend_dir, self._backend_handler)
        
        # Scan Frontend
        frontend_dir = self.root_dir / "frontend"
        if frontend_dir.exists():
            self._scan_path(frontend_dir, self._frontend_handler)

        # Scan backend/frontend (modern structure)
        be_fe_dir = self.root_dir / "backend" / "frontend"
        if be_fe_dir.exists():
            self._scan_path(be_fe_dir, self._frontend_handler)

        # Scan backend/modules (modular structure)
        modules_dir = self.root_dir / "backend" / "modules"
        if modules_dir.exists():
            for mod_folder in modules_dir.iterdir():
                if mod_folder.is_dir() and not self._should_skip(mod_folder):
                    self._scan_module_folder(mod_folder)
        
    def _scan_path(self, path: Path, handler):
        import os
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
            root_path = Path(root)
            for f in files:
                handler(root_path / f)

    def _scan_module_folder(self, path: Path):
        name = path.name
        # Add as backend module
        self.map["backend_modules"][name] = str(path.relative_to(self.root_dir))
        
        # Add as frontend module if entry point exists
        entry_points = ["index.tsx", "index.ts", "main.tsx", "main.ts", "app.tsx", "app.ts", "dashboard.tsx", "dashboard.ts"]
        subdirs = [".", "src", "source"]
        
        found_entry = False
        for subdir in subdirs:
            for entry in entry_points:
                entry_path = path / subdir / entry
                if entry_path.exists():
                    self.map["frontend_modules"][name] = str(entry_path.relative_to(self.root_dir))
                    found_entry = True
                    break
            if found_entry:
                break
        
        # Also scan for .ts/.tsx files within module
        self._scan_path(path, self._module_ts_handler)

    def _module_ts_handler(self, item: Path):
        if item.is_file() and item.suffix in [".ts", ".tsx"]:
            self.map["ts_files"].append(str(item.relative_to(self.root_dir)))

    def _backend_handler(self, item: Path):
        if item.is_file():
            if item.suffix == ".py":
                if "route" in item.name.lower():
                    self.map["routing_files"].append(str(item.relative_to(self.root_dir)))
                # Check for API patterns
                if any(x in item.name.lower() for x in ["app", "route", "service", "controller", "main"]):
                    try:
                        with open(item, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            if "@router." in content or "@app." in content:
                                self.map["api_endpoints"].append(str(item.relative_to(self.root_dir)))
                    except:
                        pass
            
            if item.name == "__init__.py" and item.parent.name != "backend":
                mod_name = item.parent.name
                self.map["backend_modules"][mod_name] = str(item.parent.relative_to(self.root_dir))

    def _frontend_handler(self, item: Path):
        if item.is_file():
            if item.suffix in [".ts", ".tsx"]:
                self.map["ts_files"].append(str(item.relative_to(self.root_dir)))
                if "route" in item.name.lower():
                    self.map["routing_files"].append(str(item.relative_to(self.root_dir)))
            
            # Identify modules by presence of entry points or specific structures
            if item.name in ["main.ts", "main.tsx", "app.ts", "app.tsx", "index.ts", "dashboard.ts"]:
                mod_name = item.parent.name
                if mod_name == "src": # Handle Vite-style src/main.tsx
                    mod_name = item.parent.parent.name
                self.map["frontend_modules"][mod_name] = str(item.relative_to(self.root_dir))

    def _scan_sub_app(self, path: Path):
        # Specific scan for sub-apps
        name = path.name
        be = path / "backend"
        if be.exists():
            self.map["backend_modules"][f"{name}_backend"] = str(be.relative_to(self.root_dir))
        
        fe = path / "frontend"
        if fe.exists():
            # Find entry point
            for entry in ["app.ts", "main.ts", "index.ts"]:
                if (fe / entry).exists():
                    self.map["frontend_modules"][name] = str((fe / entry).relative_to(self.root_dir))
                    break

    def get_frontend_entry(self, module_name: str) -> Optional[str]:
        return self.map["frontend_modules"].get(module_name)

    def get_backend_module(self, module_name: str) -> Optional[str]:
        return self.map["backend_modules"].get(module_name)

    def find_file_by_name(self, name: str) -> List[str]:
        results = []
        for p in self.root_dir.rglob(name):
            if not self._should_skip(p):
                results.append(str(p.relative_to(self.root_dir)))
        return results

    def find_ts_files_containing(self, text: str) -> List[str]:
        results = []
        for ts_file in self.map["ts_files"]:
            full_path = self.root_dir / ts_file
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    if text in f.read():
                        results.append(ts_file)
            except:
                pass
        return results

    def list_frontend_modules(self) -> List[str]:
        return list(self.map["frontend_modules"].keys())

    def list_backend_modules(self) -> List[str]:
        return list(self.map["backend_modules"].keys())

    def to_dict(self):
        return self.map
