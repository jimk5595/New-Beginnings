# personas.py
# Centralized persona registry for the platform
# Each persona has: name, role, department, personality, responsibilities

class BasePersona:
    def __init__(self, data: dict):
        self.data = data.copy()
        # Remove non-serializable class if present
        if "class" in self.data:
            del self.data["class"]
            
        self.name = data.get("name")
        self.role = data.get("role")
        self.department = data.get("department")
        self.personality = data.get("personality", {})
        self.responsibilities = data.get("responsibilities", [])
        self.reasoning_protocol = data.get("reasoning_protocol", "")
        self.escalation_protocol = data.get("escalation_protocol", "")
        self.persona_template = (
            "PERSONA TEMPLATE:"
            " ROLE: Understand your domain responsibilities clearly."
            " CREATIVITY: You possess a deep sense of creativity within your domain. "
            " Apply innovative thinking, aesthetic excellence, and creative problem-solving to all tasks while remaining strictly within your functional boundaries. "
            " REASONING: Think like a specialist working inside a constrained, existing system. "
            " Never guess file paths, module names, component names, or architecture. "
            " Ask one clarifying question if context is missing."
            " CONSTRAINTS: Modify ONLY existing files unless explicitly authorized. "
            " 9-FILE CONTRACT: If building a module, you MUST create exactly 9 files: module.json, app.py, index.html, styles.css, index.ts, service.ts, controller.ts, ui.ts, types.ts. "
            " Do NOT create new folders, modules, or dependencies without permission."
            " SELF-AUDIT: Before returning output, verify that changes are minimal, safe, "
            " rule-compliant, and directly related to the task."
            " ESCALATION: Follow the chain of command — Specialists escalate to Marcus, "
            " Marcus escalates to Eliza, Eliza escalates to the user when system rules or "
            " user intent cannot be resolved."
        )
        self.no_guessing_rule = (
            "GLOBAL RULE: Never guess file paths, module names, component names, "
            "config keys, or architecture. If any required detail is missing, "
            "ask one clarifying question or abort with a clear error instead of guessing."
        )

    def to_dict(self):
        """Return a serializable dictionary representation of the persona."""
        return {
            "name": self.name,
            "role": self.role,
            "department": self.department,
            "personality": self.personality,
            "responsibilities": self.responsibilities,
            "domain": self.data.get("domain", "general")
        }

class ElizaPersona(BasePersona): pass
class MarcusPersona(BasePersona): pass
class AvaPersona(BasePersona): pass
class JordanPersona(BasePersona): pass
class FullstackPersona(BasePersona): pass
class ReviewPersona(BasePersona): pass
class DesignPersona(BasePersona): pass
class UXPersona(BasePersona): pass
class SEOPersona(BasePersona): pass
class SystemOpsPersona(BasePersona): pass
class DebuggingPersona(BasePersona): pass
class ValidatorPersona(BasePersona): pass
class ArchitectPersona(BasePersona): pass
class DataSpecialistPersona(BasePersona): pass
class LogicAnalystPersona(BasePersona): pass
class CreativePersona(BasePersona): pass

class SoftwareEngineerPersona(BasePersona): pass
class UIProgrammerPersona(BasePersona): pass
class ToolsEngineerPersona(BasePersona): pass

PERSONAS = {}

# --- DYNAMIC REGISTRY IMPLEMENTATION ---
import sys
import os

# Add parent directory to path to find persona_manager
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from persona_manager import persona_manager
    # Initial load will happen here, but also in orchestrator startup
    dynamic_registry = persona_manager.load_personas()
except ImportError:
    # Fallback for direct script execution or path issues
    dynamic_registry = {}

# Map domain to persona class
DOMAIN_CLASS_MAP = {
    "executive": ElizaPersona,
    "build": MarcusPersona,
    "backend": JordanPersona,
    "frontend": AvaPersona,
    "fullstack": FullstackPersona,
    "review": ReviewPersona,
    "design": DesignPersona,
    "ux": UXPersona,
    "seo": SEOPersona,
    "system": SystemOpsPersona,
    "debugging": DebuggingPersona,
    "validation": ValidatorPersona,
    "architecture": ArchitectPersona,
    "data": DataSpecialistPersona,
    "logic": LogicAnalystPersona,
    "creative": CreativePersona
}

# Populate PERSONAS from dynamic registry
if dynamic_registry:
    for pid, data in dynamic_registry.items():
        domain = data.get("domain", "general")
        persona_class = DOMAIN_CLASS_MAP.get(domain, BasePersona)
        
        PERSONAS[pid] = {
            "class": persona_class,
            "name": data.get("name"),
            "role": data.get("role"),
            "department": data.get("reports_to", "Operations"), # Using reports_to as department if missing
            "personality": {
                "traits": ["creative"],
                "style": f"{data.get('personality', '')} {data.get('tone', '')} Creative within their domain.".strip()
            },
            "responsibilities": [],
            "domain": domain
        }

# Ensure we don't break existing code that expects certain keys
# Specifically ensure 'eliza' and other core personas are present for DelegationEngine
CORE_DEFAULTS = {
    "eliza": {"class": ElizaPersona, "name": "Eliza", "role": "Executive Manager & COO", "domain": "executive"},
    "marcus_hale": {"class": MarcusPersona, "name": "Marcus Hale", "role": "Operations Manager", "domain": "build"},
    "mira_kessler": {"class": ValidatorPersona, "name": "Dr. Mira Kessler", "role": "Chief Validator & Gatekeeper", "domain": "validation"},
    "rowan_hale": {"class": ArchitectPersona, "name": "Rowan Hale", "role": "Systems Architect", "domain": "architecture"},
    "selene_ward": {"class": DataSpecialistPersona, "name": "Selene Ward", "role": "Data & Knowledge Specialist", "domain": "data"},
    "orion_locke": {"class": LogicAnalystPersona, "name": "Orion Locke", "role": "Logic & Consistency Analyst", "domain": "logic"},
    "kaia_riven": {"class": CreativePersona, "name": "Kaia Riven", "role": "Creative Systems Designer", "domain": "creative"},
    "elliot_shea": {"class": SoftwareEngineerPersona, "name": "Elliot Shea", "role": "Lead Programmer", "domain": "logic"},
    "isaac_moreno": {"class": SoftwareEngineerPersona, "name": "Isaac Moreno", "role": "Senior Software Engineer", "domain": "backend"},
    "juniper_ryle": {"class": UIProgrammerPersona, "name": "Juniper Ryle", "role": "UI Programmer", "domain": "frontend"},
    "naomi_kade": {"class": ToolsEngineerPersona, "name": "Naomi Kade", "role": "Tools Engineer", "domain": "system"}
}

for pid, defaults in CORE_DEFAULTS.items():
    if pid not in PERSONAS:
        PERSONAS[pid] = {
            "class": defaults["class"],
            "name": defaults["name"],
            "role": defaults["role"],
            "department": "Operations",
            "personality": {"traits": ["creative"], "style": "Highly creative within their domain."},
            "responsibilities": [],
            "domain": defaults["domain"]
        }
