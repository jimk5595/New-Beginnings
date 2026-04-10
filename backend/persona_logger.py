import sys
import os
from datetime import datetime

# Ensure logs directory exists
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "persona_actions.log")

def narrate(persona_name: str, message: str):
    """
    Logs an activity attributed to a specific persona.
    Format: [Timestamp] [Persona Name]: Message
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{persona_name}]: {message}"
    
    # Print to stdout for live monitoring
    print(log_entry)
    sys.stdout.flush()
    
    # Write to log file for persistence
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    except Exception as e:
        print(f"FAILED TO WRITE TO PERSONA LOG: {e}")

def get_persona_for_task(task_type: str) -> str:
    """
    Maps task types or categories to personas if not explicitly provided.
    """
    mapping = {
        "DIRECT_BUILD": "Caleb Monroe",
        "DIRECT_REPAIR": "Alex Rivera",
        "validation": "Dr. Mira Kessler",
        "executive": "Eliza",
        "integration": "Integrity Monitor"
    }
    return mapping.get(task_type, "Eliza")
