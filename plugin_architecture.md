# Plugin Architecture: New Beginnings

This document defines the authoritative plugin architecture for the New Beginnings system. All modules must adhere to these specifications to ensure system integrity, portability, and autonomous manageability.

## 1. Module Boundaries
- **Isolation**: All module-specific files must reside within `modules/<module_name>/`.
- **Enforcement**: Modules are strictly prohibited from creating or modifying files outside their designated folder. Core directories (`core/`, `backend/`, `frontend/`) and root-level files are off-limits for module-level logic.

## 2. Required Module Structure
Each module must follow this standardized file contract to ensure successful registration and cross-platform compatibility:

```text
backend/modules/<module_name>/
├── app.py             # Python entrypoint (FastAPI router)
├── module.json        # Mandatory metadata contract
├── index.ts           # Main UI entrypoint
├── service.ts         # Business logic (TypeScript)
├── controller.ts      # UI controller/state management
├── ui.ts              # UI components/definitions
├── types.ts           # TypeScript type definitions
├── README.md          # Module overview
└── index.html         # (Optional) Module root HTML
```

## 3. The module.json Contract
The `module.json` file is the mandatory metadata manifest for every module.

### Required Fields:
- **name**: Unique identifier for the module.
- **description**: Short summary of module functionality.
- **version**: Semantic version string (e.g., "1.0.0").
- **entrypoint**: Path to the main execution file (e.g., "src/main.py").
- **ui_link**: Relative URL for the module's dashboard integration (e.g., "/modules/<module_name>/static/index.html").
- **language**: Primary programming language (e.g., "python", "typescript").
- **status**: Current lifecycle state ("uninitialized", "registered", "active", "failed").

### Optional Fields:
- **dependencies**: List of required modules or external packages.
- **author**: Module creator or maintainer.
- **license**: Software license type.

## 4. Integration Engine Responsibilities
The Integration Engine manages the lifecycle and registration of modules:
- **Discovery**: Scans the `modules/` directory for new `module.json` manifests.
- **Validation**: Verifies the `module.json` contract and folder structure.
- **Import**: Dynamically imports the specified `entrypoint`.
- **Registry Management**: Registers validated module metadata into the system `REGISTRY`.
- **Dashboard Exposure**: Exposes the `REGISTRY` to the frontend for dynamic UI updates.

## 5. DelegationEngine Responsibilities
The DelegationEngine enforces the rules of the architecture:
- **Boundary Enforcement**: Prevents file system operations outside `modules/<module_name>/`.
- **Schema Validation**: Validates `module.json` against the required schema.
- **Lifecycle Management**: Tracks and updates module states (uninitialized, registered, active, failed).
- **Integrity Checks**: Prevents folder pollution, identifies phantom modules, and validates version compatibility.
- **Execution Safety**: Verifies the existence of entrypoints and executes `health_check()` if implemented by the module.

## 6. Dashboard Integration Rules
- **Auto-Discovery**: The dashboard must dynamically discover modules by querying the `REGISTRY`.
- **No Hardcoding**: Hardcoded module tiles or navigation links are strictly forbidden.
- **Dynamic Routing**: Navigation and UI links are derived exclusively from the `ui_link` property in `module.json`.

## 7. AI-Generated Module Guardrails
When the AI generates or modifies modules, it must adhere to these constraints:
- **Scoped Operations**: All modifications must be contained within `modules/<module_name>/`.
- **Manifest Integrity**: A valid and accurate `module.json` must be generated for every module.
- **Core Protection**: The AI must never touch `core/`, `dashboard/`, `backend/`, `frontend/`, or root-level files during module creation.
- **Structure Adherence**: The standardized folder structure defined in Section 2 must be followed exactly.
