import os
import re
import json
import logging
import importlib
import pkgutil
from typing import Dict, Any, List

logger = logging.getLogger("PersonaManager")
logger.setLevel(logging.INFO)

PERSONAS_DIR = os.path.join(os.path.dirname(__file__), "personas")
RESOURCES_DIR = os.path.join(os.path.dirname(__file__), "resources")
MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "system_manifest.json")
REFERENCE_LINKS_PATH = os.path.join(RESOURCES_DIR, "reference_links")

DOMAIN_KEYWORDS = {
    "debugging": ["debug", "broken", "fail", "error", "routing", "manifest", "build", "integration", "repair", "fix"],
    "build": ["build", "create", "generate", "make", "setup", "new", "module", "folder", "file"],
    "backend": ["api", "database", "service", "endpoint", "model", "server", "logic"],
    "frontend": ["ui", "interface", "button", "layout", "react", "css", "html", "javascript", "typescript"],
    "design": ["design", "mockup", "visual", "style", "theme"],
    "ux": ["ux", "flow", "wireframe", "usability", "experience"],
    "seo": ["seo", "keywords", "ranking", "meta"],
    "cro": ["cro", "conversion", "funnel", "optimize"],
    "executive": ["plan", "strategy", "overview", "roadmap", "coordinate", "manage"],
    "software_engineering": ["complex", "multi-domain", "heavy software", "performance", "system", "refactor", "intricate"],
    "web_development": ["dropshipping", "store", "landing page", "simple dashboard", "website"],
    "science": ["physics", "chemistry", "biology", "neuroscience", "medical", "oncology", "earth science", "seismic", "climate", "research", "laboratory", "experiment"]
}

from persona import Persona

class PersonaManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PersonaManager, cls).__new__(cls)
            cls._instance.registry = {}
            cls._instance.resources = {}
            cls._instance.initialized = False
        return cls._instance

    def load_resources(self):
        """Loads shared system resources."""
        if os.path.exists(REFERENCE_LINKS_PATH):
            try:
                self.resources["reference_links_path"] = REFERENCE_LINKS_PATH
                logger.info("Shared resource 'reference_links' identified.")
            except Exception as e:
                logger.error(f"Failed to access resource file: {e}")
        
        rules_path = os.path.join(RESOURCES_DIR, "rules.md")
        if os.path.exists(rules_path):
            self.resources["rules_path"] = rules_path
            logger.info("Shared resource 'rules.md' identified.")

    def load_personas(self):
        """Discovers and parses all persona files (.md and .py)."""
        self.load_resources()
        if not os.path.exists(PERSONAS_DIR):
            logger.error(f"Personas directory not found: {PERSONAS_DIR}")
            return

        self.registry = {}
        
        # 1. Load Markdown Personas
        for root, dirs, files in os.walk(PERSONAS_DIR):
            # Check for department registry JSON
            if "department_registry.json" in files:
                try:
                    registry_path = os.path.join(root, "department_registry.json")
                    with open(registry_path, "r", encoding="utf-8") as f:
                        dept_data = json.load(f)
                    
                    # Process sub-departments recursively
                    def process_dept(data):
                        if isinstance(data, list):
                            for p in data:
                                pid = p["id"]
                                self.registry[pid] = {
                                    "id": pid,
                                    "name": p["name"],
                                    "role": p["role"],
                                    "full_content": f"Persona: {p['name']}\nRole: {p['role']}\nExpertise: {', '.join(p['expertise'])}\nPersonality: {p['personality']}\nResources: {', '.join(p['resources'])}",
                                    "tone": p.get("personality", "Professional"),
                                    "type": "json_registry",
                                    "domain": self._infer_domain(p["role"] + " " + " ".join(p["expertise"]))
                                }
                                logger.info(f"Loaded registry persona: {pid}")
                        elif isinstance(data, dict):
                            for key, value in data.items():
                                process_dept(value)

                    if "sub_departments" in dept_data:
                        process_dept(dept_data["sub_departments"])
                    if "director" in dept_data:
                        d = dept_data["director"]
                        self.registry[d["id"]] = {
                            "id": d["id"],
                            "name": d["name"],
                            "role": d["role"],
                            "full_content": f"Persona: {d['name']}\nRole: {d['role']}\nPersonality: {d['personality']}\nResources: {', '.join(d['resources'])}",
                            "tone": d.get("personality", "Professional"),
                            "type": "json_registry",
                            "domain": self._infer_domain(d["role"])
                        }
                except Exception as e:
                    logger.error(f"Failed to load department registry in {root}: {e}")

            for filename in files:
                if filename.endswith(".md"):
                    file_path = os.path.join(root, filename)
                    persona_id = filename[:-3]
                    try:
                        persona_data = self._parse_persona_file(file_path)
                        persona_data["id"] = persona_id
                        persona_data["type"] = "markdown"
                        self.registry[persona_id] = persona_data
                        logger.info(f"Loaded markdown persona: {persona_id}")
                    except Exception as e:
                        logger.error(f"Failed to parse markdown persona {filename}: {e}")

        # 2. Load Python Personas (Legacy/Class-based)
        try:
            self._load_python_personas()
        except Exception as e:
            logger.error(f"Failed to load python personas: {e}")

        self.initialized = True
        self._update_system_manifest()
        return self.registry

    def _load_python_personas(self):
        """Discovers and imports personas defined as Python classes."""
        # 1. Try to load from personas.registry if it exists (legacy)
        try:
            from personas.registry import PERSONA_REGISTRY
            for pid, instance in PERSONA_REGISTRY.items():
                if pid not in self.registry:
                    self.registry[pid] = {
                        "id": pid,
                        "name": instance.name,
                        "role": instance.description,
                        "full_content": instance.system_prompt,
                        "tone": instance.style,
                        "type": "python",
                        "domain": self._infer_domain(instance.description)
                    }
                    logger.info(f"Loaded python persona (from registry): {pid}")
        except ImportError:
            pass

        # 2. Dynamic Discovery (New System)
        # We look for all .py files in personas/ subdirectories and check for Persona subclasses
        for root, dirs, files in os.walk(PERSONAS_DIR):
            for filename in files:
                if filename.endswith(".py") and filename not in ["__init__.py", "base.py", "base_persona.py", "factory.py", "registry.py", "loader.py"]:
                    # Construct module path
                    rel_path = os.path.relpath(os.path.join(root, filename), os.path.dirname(PERSONAS_DIR))
                    module_name = rel_path.replace(os.path.sep, ".").replace(".py", "")
                    
                    try:
                        module = importlib.import_module(module_name)
                        for attr in dir(module):
                            obj = getattr(module, attr)
                            # Check if it's a class and inherits from Persona (but is not Persona itself)
                            if isinstance(obj, type) and issubclass(obj, Persona) and obj is not Persona:
                                try:
                                    instance = obj()
                                    pid = filename.replace(".py", "")
                                    if pid not in self.registry:
                                        self.registry[pid] = {
                                            "id": pid,
                                            "name": instance.name,
                                            "role": instance.description,
                                            "full_content": instance.system_prompt,
                                            "tone": instance.style,
                                            "type": "python",
                                            "domain": self._infer_domain(instance.description)
                                        }
                                        logger.info(f"Dynamically loaded python persona: {pid} from {module_name}")
                                except Exception as inst_e:
                                    logger.debug(f"Could not instantiate {attr} in {module_name}: {inst_e}")
                    except Exception as e:
                        logger.debug(f"Failed to import persona module {module_name}: {e}")

    def _infer_domain(self, role: str) -> str:
        role_lower = role.lower()
        for domain, keywords in DOMAIN_KEYWORDS.items():
            if any(kw in role_lower for kw in keywords):
                return domain
        return "general"

    def get_persona(self, persona_id: str) -> Persona:
        """Retrieves a persona object by ID."""
        if not self.initialized:
            self.load_personas()
        
        data = self.registry.get(persona_id)
        if not data:
            # Fallback to Eliza
            if persona_id != "eliza":
                return self.get_persona("eliza")
            return Persona(
                name="Eliza",
                description="Executive Manager & COO",
                system_prompt="You are Eliza, the COO. Respond professionally.",
                style="Professional, decisive"
            )

        return Persona(
            name=data.get("name", persona_id.title()),
            description=data.get("role", "Specialist"),
            system_prompt=data.get("full_content", ""),
            style=data.get("tone", "Professional")
        )

    def _parse_persona_file(self, file_path: str) -> Dict[str, Any]:
        """Parses the metadata from a persona markdown file."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        metadata = {}
        metadata["resources"] = [] # Initialize as list
        # Simple Key: Value parsing for the top of the file
        lines = content.split("\n")
        in_resources = False
        for line in lines:
            line_strip = line.strip()
            if line.startswith("General Resources:") or line.startswith("Resources:"):
                in_resources = True
                continue
            
            if in_resources:
                if line_strip.startswith("- http"):
                    metadata["resources"].append(line_strip.replace("- ", "").strip())
                    continue
                elif line_strip == "" or ":" in line:
                    in_resources = False
            
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower().replace(" ", "_")
                if key in ["name", "full_name", "role", "reports_to", "domain", "capabilities", "personality", "tone", "department"]:
                    # Normalize keys
                    if key == "full_name": key = "name"
                    if key == "capabilities": key = "domain"
                    metadata[key] = value.strip()
            elif line.startswith("# Persona:"):
                metadata["name"] = line.replace("# Persona:", "").strip()

        # Defaults
        if "name" not in metadata:
            metadata["name"] = os.path.basename(file_path).replace(".md", "").title()
        if "role" not in metadata:
            metadata["role"] = "Specialist"
        if "reports_to" not in metadata:
            metadata["reports_to"] = "Eliza"
        if "domain" not in metadata:
            metadata["domain"] = self._infer_domain(metadata["role"])

        metadata["full_content"] = content
        # Ensure system-wide resources are also available
        if "reference_links_path" in self.resources:
             metadata["system_resources_path"] = self.resources["reference_links_path"]
             
        return metadata

    def _update_system_manifest(self):
        """Injects active personas into system_manifest.json."""
        if not os.path.exists(MANIFEST_PATH):
            logger.warning(f"Manifest not found at {MANIFEST_PATH}")
            return

        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            manifest["resources"] = self.resources
            manifest["active_personas"] = {
                pid: {
                    "name": data["name"],
                    "role": data["role"],
                    "status": "active",
                    "domain": data["domain"],
                    "type": data.get("type", "markdown")
                }
                for pid, data in self.registry.items()
            }

            with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=4)
            logger.info("Updated system_manifest.json with active personas.")
        except Exception as e:
            logger.error(f"Failed to update manifest: {e}")

    def get_keywords_map(self) -> Dict[str, str]:
        """Builds a keyword-to-category map based on loaded personas."""
        keyword_map = {}
        for pid, data in self.registry.items():
            domain = data.get("domain", "general")
            keywords = DOMAIN_KEYWORDS.get(domain, [])
            for kw in keywords:
                keyword_map[kw] = domain
        return keyword_map

    def get_routing_rules(self) -> Dict[str, str]:
        """Returns a domain-to-persona mapping for delegation."""
        routing = {}
        # Sort personas by "Reports To" depth if needed, but for now simple mapping
        for pid, data in self.registry.items():
            domain = data.get("domain")
            if domain and domain != "general":
                # If multiple personas have the same domain, we might need more logic
                # For now, let the most recent one (or first one) win
                if domain not in routing:
                    routing[domain] = pid
        
        # Ensure core roles are mapped
        if "executive" not in routing and "eliza" in self.registry:
            routing["executive"] = "eliza"
        if "build" not in routing and "noah_patel" in self.registry:
            routing["build"] = "noah_patel"
            
        return routing

    def get_all_persona_names(self) -> List[Dict[str, str]]:
        """Returns a list of all persona IDs and names for identification."""
        if not self.initialized:
            self.load_personas()
        return [{"id": pid, "name": data.get("name", pid.title())} for pid, data in self.registry.items()]

persona_manager = PersonaManager()
