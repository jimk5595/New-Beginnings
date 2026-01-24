import os
from pathlib import Path

def write_to_disk(path_str: str, content: str):
    """
    Safely creates directories and writes content to a file.
    """
    path = Path(path_str)
    # Create parent directories if they don't exist
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
