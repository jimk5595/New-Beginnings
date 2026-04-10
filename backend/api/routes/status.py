from fastapi import APIRouter
import time
from core.config import Config

# Original FastAPI code for system status tracking
status_router = APIRouter()
config = Config()

# Global start time to track uptime
start_time = time.time()

@status_router.get("/status")
async def get_system_status():
    """
    Returns the current system status with data expected by the dashboard.
    """
    uptime_seconds = int(time.time() - start_time)
    
    # Format uptime as HH:MM:SS
    hours, rem = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    uptime_str = f"{hours:02}:{minutes:02}:{seconds:02}"
    
    # Dynamic engine name from config
    engine_name = config.DEFAULT_MODEL
    if "flash-lite" in engine_name.lower():
        engine_display = "Gemini 3.1 Flash Lite"
    elif "flash" in engine_name.lower():
        engine_display = "Gemini 3.1 Flash"
    elif "3.1" in engine_name:
        engine_display = "Gemini 3.1 Pro"
    else:
        engine_display = engine_name

    return {
        "status": "ONLINE",
        "uptime": uptime_str,
        "version": "1.1.0",
        "engine": engine_display,
        "active_personas": ["Marcus Hale", "Alex Rivera", "Jordan Reyes"],
        "memory_engine_status": "healthy"
    }
