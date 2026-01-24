from personas.factory import create_persona

class PersonaService:
    @staticmethod
    def instantiate(persona_name: str):
        return create_persona(persona_name)
