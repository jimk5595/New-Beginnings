import sqlite3

def initialize_memory():
    conn = sqlite3.connect('system_growth.db')
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('CREATE TABLE IF NOT EXISTS lessons_learned (mistake TEXT, fix TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS build_registry (project TEXT, status TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS family_profiles (detail TEXT)')
    
    # Log entries
    cursor.execute("INSERT INTO lessons_learned (mistake, fix) VALUES (?, ?)", 
                   ('Consultant Drift', 'Integration of direct file-system actions and the Working and Right directive.'))
    
    cursor.execute("INSERT INTO build_registry (project, status) VALUES (?, ?)", 
                   ('Core Infrastructure', 'Git linked, SQLite Memory active, and .gitignore implemented.'))
    
    cursor.execute("INSERT INTO family_profiles (detail) VALUES (?)", 
                   ('This system is designed for long-term growth with the family, focusing on memory persistence and evolving intelligence.',))
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    initialize_memory()