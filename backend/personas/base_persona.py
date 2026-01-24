class Persona:
    def __init__(self, name, description, system_prompt, style=""):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.style = style
    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "style": self.style
        }
