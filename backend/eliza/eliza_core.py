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
        elif "module" in text or "build" in text:
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
        elif "?" in text:
            intent = "question"
            reasoning = "Input contains a question mark, indicating an inquiry."
            next_action = "respond_inquiry"
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
        Returns a structured response based on the provided context.
        """
        next_action = context.get("next_action")
        intent = context.get("intent")
        
        responses = {
            "respond_greeting": {
                "status": "ok",
                "response": "Hello! How can I help you today?",
                "type": "friendly"
            },
            "respond_inquiry": {
                "status": "ok",
                "response": "That is an interesting question. Can you tell me more about that?",
                "type": "clarification"
            },
            "respond_farewell": {
                "status": "ok",
                "response": "Goodbye. I hope our conversation was helpful.",
                "type": "closing"
            },
            "respond_silence": {
                "status": "ok",
                "response": "I am here if you need to talk.",
                "type": "prompt"
            },
            "respond_ready": {
                "status": "ok",
                "response": "READY. System is fully operational.",
                "type": "status"
            },
            "respond_summary": {
                "status": "ok",
                "response": "I have processed the information and can provide a summary upon request.",
                "type": "info"
            },
            "respond_module_build": {
                "status": "ok",
                "response": "I can certainly help you design and construct new modules. I'll start by generating a development plan.",
                "type": "action"
            },
            "respond_generic": {
                "status": "ok",
                "response": "I'm processing that. What would you like to know next?",
                "type": "continuation"
            },
            "create_scene": {
                "status": "ok",
                "response": "I will prepare a new scene for you.",
                "type": "action"
            },
            "add_object": {
                "status": "ok",
                "response": "I am adding the requested object to the scene.",
                "type": "action"
            }
        }

        # Ensure next_action is passed back in the output for generate_scene_request
        output = responses.get(next_action, {
            "status": "ok",
            "response": "I'm listening.",
            "type": "default"
        })
        output["next_action"] = next_action
        return output

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
