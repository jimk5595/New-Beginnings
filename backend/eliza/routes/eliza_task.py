from flask import Blueprint, request, jsonify
from task_planner import TaskPlanner
from task_orchestrator import TaskOrchestrator

eliza_task_bp = Blueprint('eliza_task', __name__)

@eliza_task_bp.route('/task', methods=['POST'])
def handle_task():
    """
    Route handler for the Eliza task planning and orchestration system.
    Expects JSON: { "task_text": string } OR { "task": string }
    """
    data = request.get_json()
    
    task_content = data.get('task') or data.get('task_text')
    
    if not task_content:
        return jsonify({
            "status": "error",
            "message": "Required field 'task' is missing"
        }), 400
    
    task_text = task_content
    
    # Initialize components
    planner = TaskPlanner()
    orchestrator = TaskOrchestrator()
    
    try:
        # Generate the plan
        plan = planner.plan(task_text)
        
        # Execute the plan and get Eliza analysis
        execution_result = orchestrator.execute(plan, task_text)
        
        return jsonify({
            "status": "ok",
            "result": execution_result
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
