from models import Plan, Step, TaskType
from llm_router import call_gemini
import re

def generate_plan(prompt: str) -> Plan:
    """
    Uses LLM to naturally discern intent based on contextual specificity.
    Strictly separates technical actions from strategic responses.
    """
    planner_prompt = f"""
    You are a Technical Build Agent. Your goal is to identify required file system actions.

    INSTRUCTIONS:
    1. If the user request is specific (folders, files, code), return ONLY TaskType blocks.
    2. If the user request is abstract (strategy, how-to), return a [RESPONSE] block.
    3. NEVER wrap FS_ TaskTypes inside a [RESPONSE] block.
    4. If an action is identified, DO NOT provide introductory text or frameworks.
    
    OUTPUT FORMAT:
    [FS_CREATE_DIR] path
    [FS_WRITE_FILE] path | content
    [RESPONSE] text

    Task Types:
    - FS_CREATE_DIR: directory path
    - FS_WRITE_FILE: filepath | content
    - FS_READ_FILE: filepath
    - FS_DELETE: path
    - RESPONSE: conversational reply

    User Request: {prompt}
    """

    response = call_gemini("default", planner_prompt)
    
    steps = []
    step_id = 1
    
    # Split by any [TAG] but keep the tags
    parts = re.split(r'(\[(?:FS_CREATE_DIR|FS_WRITE_FILE|FS_READ_FILE|FS_DELETE|RESPONSE|EXECUTE)\])', response)
    
    for i in range(1, len(parts), 2):
        tag = parts[i].strip('[]')
        content = parts[i+1].strip() if i+1 < len(parts) else ""
        
        # If it's a response, we usually treat it as the only step or terminal
        if tag == "RESPONSE":
            steps.append(Step(id=step_id, type="RESPONSE", description=content))
        else:
            steps.append(Step(id=step_id, type=tag, description=content))
        step_id += 1
    
    # Fallback if no steps were parsed
    if not steps:
        steps = [Step(id=1, type=TaskType.RESPONSE, description=response.strip())]
        
    return Plan(steps=steps)
