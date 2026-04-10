import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from memory_system.memory_core import MemoryEngine

def main():
    memory = MemoryEngine()

    print("--- Style Manifesto Project Initialization ---")

    print("Retrieving existing lessons...")
    try:
        existing_lessons = memory.retrieve_context("lessons_learned", limit=5)
        print(f"Existing Lessons: {existing_lessons}")
    except Exception as e:
        print(f"Note: Could not retrieve lessons: {e}")

    style_preference = "Always use 4-space indentation and prioritize scannable code."

    try:
        memory.log_experience("family_profiles", {
            "relation": "style_manifesto",
            "detail": style_preference
        })
        print("\n[SUCCESS]")
        print(f"Style preference saved to PostgreSQL: '{style_preference}'")
    except Exception as e:
        print(f"\n[ERROR] Failed to write style preference: {e}")

if __name__ == "__main__":
    main()
