from models import Plan, Step, StepStatus

def validate_plan(plan: Plan) -> bool:
    if not plan.steps:
        return False
    for step in plan.steps:
        if not isinstance(step, Step):
            return False
        if not isinstance(step.id, int):
            return False
        if not isinstance(step.type, str) or not step.type:
            return False
        if not isinstance(step.description, str) or not step.description:
            return False
        if step.status != StepStatus.PENDING:
            return False
    return True
