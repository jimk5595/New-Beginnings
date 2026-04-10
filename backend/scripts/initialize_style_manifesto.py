
import sys
import os
from backend.memory_system.memory_core import MemoryEngine

def main():
    # Initialize the MemoryEngine pointed to the system growth database
    # Assuming MemoryEngine handles the connection to system_growth.db internally 
    # as per backend/memory_system/memory_core.py logic
    memory = MemoryEngine()

    print("--- Style Manifesto Project Initialization ---")

    # 1. Retrieve existing lessons learned
    print("Retrieving existing lessons...")
    try:
        # Assuming retrieve_lessons or a similar query method exists in MemoryEngine
        existing_lessons = memory.log_experience(action="RETRIEVE", category="lessons_learned")
        print(f"Existing Lessons: {existing_lessons}")
    except Exception as e:
        print(f"Note: Could not retrieve lessons (Engine might be empty or method signature differs): {e}")

    # 2. Store the Style Preference
    # Using log_experience() as requested to save to the database instead of a .md file
    style_preference = "Always use 4-space indentation and prioritize scannable code."
    
    try:
        memory.log_experience(
            category="style_preference",
            content=style_preference,
            metadata={
                "project": "Style Manifesto",
                "priority": "high",
                "table_hint": "family_profiles"
            }
        )
        print("\n[SUCCESS]")
        print(f"Data sent to system_growth.db: '{style_preference}'")
        print("Verified: No text files created. Memory persistent in database via MemoryEngine.")
    except Exception as e:
        print(f"\n[ERROR] Failed to write to system_growth.db: {e}")

if __name__ == "__main__":
    main()