import os
import json
import shutil
import logging
from pathlib import Path

logger = logging.getLogger("DeploymentManager")

class DeploymentManager:
    """Handles deployment, activation, rollback, and versioning of modules."""
    
    def __init__(self):
        # Robust fallback for project root detection
        try:
            from tools.project_map import ProjectMap
            self.project_root = Path(ProjectMap().root_dir)
        except:
            self.project_root = Path(__file__).resolve().parent.parent.parent
            
        self.modules_root = self.project_root / "backend" / "modules"
        self.backup_root = self.project_root / "backend" / "backups"
        self.backup_root.mkdir(parents=True, exist_ok=True)

    def activate_module(self, module_id: str) -> dict:
        """
        Activates a module after final executive authorization.
        Includes a safety backup for rollback.
        """
        module_path = self.modules_root / module_id
        if not module_path.exists():
             return {"success": False, "error": f"Module {module_id} not found."}

        # 1. Verification of approvals (Final check)
        marcus_approval = module_path / "marcus_approval.json"
        validation_report = module_path / "validation_report.json"
        eliza_auth = module_path / "eliza_authorization.json"

        if not marcus_approval.exists():
            return {"success": False, "error": "Missing Marcus's technical approval."}
        if not validation_report.exists():
            return {"success": False, "error": "Missing Mira's validation report."}
        
        with open(validation_report, "r") as f:
            report = json.load(f)
            if not report.get("checks_passed"):
                return {"success": False, "error": "Mira's validation failed."}
        
        if not eliza_auth.exists():
            return {"success": False, "error": "Missing Eliza's executive authorization."}

        # 2. Create Rollback Backup
        backup_path = self.backup_root / f"{module_id}_pre_activation"
        if backup_path.exists():
            shutil.rmtree(backup_path)
        shutil.copytree(module_path, backup_path)
        logger.info(f"DEPLOYMENT: Backup created at {backup_path}")

        # 3. Update Module Status in module.json
        module_json_path = module_path / "module.json"
        with open(module_json_path, "r") as f:
            data = json.load(f)
        
        data["status"] = "active"
        data["activated_at"] = "2026-02-01"
        
        with open(module_json_path, "w") as f:
            json.dump(data, f, indent=4)

        # 4. Final Activation Activation (Integration)
        # In a real system, this would trigger route mounting or similar
        logger.info(f"DEPLOYMENT: Module '{module_id}' is now ACTIVE and operational.")
        
        return {
            "success": True, 
            "module_id": module_id, 
            "status": "active",
            "backup": str(backup_path)
        }

    def rollback(self, module_id: str) -> dict:
        """Rolls back a module to its pre-activation state."""
        backup_path = self.backup_root / f"{module_id}_pre_activation"
        module_path = self.modules_root / module_id
        
        if not backup_path.exists():
            return {"success": False, "error": f"No backup found for module {module_id}."}

        if module_path.exists():
            shutil.rmtree(module_path)
        
        shutil.copytree(backup_path, module_path)
        logger.info(f"DEPLOYMENT: Rollback complete for module '{module_id}'.")
        
        return {"success": True, "module_id": module_id, "status": "rolled_back"}

# Global Instance
deployment_manager = DeploymentManager()
