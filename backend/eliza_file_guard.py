import os
import sys

def audit_file_operation(filepath: str):
    """
    Sudo-level audit: Enforces Module-Scoped writes and TS-ONLY platform rules.
    """
    # Robust project root detection
    try:
        from tools.project_map import ProjectMap
        project_root = str(ProjectMap().root_dir).replace('\\', '/')
    except:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")).replace('\\', '/')
    
    # Normalize for comparison
    if os.path.isabs(filepath):
        rel_path = os.path.relpath(filepath, project_root).replace('\\', '/')
    else:
        rel_path = filepath.replace('\\', '/')
    
    # 1. ROOT CHECK: must be within project_root
    if rel_path.startswith('..'):
         raise PermissionError(f"CRITICAL ERROR: Attempt to access outside project root: {rel_path}")

    # 1.1 POLLUTION CHECK: Block redundant backend nesting
    if "backend/backend" in rel_path or "backend/frontend/backend" in rel_path:
         raise PermissionError(f"POLLUTION VIOLATION: Illegal nested backend structure detected: {rel_path}")

    # 2. TS-ONLY RULE: JavaScript is strictly FORBIDDEN in modules.
    if (rel_path.endswith('.js') or rel_path.endswith('.jsx')) and "backend/modules/" in rel_path:
         raise PermissionError(f"TS-ONLY VIOLATION: JavaScript file '{rel_path}' is strictly forbidden. Modules MUST use TypeScript (.ts, .tsx) and Python (.py).")
    
    # 2.1 SUBDIRECTORY BLOCK: Subdirectories are ALLOWED for organization.
    if "backend/modules/" in rel_path:
        # Enforce module-scoped logic
        pass

    # 2.2 BUILD BYPASS: Allow .js in static/built (compiler output)
    if "backend/static/built" in rel_path:
        print(f"SUDO AUDIT PASSED: Build artifact '{rel_path}' authorized.")
        return

    # 3. TEAM-BASED ACCESS CONTROL
    current_persona = os.environ.get("CURRENT_PERSONA", "unknown").lower()
    
    # Software Engineer Team members
    # Handles all complex builds, repairs, and performance upgrades. Full repository access.
    software_engineers = [
        "elliot_shea", "isaac_moreno", "juniper_ryle", "naomi_kade", 
        "mira_kessler", "rowan_hale", "selene_ward", "orion_locke"
    ]
    
    # Web Development Team
    # Marcus is the Senior Developer. Handles store creation, dashboards, and landing pages.
    web_developers = [
        "marcus_hale", "alex_rivera", "jordan_reyes", "chloe_bennett", "caleb_monroe"
    ]

    # Management Group (COO / Executive Manager)
    # Granted system-wide access for oversight and configuration.
    management_group = ["eliza"]
    
    is_software_engineer = any(se in current_persona for se in software_engineers)
    is_web_developer = any(wd in current_persona for wd in web_developers)
    is_management = any(mg in current_persona for mg in management_group)

    # 4. MODULE-SCOPE & TEAM ACCESS RULES
    parts = rel_path.split('/')
    allowed_root_files = [".env", ".gitignore", "system_manifest.json", "backend/system_manifest.json", "MANAGEMENT_README.md", "memory_bridge.py", "dashboard.entry", "test_models.py", "validator.py", "build.py", "llm_router.py"]
    
    category = os.environ.get("CURRENT_TASK_CATEGORY", "executive")
    current_module = os.environ.get("CURRENT_MODULE", "").lower()

    # 4.1 EXPANSION LOCK: During expansion/build, direct writes to modules are forbidden.
    # Modules MUST be returned as a JSON blob to the BuildGate.
    if category in ("expansion", "build", "complex_build", "web_build") and rel_path.startswith("backend/modules/"):
         # EXEMPTION for expansion tool setup itself
         if rel_path.endswith(f"backend/modules/{current_module}/"):
              pass
         else:
              raise PermissionError(f"EXPANSION_PROTOCOL_VIOLATION: During module creation ({category}), you MUST NOT write files directly to '{rel_path}'. You MUST return the 5-file core JSON object in your response so it can pass the BuildGate.")
    
    # FULL ACCESS BYPASS (Checked after critical expansion/format rules)
    if is_software_engineer or is_management:
        print(f"SUDO AUDIT PASSED: Authorized group member '{current_persona}' granted system-wide access to '{rel_path}'.")
        return 
    
    category = os.environ.get("CURRENT_TASK_CATEGORY", "executive")
    current_module = os.environ.get("CURRENT_MODULE", "").lower()
    
    # Dashboard and specific root files are exempt from the backend/modules/ rule
    is_dashboard = rel_path == "frontend/index.html" or rel_path.startswith("frontend/dashboard/")
    is_allowed_root = rel_path in allowed_root_files

    # Core system protection: Block any write to backend/ that is NOT in backend/modules/
    # unless it's a known system file (handled by other logic if needed, but here we block module pollution)
    if not is_allowed_root and not is_dashboard:
        if rel_path.startswith('backend/') and not rel_path.startswith('backend/modules/'):
            # Allow existing core files to be modified only if NOT a module task
            if current_module:
                 raise PermissionError(f"MODULE POLLUTION VIOLATION: Module '{current_module}' attempted to write to core backend at '{rel_path}'. All module files must be in backend/modules/.")

        if not rel_path.startswith('backend/modules/') and not rel_path.startswith('frontend/dashboard/'):
             if rel_path.startswith('frontend/'):
                  raise PermissionError(f"FRONTEND POLLUTION VIOLATION: Path: {rel_path}. Use backend/modules/{{module_name}}/")
             if not is_allowed_root:
                  raise PermissionError(f"ROOT POLLUTION VIOLATION: File '{rel_path}' is not allowed in project root. Modules must be in backend/modules/.")

    # 4. CURRENT MODULE ENFORCEMENT
    if current_module and current_module != "new_module":
        # Check if the path is within the current module folder
        if rel_path.startswith('backend/modules/'):
            # Must start with backend/modules/{current_module}/
            expected_prefix = f'backend/modules/{current_module}/'
            if not rel_path.lower().startswith(expected_prefix.lower()):
                 raise PermissionError(f"SCOPE VIOLATION: Module task '{current_module}' attempted to write to wrong module folder: {rel_path}. All files must be in {expected_prefix}")
        else:
            # If a module task is writing outside backend/modules/, and it's not an allowed exception
            if not is_dashboard and not is_allowed_root:
                 raise PermissionError(f"SCOPE VIOLATION: Module task '{current_module}' must write to backend/modules/{current_module}/. Attempted: {rel_path}")
        
        # Additional check for root-level folders if not in backend/modules/
        if not rel_path.startswith('backend/modules/'):
            path_parts = rel_path.split('/')
            if len(path_parts) > 0:
                # If it's a module task, it shouldn't be writing to other root folders (except dashboard/integration)
                if path_parts[0].lower() != current_module and rel_path not in allowed_root_files:
                     if category == "integration" and path_parts[0].lower() == "dashboard":
                         pass
                     else:
                         raise PermissionError(f"SCOPE VIOLATION: Task for module '{current_module}' attempted to write to '{path_parts[0]}' (Full path: {rel_path}).")

    # 5. INTEGRATION_TASK ENFORCEMENT
    if category == "integration":
        # Integration target identification (log only)
        if "dashboard" in rel_path.lower():
            print(f"INTEGRATION TARGET DETECTED: Dashboard at {rel_path}")

        if len(parts) >= 2:
            module_folder = parts[0]
            module_path = os.path.join(project_root, module_folder)
            
            # Target module must exist
            if not os.path.exists(module_path):
                raise PermissionError("Error: Integration tasks cannot create new modules.")
            
            # Never create new folders
            dir_path = os.path.dirname(os.path.join(project_root, rel_path))
            if not os.path.exists(dir_path):
                raise PermissionError(f"Error: Integration tasks cannot create new directories: {os.path.relpath(dir_path, project_root)}")

            # Never generate manifest.json
            if rel_path.endswith("manifest.json"):
                raise PermissionError("Error: Integration tasks are not permitted to generate manifest.json.")

            # Only write files that already exist (Strict enforcement of "Creation not permitted")
            full_path = os.path.join(project_root, rel_path)
            if not os.path.exists(full_path):
                # The directive says: If a required file does not exist, abort
                raise PermissionError(f"Error: Integration requires existing file {rel_path}. Creation not permitted.")
            
            # Never create frontend files unless explicitly ordered
            # (Enforced by the existence check above, but adding explicit block for clarity if needed)
            if "frontend" in rel_path and not os.path.exists(full_path):
                raise PermissionError(f"Error: Integration requires existing file {rel_path}. Creation not permitted.")

    print(f"SUDO AUDIT PASSED: Operation on '{rel_path}' authorized.")
    
    # Log to memory
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import memory_bridge
        memory_bridge.quick_save('file_operations', {
            'project_name': 'NewBeginnings',
            'operation': f"Authorized operation on: {rel_path}"
        })
    except Exception:
        pass
