class TaskPlanner:
    def plan(self, task_text: str) -> list:
        """
        Produces a simple ordered execution plan from a task description.
        Each step contains an id, action label, and detail string.
        """
        steps = [
            {
                "id": 1,
                "action": "analyze",
                "detail": f"Analyze the following task and identify requirements: {task_text}"
            },
            {
                "id": 2,
                "action": "design",
                "detail": f"Design a solution approach for: {task_text}"
            },
            {
                "id": 3,
                "action": "execute",
                "detail": f"Execute and implement the solution for: {task_text}"
            },
        ]
        return steps
