import psycopg2
from psycopg2.extras import RealDictCursor
import os
import sys
from datetime import datetime, timezone
import threading
from contextlib import contextmanager
from pathlib import Path

# Ensure we can find the config
sys.path.append(str(Path(__file__).parent.parent))
try:
    from config import settings
except ImportError:
    # Fallback or error handling
    class MockSettings:
        DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:July242010!@localhost:5432/NewBeginnings")
    settings = MockSettings()

class MemoryEngine:
    """
    Thread-safe PostgreSQL Memory Engine for AI Persona persistence.
    Manages its own connection context and handles original schema logic.
    """
    _initialized = False

    def __init__(self):
        self.db_url = settings.DATABASE_URL
        self._lock = threading.Lock()
        if not MemoryEngine._initialized:
            self._init_db()
            MemoryEngine._initialized = True

    def _init_db(self):
        """
        Initializes the database schema if it doesn't exist.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Table 1: lessons_learned
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS lessons_learned (
                    id SERIAL PRIMARY KEY,
                    module_name TEXT,
                    mistake_description TEXT NOT NULL,
                    fix_applied TEXT,
                    status TEXT,
                    timestamp TIMESTAMPTZ NOT NULL
                )
            ''')

            # Table 1.5: build_success_stories
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS build_success_stories (
                    id SERIAL PRIMARY KEY,
                    module_name TEXT,
                    feature_description TEXT NOT NULL,
                    why_it_worked TEXT,
                    timestamp TIMESTAMPTZ NOT NULL
                )
            ''')
            
            # Table 2: family_profiles
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS family_profiles (
                    id SERIAL PRIMARY KEY,
                    relation TEXT NOT NULL UNIQUE,
                    detail TEXT NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL
                )
            ''')
            
            # Table 3: build_registry
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS build_registry (
                    id SERIAL PRIMARY KEY,
                    project_name TEXT NOT NULL,
                    file_structure_map TEXT NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL
                )
            ''')
            
            # Table 4: system_state
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL
                )
            ''')

            # Table 6: cross_department_memory (Shared insights between departments)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cross_department_memory (
                    id SERIAL PRIMARY KEY,
                    source_department TEXT NOT NULL,
                    target_department TEXT,
                    insight_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB,
                    timestamp TIMESTAMPTZ NOT NULL
                )
            ''')

            # Table 7: user_profiles — rich personal profiles per person
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id SERIAL PRIMARY KEY,
                    user_name TEXT NOT NULL UNIQUE,
                    relation TEXT,
                    bio TEXT,
                    personality TEXT,
                    preferences TEXT,
                    life_context TEXT,
                    updated_at TIMESTAMPTZ NOT NULL
                )
            ''')

            # Table 8: platform_vision — Jim's documented vision for the platform
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS platform_vision (
                    id SERIAL PRIMARY KEY,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL,
                    UNIQUE(category)
                )
            ''')

            # Table 9: memory_facts — atomic extracted facts per person from conversations
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memory_facts (
                    id SERIAL PRIMARY KEY,
                    user_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    fact TEXT NOT NULL,
                    source_session TEXT,
                    timestamp TIMESTAMPTZ NOT NULL
                )
            ''')

            # Table 10: long_term_summaries — persisted conversation summaries per user
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS long_term_summaries (
                    id SERIAL PRIMARY KEY,
                    user_name TEXT NOT NULL,
                    session_id TEXT,
                    summary TEXT NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL
                )
            ''')

            conn.commit()

    @contextmanager
    def get_connection(self):
        """
        Context manager for thread-safe PostgreSQL connections.
        Ensures connections are closed properly.
        """
        with self._lock:
            conn = psycopg2.connect(self.db_url)
            try:
                yield conn
            finally:
                conn.close()

    def log_experience(self, category: str, content: dict):
        """
        Sanitizes input and stores it with a UTC timestamp.
        Categories: 'lessons_learned', 'build_success_stories', 'family_profiles', 'build_registry', 'system_state'
        """
        timestamp = datetime.now(timezone.utc)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if category == 'lessons_learned':
                cursor.execute(
                    "INSERT INTO lessons_learned (module_name, mistake_description, fix_applied, status, timestamp) VALUES (%s, %s, %s, %s, %s)",
                    (content.get('module_name', ''), content.get('mistake', ''), content.get('fix', ''), content.get('status', ''), timestamp)
                )
            elif category == 'build_success_stories':
                cursor.execute(
                    "INSERT INTO build_success_stories (module_name, feature_description, why_it_worked, timestamp) VALUES (%s, %s, %s, %s)",
                    (content.get('module_name', ''), content.get('feature', ''), content.get('why', ''), timestamp)
                )
            elif category == 'family_profiles':
                # Intent-trigger: If identity details are passed, write to family_profiles
                cursor.execute(
                    "INSERT INTO family_profiles (relation, detail, timestamp) VALUES (%s, %s, %s) ON CONFLICT (relation) DO UPDATE SET detail = EXCLUDED.detail, timestamp = EXCLUDED.timestamp",
                    (content.get('relation', ''), content.get('detail', ''), timestamp)
                )
            elif category == 'build_registry':
                cursor.execute(
                    "INSERT INTO build_registry (project_name, file_structure_map, timestamp) VALUES (%s, %s, %s)",
                    (content.get('project_name', ''), content.get('map', ''), timestamp)
                )
            elif category == 'system_state':
                cursor.execute(
                    "INSERT INTO system_state (key, value, timestamp) VALUES (%s, %s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, timestamp = EXCLUDED.timestamp",
                    (content.get('key', ''), content.get('value', ''), timestamp)
                )
            conn.commit()

    def retrieve_context(self, category: str, limit: int = 5):
        """
        Returns a list of the most recent entries for the specified category.
        """
        valid_tables = ['lessons_learned', 'build_success_stories', 'family_profiles', 'build_registry', 'system_state']
        if category not in valid_tables:
            return []

        with self.get_connection() as conn:
            # Use RealDictCursor for row-as-dict behavior
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Note: Table names cannot be parameterized normally, 
            # but since we validate against 'valid_tables', this is safe.
            query = f"SELECT * FROM {category} ORDER BY timestamp DESC LIMIT %s"
            cursor.execute(query, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]

    def set_state(self, key: str, value: str):
        """
        Sets or updates a system state key-value pair.
        """
        self.log_experience('system_state', {'key': key, 'value': value})

    def get_state(self, key: str) -> str:
        """
        Retrieves a system state value by key.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_state WHERE key = %s", (key,))
            result = cursor.fetchone()
            return result[0] if result else None

    def delete_state(self, key: str):
        """
        Deletes a system state entry by key.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM system_state WHERE key = %s", (key,))
            conn.commit()

    def list_state(self) -> dict:
        """
        Lists all system state key-value pairs.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM system_state")
            return {row[0]: row[1] for row in cursor.fetchall()}

    def log_persona_activity(self, name: str, role: str, category: str, module: str, description: str):
        """
        Logs persona involvement in a task.
        """
        timestamp = datetime.now(timezone.utc)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO persona_activity (persona_name, persona_role, task_category, module_name, task_description, timestamp) VALUES (%s, %s, %s, %s, %s, %s)",
                (name, role, category, module, description, timestamp)
            )
            conn.commit()

    def share_insight(self, source: str, target: str, insight_type: str, content: str, metadata: dict = None):
        """
        Shares an insight from one department to another.
        """
        timestamp = datetime.now(timezone.utc)
        import json
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO cross_department_memory (source_department, target_department, insight_type, content, metadata, timestamp) VALUES (%s, %s, %s, %s, %s, %s)",
                (source, target, insight_type, content, json.dumps(metadata) if metadata else None, timestamp)
            )
            conn.commit()

    def get_insights(self, target_department: str = None, limit: int = 10):
        """
        Retrieves insights shared with a specific department (or all).
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            if target_department:
                cursor.execute(
                    "SELECT * FROM cross_department_memory WHERE target_department = %s OR target_department IS NULL ORDER BY timestamp DESC LIMIT %s",
                    (target_department, limit)
                )
            else:
                cursor.execute("SELECT * FROM cross_department_memory ORDER BY timestamp DESC LIMIT %s", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_persona_activity(self, name: str, limit: int = 10):
        """
        Retrieves activity logs for a specific persona.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                "SELECT * FROM persona_activity WHERE persona_name = %s ORDER BY timestamp DESC LIMIT %s",
                (name, limit)
            )
            return [dict(row) for row in cursor.fetchall()]

    def search_context(self, query: str, limit: int = 3) -> str:
        """
        Active Retrieval from all relevant tables including identity tables.
        """
        words = [w.lower() for w in query.split() if len(w) > 3]
        if not words:
            return ""
            
        search_pattern = "%" + "%".join(words[:5]) + "%"
        
        context = "\n### TIER 2: RELEVANT VECTOR RETRIEVAL (LOCAL) ###\n"
        found = False
        
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Search lessons_learned
            cursor.execute(
                "SELECT * FROM lessons_learned WHERE mistake_description ILIKE %s OR fix_applied ILIKE %s ORDER BY timestamp DESC LIMIT %s",
                (search_pattern, search_pattern, limit)
            )
            for l in cursor.fetchall():
                context += f"- [LESSON]: {l['mistake_description']} -> {l['fix_applied']}\n"
                found = True
                
            # Search build_success_stories
            cursor.execute(
                "SELECT * FROM build_success_stories WHERE feature_description ILIKE %s OR why_it_worked ILIKE %s ORDER BY timestamp DESC LIMIT %s",
                (search_pattern, search_pattern, limit)
            )
            for s in cursor.fetchall():
                context += f"- [SUCCESS]: {s['feature_description']} -> {s['why_it_worked']}\n"
                found = True
            
            # Search family_profiles (Identity)
            cursor.execute(
                "SELECT * FROM family_profiles WHERE relation ILIKE %s OR detail ILIKE %s ORDER BY timestamp DESC LIMIT %s",
                (search_pattern, search_pattern, limit)
            )
            for p in cursor.fetchall():
                context += f"- [IDENTITY]: {p['relation']} -> {p['detail']}\n"
                found = True
                
            # Search system_state (Identity/Persistence)
            cursor.execute(
                "SELECT * FROM system_state WHERE key ILIKE %s OR value ILIKE %s ORDER BY timestamp DESC LIMIT %s",
                (search_pattern, search_pattern, limit)
            )
            for s in cursor.fetchall():
                context += f"- [STATE]: {s['key']} -> {s['value']}\n"
                found = True
        
        if not found:
            return ""
            
        return context + "#################################################\n\n"

    def upsert_user_profile(self, user_name: str, relation: str = None, bio: str = None,
                            personality: str = None, preferences: str = None, life_context: str = None):
        """Creates or updates a personal profile for a user."""
        timestamp = datetime.now(timezone.utc)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_profiles (user_name, relation, bio, personality, preferences, life_context, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_name) DO UPDATE SET
                    relation = COALESCE(EXCLUDED.relation, user_profiles.relation),
                    bio = COALESCE(EXCLUDED.bio, user_profiles.bio),
                    personality = COALESCE(EXCLUDED.personality, user_profiles.personality),
                    preferences = COALESCE(EXCLUDED.preferences, user_profiles.preferences),
                    life_context = COALESCE(EXCLUDED.life_context, user_profiles.life_context),
                    updated_at = EXCLUDED.updated_at
            ''', (user_name, relation, bio, personality, preferences, life_context, timestamp))
            conn.commit()

    def get_user_profile(self, user_name: str) -> dict:
        """Returns the full personal profile for a user."""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM user_profiles WHERE LOWER(user_name) = LOWER(%s)", (user_name,))
            row = cursor.fetchone()
            return dict(row) if row else {}

    def set_platform_vision(self, category: str, content: str):
        """Stores or updates a platform vision entry by category."""
        timestamp = datetime.now(timezone.utc)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO platform_vision (category, content, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (category) DO UPDATE SET content = EXCLUDED.content, updated_at = EXCLUDED.updated_at
            ''', (category, content, timestamp))
            conn.commit()

    def get_platform_vision(self) -> list:
        """Returns all platform vision entries ordered by category."""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM platform_vision ORDER BY category")
            return [dict(r) for r in cursor.fetchall()]

    def add_memory_fact(self, user_name: str, category: str, fact: str, session_id: str = None):
        """Stores an extracted fact about a person from a conversation."""
        timestamp = datetime.now(timezone.utc)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO memory_facts (user_name, category, fact, source_session, timestamp) VALUES (%s, %s, %s, %s, %s)",
                (user_name, category, fact, session_id, timestamp)
            )
            conn.commit()

    def get_memory_facts(self, user_name: str, limit: int = 30) -> list:
        """Returns recent extracted facts for a specific user."""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                "SELECT * FROM memory_facts WHERE LOWER(user_name) = LOWER(%s) ORDER BY timestamp DESC LIMIT %s",
                (user_name, limit)
            )
            return [dict(r) for r in cursor.fetchall()]

    def save_long_term_summary(self, user_name: str, summary: str, session_id: str = None):
        """Persists a conversation summary to the DB for long-term recall."""
        timestamp = datetime.now(timezone.utc)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO long_term_summaries (user_name, session_id, summary, timestamp) VALUES (%s, %s, %s, %s)",
                (user_name, session_id, summary, timestamp)
            )
            conn.commit()

    def get_long_term_summaries(self, user_name: str, limit: int = 5) -> list:
        """Returns the most recent persisted conversation summaries for a user."""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                "SELECT * FROM long_term_summaries WHERE LOWER(user_name) = LOWER(%s) ORDER BY timestamp DESC LIMIT %s",
                (user_name, limit)
            )
            return [dict(r) for r in cursor.fetchall()]

    def get_full_person_context(self, user_name: str) -> str:
        """
        Builds a complete memory context string for a person to inject into system instructions.
        Includes their profile, extracted facts, and recent conversation summaries.
        """
        parts = []

        profile = self.get_user_profile(user_name)
        if profile:
            parts.append(f"=== WHO YOU ARE TALKING TO: {profile['user_name']} ===")
            if profile.get('relation'):
                parts.append(f"Relation: {profile['relation']}")
            if profile.get('bio'):
                parts.append(f"Bio: {profile['bio']}")
            if profile.get('personality'):
                parts.append(f"Personality: {profile['personality']}")
            if profile.get('preferences'):
                parts.append(f"Preferences: {profile['preferences']}")
            if profile.get('life_context'):
                parts.append(f"Life Context: {profile['life_context']}")

        facts = self.get_memory_facts(user_name, limit=25)
        if facts:
            parts.append(f"\n--- Things you remember about {user_name} ---")
            by_category: dict = {}
            for f in facts:
                by_category.setdefault(f['category'], []).append(f['fact'])
            for cat, fact_list in by_category.items():
                parts.append(f"[{cat.upper()}]")
                for fact in fact_list[:5]:
                    parts.append(f"  • {fact}")

        summaries = self.get_long_term_summaries(user_name, limit=3)
        if summaries:
            parts.append(f"\n--- Recent conversations with {user_name} ---")
            for s in summaries:
                ts = s['timestamp'].strftime('%b %d') if s.get('timestamp') else ''
                parts.append(f"[{ts}]: {s['summary']}")

        return "\n".join(parts) if parts else ""

    def get_learning_context(self, limit: int = 5) -> str:
        """
        Builds a formatted string of recent lessons and successes for LLM injection.
        """
        lessons = self.retrieve_context("lessons_learned", limit=limit)
        successes = self.retrieve_context("build_success_stories", limit=limit)
        
        context = "\n### SYSTEM RECURSIVE MEMORY & LESSONS LEARNED ###\n"
        
        if lessons:
            context += "CRITICAL: AVOID THESE PAST MISTAKES:\n"
            for l in lessons:
                m_name = l.get('module_name') or 'unknown'
                m_desc = l.get('mistake_description') or 'No description'
                m_fix = l.get('fix_applied') or 'No fix'
                context += f"- [{m_name}]: {m_desc} -> FIXED BY: {m_fix}\n"
        
        if successes:
            context += "\nSUCCESSFUL PATTERNS TO REPLICATE:\n"
            for s in successes:
                s_name = s.get('module_name') or 'unknown'
                s_feat = s.get('feature_description') or 'No feature'
                s_why = s.get('why_it_worked') or 'No explanation'
                context += f"- [{s_name}]: {s_feat} -> WHY IT WORKED: {s_why}\n"
        
        if not lessons and not successes:
            context += "No historical build data available yet. Establish high-fidelity patterns now.\n"
            
        return context + "\n"