class Persona:
    def __init__(self, name: str, description: str, system_prompt: str, style: str = ""):
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

    def __repr__(self):
        return f"Persona(name={self.name!r}, description={self.description!r})"