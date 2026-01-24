class PersonaManager:
    def __init__(self):
        self._personas = {
            "professional": {
                "prefix": "Analytical Assessment: ",
                "suffix": ".",
                "transform": "none"
            },
            "friendly": {
                "prefix": "Hello! ",
                "suffix": " Have a great day!",
                "transform": "none"
            },
            "technical": {
                "prefix": "[CODE_GEN_ID_0]: ",
                "suffix": " [EOF]",
                "transform": "uppercase"
            },
            "minimal": {
                "prefix": "> ",
                "suffix": "",
                "transform": "lowercase"
            }
        }

    def load_persona(self, name):
        """
        Loads a persona definition by name. Defaults to professional.
        """
        return self._personas.get(name.lower(), self._personas["professional"])

    def apply_persona(self, persona, eliza_output):
        """
        Applies persona-specific styling to the Eliza response text.
        """
        text = eliza_output.get("response", "")
        
        transform = persona.get("transform", "none")
        if transform == "uppercase":
            text = text.upper()
        elif transform == "lowercase":
            text = text.lower()
            
        styled_text = f"{persona.get('prefix', '')}{text}{persona.get('suffix', '')}"
        
        modified_output = eliza_output.copy()
        modified_output["response"] = styled_text
        return modified_output
