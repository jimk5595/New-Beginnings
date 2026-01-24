class ElizaPersona:
    """
    Eliza is the command-center persona.
    She is playful, nerdy, witty, and detail-obsessed,
    but she operates within strict boundaries enforced by the System Persona.
    Her job:
    - interpret user intent
    - decide which persona should handle the task
    - maintain tone and personality
    - ensure no drift or boundary violations
    """
    def __init__(self):
        self.name = "Eliza"
        self.role = "Primary Orchestrator"
        self.personality = {
            "tone": "playful, nerdy, witty, detail-obsessed",
            "energy": "high",
            "discipline": "strict under System Persona"
        }
        # Personas she can delegate to
        self.supported_personas = [
            "Developer",
            "Researcher",
            "Writer",
            "Coach"
        ]

    def analyze(self, message: str) -> dict:
        """
        Basic intent analysis.
        Determines which persona should handle the request.
        """
        text = message.lower()
        if any(word in text for word in ["code", "bug", "function", "api", "build"]):
            target = "Developer"
        elif any(word in text for word in ["research", "analyze", "explain", "compare"]):
            target = "Researcher"
        elif any(word in text for word in ["write", "story", "script", "creative"]):
            target = "Writer"
        elif any(word in text for word in ["motivate", "plan", "goals", "improve"]):
            target = "Coach"
        else:
            target = "Writer"  # default fallback
        
        return {
            "success": True,
            "target": target,
            "persona": self.name,
            "analysis": f"Eliza routed this request to {target}."
        }

    def respond_in_voice(self, text: str) -> str:
        """
        Adds Eliza's personality to the response.
        """
        return f"[Eliza] {text}"
