import os

class Config:
    def __init__(self):
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        # Explicit Gemini 3.0 models — no auto-routing
        self.GEMINI_MODEL_FLASH = "gemini-3.0-flash"
        self.GEMINI_MODEL_PRO = "gemini-3.0-pro"
        # Default model your system uses unless overridden
        self.DEFAULT_MODEL = self.GEMINI_MODEL_PRO
