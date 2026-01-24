class TaskPlanner:
    def plan(self, task_text):
        """
        Generates a deterministic plan for a given task text.
        Returns a list of 3 to 7 steps.
        """
        task_text = task_text.strip() or "General Task"
        task_lower = task_text.lower()
        
        # Determine step count based on input length (deterministic mapping 3-7)
        num_steps = max(3, min(7, (len(task_text) % 5) + 3))
        
        # Step templates
        templates = [
            {"action": "Analysis", "detail": "Analyze the requirements for '{task}'."},
            {"action": "Preparation", "detail": "Gather resources and set up the environment for '{task}'."},
            {"action": "Execution", "detail": "Perform the core operations required for '{task}'."},
            {"action": "Validation", "detail": "Verify that the output of '{task}' meets expectations."},
            {"action": "Optimization", "detail": "Refine the results of '{task}' for better performance."},
            {"action": "Documentation", "detail": "Record the findings and process for '{task}'."},
            {"action": "Finalization", "detail": "Complete the task and release the results of '{task}'."}
        ]

        # Context-specific adjustments
        if any(k in task_lower for k in ["fix", "bug", "error"]):
            templates[0] = {"action": "Diagnosis", "detail": "Identify the root cause of the error in '{task}'."}
            templates[2] = {"action": "Repair", "detail": "Implement the fix for the identified issue in '{task}'."}
        elif any(k in task_lower for k in ["build", "create", "new"]):
            templates[0] = {"action": "Design", "detail": "Create the architectural blueprint for '{task}'."}
            templates[2] = {"action": "Construction", "detail": "Build the foundational components for '{task}'."}

        # Generate the plan based on the calculated number of steps
        plan_steps = []
        for i in range(num_steps):
            step_data = templates[i]
            plan_steps.append({
                "id": i + 1,
                "action": step_data["action"],
                "detail": step_data["detail"].format(task=task_text)
            })

        return plan_steps
