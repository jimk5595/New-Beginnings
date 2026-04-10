import re

def fix_imports(match):
    stmt = match.group(0)
    print(f"DEBUG: Found stmt: {stmt}")
    import_path_match = re.search(r"from\s+['\"](\.\.?/[^'\"]+)['\"]", stmt)
    if import_path_match:
        path = import_path_match.group(1)
        print(f"DEBUG: Found path: {path}")
        if not path.endswith('.js') and not path.endswith('.css'):
            new_path = path + '.js'
            stmt = stmt.replace(path, new_path)
            print(f"DEBUG: New stmt: {stmt}")
    return stmt

content = "import { WeatherController } from './controller';"
content = re.sub(r'import\s+.*?from\s+[\'\"].*?[\'\"];', fix_imports, content)
print(f"RESULT: {content}")
