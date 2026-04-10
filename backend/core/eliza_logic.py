class ElizaCore:
    def analyze_input(self, text):
        """
        Analyzes the input text using deterministic rule-based logic.
        """
        text = text.lower().strip()
        
        if "ready" in text:
            intent = "ready_check"
            reasoning = "Input contains the keyword READY."
            next_action = "respond_ready"
        elif any(greet in text for greet in ["hello", "hi", "hey"]):
            intent = "greeting"
            reasoning = "Input contains common greeting keywords."
            next_action = "respond_greeting"
        elif "?" in text:
            intent = "question"
            reasoning = "Input contains a question mark, indicating an inquiry."
            next_action = "respond_inquiry"
        elif "module" in text or "build" in text:
            if "delete" in text or "remove" in text or "destroy" in text:
                intent = "module_delete"
                reasoning = "Input mentions deleting or removing a module."
                next_action = "respond_module_delete"
            else:
                intent = "module_build"
                reasoning = "Input mentions building or creating a module."
                next_action = "respond_module_build"
        elif "scene" in text or "room" in text:
            intent = "scene_request"
            reasoning = "Input mentions scene or room creation."
            next_action = "create_scene"
        elif "summarize" in text or "summary" in text:
            intent = "summarization"
            reasoning = "Input asks for a summary."
            next_action = "respond_summary"
        elif "cube" in text or "object" in text:
            intent = "object_request"
            reasoning = "Input mentions adding an object or cube."
            next_action = "add_object"
        elif any(bye in text for bye in ["bye", "goodbye", "exit", "quit"]):
            intent = "farewell"
            reasoning = "Input contains termination or departure keywords."
            next_action = "respond_farewell"
        elif not text:
            intent = "empty"
            reasoning = "Input is empty or whitespace."
            next_action = "respond_silence"
        else:
            intent = "statement"
            reasoning = "Input does not match specific patterns; treated as a general statement."
            next_action = "respond_generic"

        return {
            "intent": intent,
            "reasoning": reasoning,
            "next_action": next_action
        }

    def respond(self, context):
        """
        Returns a structured response based on the detected intent and next action.
        Descriptions are derived from context — no static template strings.
        """
        next_action = context.get("next_action")
        intent = context.get("intent", "unknown")
        reasoning = context.get("reasoning", "")

        action_type_map = {
            "create_scene": "action",
            "add_object": "action",
            "respond_module_build": "delegation",
            "respond_module_delete": "delegation",
            "respond_summary": "info",
            "respond_ready": "status",
            "respond_greeting": "friendly",
            "respond_farewell": "closing",
            "respond_silence": "prompt",
            "respond_inquiry": "clarification",
            "respond_generic": "continuation",
        }

        response_type = action_type_map.get(next_action, "default")

        return {
            "status": "ok",
            "intent": intent,
            "next_action": next_action,
            "type": response_type,
            "reasoning": reasoning,
        }

    def generate_scene_request(self, eliza_output):
        """
        Generates a scene or object request based on Eliza's next action.
        """
        next_action = eliza_output.get("next_action")
        if next_action == "create_scene":
            return {"scene": "basic_room"}
        elif next_action == "add_object":
            return {"object": "cube"}
        return None
