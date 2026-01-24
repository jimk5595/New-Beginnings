import os
import shutil
from pathlib import Path
from models import Plan, StepStatus, TaskType
from llm_router import call_gemini
from services.file_service import write_to_disk

def validate_code_syntax(content: str, filepath: str) -> bool:
    """
    Safety check: Ensures that code files contain actual code syntax.
    """
    ext = Path(filepath).suffix.lower()
    if ext == ".html":
        return "<" in content and ">" in content
    if ext == ".css":
        return "{" in content and "}" in content or ":" in content
    if ext in [".js", ".ts"]:
        return "(" in content and ")" in content or ";" in content or "{" in content
    return True

def execute_plan(plan: Plan, model: str) -> Plan:
    """
    Executes each step in the plan. 
    Recognizes FS_ task types for local file system operations.
    """
    # Base path for backend operations
    base_path = Path("C:/dev/NewBeginnings/backend")

    for step in plan.steps:
        try:
            step.status = StepStatus.RUNNING
            print(f"DEBUG: Executing [{step.type}] - {step.description[:50]}...")
            
            if step.type == TaskType.FS_CREATE_DIR:
                path = base_path / step.description if not os.path.isabs(step.description) else Path(step.description)
                path.mkdir(parents=True, exist_ok=True)
                step.result = f"Folder '{step.description}' created successfully."
                
            elif step.type == TaskType.FS_WRITE_FILE:
                if " | " in step.description:
                    filepath_str, content = step.description.split(" | ", 1)
                    
                    # Safety Check: Validate code syntax for web files
                    if not validate_code_syntax(content, filepath_str):
                        step.result = f"Error: Validation failed. Content for '{filepath_str}' does not appear to be valid code."
                        step.status = StepStatus.FAILED
                        continue

                    filepath = base_path / filepath_str if not os.path.isabs(filepath_str) else Path(filepath_str)
                    write_to_disk(str(filepath), content)
                    step.result = f"File '{filepath_str}' written successfully."
                else:
                    step.result = "Error: Invalid FS_WRITE_FILE format. Use 'path | content'."
                    step.status = StepStatus.FAILED
                    continue
                    
            elif step.type == TaskType.FS_READ_FILE:
                path = base_path / step.description if not os.path.isabs(step.description) else Path(step.description)
                if path.exists():
                    step.result = path.read_text(encoding="utf-8")
                else:
                    step.result = f"Error: File '{step.description}' not found."
                    step.status = StepStatus.FAILED
                    continue
                    
            elif step.type == TaskType.FS_DELETE:
                path = base_path / step.description if not os.path.isabs(step.description) else Path(step.description)
                if path.exists():
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                    step.result = f"Path '{step.description}' deleted successfully."
                else:
                    step.result = f"Error: Path '{step.description}' not found."
                    step.status = StepStatus.FAILED
                    continue
            
            elif step.type == TaskType.RESPONSE:
                step.result = step.description
                    
            else:
                # Default behavior: Call LLM for non-FS tasks
                result = call_gemini(model, step.description)
                step.result = result
            
            step.status = StepStatus.COMPLETE
            
        except Exception as e:
            print(f"DEBUG: Error in executor - {e}")
            step.result = str(e)
            step.status = StepStatus.FAILED
            
    return plan
