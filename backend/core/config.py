import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        # Ensure environment variables are loaded
        load_dotenv()
        
        # Dynamically determine project root
        current_file = os.path.abspath(__file__)
        # From backend/core/config.py to root
        self.PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        self.ENV = os.getenv("ENV", "development")
        self.DATABASE_URL = os.getenv("DATABASE_URL")
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        
        # Local model directories (models are in backend/models)
        self.MODEL_DIR = os.path.join(self.PROJECT_ROOT, "backend", "models")
        
        # Local Qwen models
        self.MODEL_QWEN_7B = os.path.join(self.MODEL_DIR, "Qwen 7b") 
        self.MODEL_QWEN_14B = os.path.join(self.MODEL_DIR, "Qwen 14b")
        
        # Specialist models
        self.MODEL_BGE_LARGE = os.path.join(self.MODEL_DIR, "BGE Large")
        self.MODEL_MOONDREAM2 = os.path.join(self.MODEL_DIR, "moondream2")
        self.MODEL_WHISPER = os.path.join(self.MODEL_DIR, "Whisper")
        
        # Explicit Gemini models
        self.GEMINI_MODEL_31_CUSTOMTOOLS = "gemini-3.1-pro-preview-customtools"
        self.GEMINI_MODEL_31_PRO = "gemini-3.1-pro-preview"
        self.GEMINI_MODEL_31_FLASH_LITE = "gemini-3.1-flash-lite-preview"
        self.GEMINI_MODEL_31_FLASH = "gemini-3.1-flash-preview"
        self.GEMINI_MODEL_30_FLASH = "gemini-3-flash-preview"
        self.GEMINI_MODEL_25_PRO = "gemini-2.5-pro"
        self.GEMINI_MODEL_25_FLASH = "gemini-2.5-flash"
        
        # Default model
        self.DEFAULT_MODEL = self.GEMINI_MODEL_31_FLASH_LITE
