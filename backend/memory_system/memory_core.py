import sqlite3
import os
from datetime import datetime, timezone
import threading
from contextlib import contextmanager
from pathlib import Path

class MemoryEngine:
    """
    Thread-safe SQLite Memory Engine for AI Persona persistence.
    Manages its own connection context and handles original schema logic.
    """
    def __init__(self, db_name="system_growth.db"):
        self.db_path = Path(__file__).parent.parent / "database" / db_name
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """
        Initializes the database schema if it doesn't exist.
        """
        # Safety check: ensure directory exists before any potential file operations
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Table 1: lessons_learned
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS lessons_learned (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mistake_description TEXT NOT NULL,
                    fix_applied TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            
            # Table 2: family_profiles
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS family_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    relation TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            
            # Table 3: build_registry
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS build_registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT NOT NULL,
                    file_structure_map TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            conn.commit()

    @contextmanager
    def get_connection(self):
        """
        Context manager for thread-safe SQLite connections.
        Ensures connections are closed properly.
        """
        with self._lock:
            # Safety Check: Verify file accessibility to prevent Permission Errors
            if self.db_path.exists():
                try:
                    # Attempt to open to check permissions
                    open(self.db_path, 'a').close()
                except OSError as e:
                    raise PermissionError(f"Database file access denied: {e}")

            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            try:
                yield conn
            finally:
                conn.close()

    def log_experience(self, category: str, content: dict):
        """
        Sanitizes input and stores it with a UTC timestamp.
        Categories: 'lessons_learned', 'family_profiles', 'build_registry'
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if category == 'lessons_learned':
                cursor.execute(
                    "INSERT INTO lessons_learned (mistake_description, fix_applied, timestamp) VALUES (?, ?, ?)",
                    (content.get('mistake', ''), content.get('fix', ''), timestamp)
                )
            elif category == 'family_profiles':
                cursor.execute(
                    "INSERT INTO family_profiles (relation, detail, timestamp) VALUES (?, ?, ?)",
                    (content.get('relation', ''), content.get('detail', ''), timestamp)
                )
            elif category == 'build_registry':
                cursor.execute(
                    "INSERT INTO build_registry (project_name, file_structure_map, timestamp) VALUES (?, ?, ?)",
                    (content.get('project_name', ''), content.get('map', ''), timestamp)
                )
            conn.commit()

    def retrieve_context(self, category: str, limit: int = 5):
        """
        Returns a list of the most recent entries for the specified category.
        """
        valid_tables = ['lessons_learned', 'family_profiles', 'build_registry']
        if category not in valid_tables:
            return []

        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Note: SQLite table names cannot be parameterized normally, 
            # but since we validate against 'valid_tables', this is safe.
            query = f"SELECT * FROM {category} ORDER BY timestamp DESC LIMIT ?"
            cursor.execute(query, (limit,))
            
            # Get column names for structured return
            columns = [column[0] for column in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            return results
