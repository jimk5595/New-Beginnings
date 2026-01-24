import os

class Settings:
    ZENCODER_API_KEY = os.getenv("ZENCODER_API_KEY", "")
    ENV = os.getenv("ENV", "development")

settings = Settings()
