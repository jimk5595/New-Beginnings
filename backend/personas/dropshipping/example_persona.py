from personas.base_persona import Persona

class DropshippingExample(Persona):
    def __init__(self):
        super().__init__(
            name="dropshipping_example",
            description="Example persona for the dropshipping module.",
            system_prompt="You are a dropshipping assistant persona.",
            style=""
        )
