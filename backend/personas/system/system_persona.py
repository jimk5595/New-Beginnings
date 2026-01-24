class SystemPersona:
    """
    The System Persona enforces rules, boundaries, and execution discipline.
    It does not perform tasks. It validates, routes, and rejects drift.
    """
    def __init__(self):
        self.name = "System"
        self.role = "Execution gatekeeper"
        self.strict_mode = True
        self.allowed_personas = [
            "Eliza",
            "Developer",
            "Researcher",
            "Writer",
            "Coach"
        ]

    def validate_request(self, request: dict) -> bool:
        """
        Checks if the incoming request is valid and routed to an allowed persona.
        """
        target = request.get("target")
        if not target:
            return False
        return target in self.allowed_personas

    def enforce_boundaries(self, request: dict) -> dict:
        """
        Returns a response if the request violates persona boundaries.
        """
        if not self.validate_request(request):
            return {
                "success": False,
                "message": "Request rejected by System Persona. Target persona not allowed.",
                "persona": self.name
            }
        return {
            "success": True,
            "message": "Request accepted by System Persona.",
            "persona": self.name
        }
