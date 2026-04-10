# build_gate.py
# Authoritative Hard Gate for module construction.
# This layer validates structured JSON blobs from personas BEFORE writing to disk.

import os
import ast
import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple
from persona_logger import narrate

logger = logging.getLogger("BuildGate")

class BuildGate:
    REQUIRED_FILES = [
        "module.json", "app.py", "index.html", "index.tsx", "styles.css", ".env"
    ]

    def __init__(self, project_root: str = None):
        if project_root is None:
            # Robust fallback for project root detection
            try:
                from core.config import Config
                cfg = Config()
                self.project_root = Path(cfg.PROJECT_ROOT)
            except Exception as e:
                # Resolve root from this file's location: backend/schemas/build_gate.py -> root is 2 levels up
                self.project_root = Path(__file__).resolve().parent.parent.parent
        else:
            self.project_root = Path(project_root)

    def validate_blob(self, module_name: str, blob: Dict[str, str], task_prompt: str = None) -> Tuple[bool, List[str]]:
        """
        Pure function validation of the module blob.
        Returns (is_valid, error_list).
        """
        errors = []

        # 1. Check for missing core files
        for filename in self.REQUIRED_FILES:
            if filename not in blob:
                errors.append(f"MISSING_FILE: '{filename}'")
        
        if errors: return False, errors

        # 2. Check for empty contents
        for filename, content in blob.items():
            if not content or len(content.strip()) < 10:
                errors.append(f"EMPTY_FILE: '{filename}'")

        # 3. Skeleton Check (must stay in sync with tools/repair.py MOCK_PATTERNS)
        skeleton_patterns = [
            r'TODO:',
            r'FIXME:',
            r'//\s*implementation\s*here',
            r'\[Interactive\s*Map\s*Here\]',
            r'#\s*add\s*logic\s*here',
            r'implementation pending',
            r'\bmock_',
            r'example\.com',
            r'//\s*Placeholder',
            r'#\s*Placeholder',
            r'<div[^>]*>\s*Placeholder\s*</div>',
            r'data\s*=\s*\[\]\s*#\s*Replace\s*with\s*API',
            r'fetch\(["\']https?://example\.com',
            r'console\.log\(["\']Implement\s*fetch',
        ]
        for filename, content in blob.items():
            for pattern in skeleton_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    errors.append(f"SKELETON: '{filename}' matched pattern `{pattern}` near: '{match.group()}'")
                    break

        # 4. Backend Contract Check (app.py)
        app_py = blob.get("app.py", "")
        if "def register():" not in app_py:
            errors.append("CONTRACT_ERROR: app.py missing 'def register():'")
        if "router = APIRouter()" not in app_py:
            errors.append("CONTRACT_ERROR: app.py missing 'router = APIRouter()'")
        if "import os" not in app_py:
            errors.append("CONTRACT_ERROR: app.py missing 'import os' — os.getenv() will throw NameError")
        if "import * as Lucide" in blob.get("index.tsx", ""):
            errors.append("CONTRACT_ERROR: index.tsx uses forbidden 'import * as Lucide' namespace import — individual icon imports required")
        if "127.0.0.1:8001" in app_py or "localhost:8001" in app_py:
            errors.append("CONTRACT_ERROR: app.py calls local AI port 8001 which is not guaranteed to run — use /api/chat/chat instead")
        index_html = blob.get("index.html", "")
        if "/index.html" not in index_html:
            errors.append("CONTRACT_ERROR: index.html missing return-to-dashboard link (href='/index.html') — every module MUST have a visible link back to the main dashboard")
        tsx_content = blob.get("index.tsx", "")
        if "import('react-dom/client')" in tsx_content or "import('react-dom')" in tsx_content:
            errors.append("CONTRACT_ERROR: index.tsx uses forbidden dynamic ReactDOM import — MUST use static `import ReactDOM from 'react-dom/client'` as the last lines. Dynamic import causes build pipeline race conditions.")
        try:
            ast.parse(app_py)
        except SyntaxError as _se:
            _bad_line = (_se.text or "").strip()
            errors.append(f"SYNTAX_ERROR: app.py has invalid Python syntax at line {_se.lineno}: {_se.msg} — '{_bad_line}'")

        # Tile proxy check: if frontend uses /api/.../tile/ URLs, backend MUST define the route.
        import re as _re_proxy
        if _re_proxy.search(r'/api/[^"\']+/tile/', tsx_content):
            if "@router.get('/tile/" not in blob.get("app.py", "") and '@router.get("/tile/' not in blob.get("app.py", ""):
                errors.append("CONTRACT_ERROR: index.tsx uses a backend tile proxy URL (/api/.../tile/...) but app.py has no @router.get('/tile/...') route. Every tile proxy URL MUST have a corresponding backend route that fetches tiles with the API key from os.getenv.")
        
        _hex32 = _re_proxy.compile(r'[a-f0-9]{32}', _re_proxy.IGNORECASE)
        if _hex32.search(tsx_content):
            errors.append("CONTRACT_ERROR: index.tsx contains a hardcoded 32-char hex API key — NEVER embed API keys in frontend code. Use a backend proxy route for tile URLs and inject keys via os.getenv on the server side.")

        # TSX brace balance check — catches truncated domain components that esbuild would fail with
        # "Unexpected const/function/let/var" because the previous component's closing brace is missing.
        _tsx_opens = tsx_content.count('{')
        _tsx_closes = tsx_content.count('}')
        _tsx_net = _tsx_opens - _tsx_closes
        if _tsx_net > 10:
            errors.append(
                f"SYNTAX_ERROR: index.tsx has severely unbalanced braces: {_tsx_opens} open vs {_tsx_closes} close "
                f"(net={_tsx_net}). This means at least one domain component is missing its closing `}};` — "
                f"esbuild will fail with 'Unexpected const/function'. Regenerate the affected component."
            )

        # Duplicate shell element checks — these create double-rendered overlapping UI elements.
        # The HTML shell provides the dashboard link; build.py injects the chat bubble.
        # If the React component ALSO renders these, they visually stack on top of each other.
        _dashboard_in_tsx = _re_proxy.search(
            r'''(?:href\s*=\s*['"][^'"]*index\.html['"]|←\s*(?:Dashboard|Return)|Return\s+to\s+Dashboard)''',
            tsx_content
        )
        if _dashboard_in_tsx:
            errors.append(
                "CONTRACT_ERROR: index.tsx contains a return-to-dashboard link or text (← Dashboard / Return to Dashboard / href='index.html'). "
                "The HTML shell (index.html) already provides this fixed-position link. Remove it from the React component to prevent a double-button overlap."
            )
        _chat_bubble_in_tsx = _re_proxy.search(
            r'''(?:ChatBubble|chat[-_]toggle|chat[-_]bubble|fixed\s+bottom-\d+\s+right-\d+[^"\'<]{0,120}(?:MessageSquare|chat|bubble|message))''',
            tsx_content,
            _re_proxy.IGNORECASE
        )
        if _chat_bubble_in_tsx:
            errors.append(
                "CONTRACT_ERROR: index.tsx contains a floating chat bubble or MessageSquare toggle button. "
                "The build system injects the module chat automatically. Remove the React chat component to prevent a duplicate overlapping bubble."
            )

        # HTTPException-in-except check — causes blank screens when external APIs fail.
        # Routes MUST return safe default dicts instead of propagating 500 errors to the frontend.
        _http_exc_in_except = _re_proxy.search(
            r'except\s+(?:Exception|httpx\.\w+|Exception\s+as\s+\w+)[^:]*:\s*\n\s*raise\s+HTTPException',
            app_py
        )
        if _http_exc_in_except:
            errors.append(
                "CONTRACT_ERROR: app.py raises HTTPException inside an except block that catches external API failures. "
                "This propagates HTTP 500 to the frontend which causes React components to crash (blank screens). "
                "Instead, catch the exception and return a safe default dict with the same shape as the success response."
            )

        # Skeleton view detection — a view component with no useEffect/useState is unimplemented.
        # Find const XxxView = () => { ... } blocks and check each one has at least one hook.
        _view_fn_re = _re_proxy.compile(
            r'const\s+([A-Z][a-zA-Z0-9]*View)\s*=\s*(?:\([^)]*\)\s*:\s*\{[^}]*\}\s*=>|\([^)]*\)\s*=>)\s*\{',
        )
        for _vm in _view_fn_re.finditer(tsx_content):
            _vname = _vm.group(1)
            _vstart = _vm.end()
            # Find the closing brace of this component (approximate by looking for next top-level const)
            _vnext = _re_proxy.search(r'\nconst\s+\w+', tsx_content[_vstart:])
            _vbody = tsx_content[_vstart: _vstart + (_vnext.start() if _vnext else 8000)]
            has_hooks = 'useEffect' in _vbody or 'useState' in _vbody
            # Also pass if the view delegates data fetching to a known wrapper (AIPanel, fetch(), etc.)
            # These components manage their own state internally so the parent doesn't need hooks.
            has_data_delegate = (
                'AIPanel' in _vbody or
                'fetch(' in _vbody or
                _re_proxy.search(r'<[A-Z][A-Za-z]+(?:Panel|Fetcher|Data|Chart|Map|View)\b', _vbody)
            )
            if not has_hooks and not has_data_delegate:
                errors.append(
                    f"SKELETON_VIEW: index.tsx component '{_vname}' has no useState, useEffect, fetch(), or data-fetching sub-component — "
                    f"it renders static content only with no data fetching. Every view MUST fetch and display real data."
                )

        # 5. Manifest Check (module.json)
        try:
            m_json = json.loads(blob.get("module.json", "{}"))
            required_keys = ["name", "entrypoint", "status", "ui_link"]
            for key in required_keys:
                if key not in m_json:
                    errors.append(f"MANIFEST_ERROR: module.json missing '{key}'")
        except:
            errors.append("MANIFEST_ERROR: module.json is invalid JSON")

        # 6. Content Density Check (Realistic limits for stable models)
        if len(blob.get("index.tsx", "")) < 5000:
            errors.append("DENSITY_ERROR: index.tsx is too short (min 5000 chars) — a full module requires complete component implementations for every view")
        if len(blob.get("app.py", "")) < 600:
            errors.append("DENSITY_ERROR: app.py is too short (min 600 chars)")

        # 7. Prompt Alignment Check (Critical for preventing mocks)
        if task_prompt:
            # Strip RAG/memory context — memory engine prepends lessons under a header ending
            # with "USER_PROMPT:" or "CURRENT_USER_INPUT:". Only check what the USER actually
            # wrote to avoid false positives from library names or API keys that appear in
            # past-build memory entries injected by the orchestrator.
            user_facing_prompt = task_prompt
            if "USER_PROMPT:" in task_prompt:
                user_facing_prompt = task_prompt.split("USER_PROMPT:", 1)[-1].strip()
            if "CURRENT_USER_INPUT:" in user_facing_prompt:
                user_facing_prompt = user_facing_prompt.split("CURRENT_USER_INPUT:", 1)[-1].strip()

            # Check for API Key usage - only if prompt contains explicit key assignment patterns
            # Avoids false positives from ordinary long words like "environmentalMonitoring"
            key_assignment_pattern = r'(?:[A-Z0-9_]{3,}_(?:KEY|TOKEN|SECRET|ID|API|URL)\s*[=:]|api[_\s]?key\s*[=:])'
            has_explicit_keys = bool(re.search(key_assignment_pattern, user_facing_prompt, re.IGNORECASE))
            
            actual_key_pattern = r'[A-Za-z0-9]{32,}'
            prompt_keys = re.findall(actual_key_pattern, user_facing_prompt) if has_explicit_keys else []

            # Check for URLs/Endpoints if they are in prompt
            url_pattern = r'https?://[^\s\)]+'
            prompt_urls = re.findall(url_pattern, user_facing_prompt)

            all_content = " ".join(blob.values())

            if prompt_keys:
                found_keys = [k for k in prompt_keys if k in all_content or k in blob.get('.env', '')]
                if not found_keys:
                    errors.append("FIDELITY_ERROR: Requested API keys from prompt were NOT found in the code.")

            if prompt_urls:
                # Filter to ONLY actual API endpoint URLs — not documentation/product pages.
                # Documentation URLs should NOT appear in generated code (they are reference material only).
                # API endpoint indicators: versioned paths, JSON/GeoJSON responses, known data service patterns.
                api_indicators = [
                    r'/v\d+/', r'/api/', r'api\.', r'\.json', r'\.geojson',
                    r'/feed/', r'/data/\d', r'/services/', r'/query',
                    r'\?.*appid=', r'\?.*api_key=', r'\?.*key=', r'\?.*token=',
                ]
                docs_indicators = [
                    r'/docs', r'/documentation', r'/help', r'/support',
                    r'/blog/', r'/news/', r'/about', r'/pricing',
                    r'/ourservices', r'/products-and-data',
                ]
                actual_api_urls = [
                    u for u in prompt_urls
                    if any(re.search(ind, u) for ind in api_indicators)
                    and not any(re.search(dp, u) for dp in docs_indicators)
                ]

                if actual_api_urls:
                    backend_content = blob.get("app.py", "") + " " + blob.get(".env", "")
                    # Strip query strings AND template variables (e.g. {lat}, {API key}) before matching.
                    # The AI stores base URLs in .env without template params, so we match on base URL only.
                    def _base_url(u):
                        # Remove template variables first, then strip query string and trailing slashes.
                        cleaned = re.sub(r'\{[^}]+\}', '', u.split('?')[0]).rstrip('/')
                        # Remove double-slashes introduced by template-variable removal (e.g. /v1//forecast)
                        return re.sub(r'(?<!:)//', '/', cleaned)
                    found_urls = [u for u in actual_api_urls if _base_url(u) in backend_content]
                    # Require at least half the API URLs to be present — catching total omissions
                    # while allowing the LLM some flexibility on secondary endpoints.
                    min_required = max(1, len(actual_api_urls) // 2)
                    if len(found_urls) < min_required:
                        errors.append(
                            f"FIDELITY_ERROR: Only {len(found_urls)}/{len(actual_api_urls)} requested API endpoints "
                            f"found in app.py or .env (minimum required: {min_required})."
                        )

            # 7. UI Operational Check
            _original_tsx = blob.get("index.tsx", "")
            index_tsx = _original_tsx.lower()
            _nav_var_patterns = [
                "activeview", "activetab", "activepage",
                "currentview", "currenttab", "currentpage",
                "selectedview", "selectedtab", "selectedpage",
                "activesection", "currentsection", "selectedsection",
                "activepanel", "currentpanel", "selectedpanel",
                "activescreen", "currentscreen", "selectedscreen",
            ]
            _nav_var_found = next((v for v in _nav_var_patterns if v in index_tsx), None)
            if _nav_var_found:
                _direct_view_values = set(re.findall(
                    rf'{re.escape(_nav_var_found)}\s*===?\s*["\']([^"\']+)["\']',
                    index_tsx
                ))
                _switch_cases = set(re.findall(r"case\s+['\"]([^'\"]+)['\"]", index_tsx))
                _map_access = bool(re.search(
                    rf'[a-z_]\w*\[{re.escape(_nav_var_found)}\]',
                    index_tsx
                ))
                _component_defs = set(re.findall(
                    r'(?:const|function)\s+([A-Z][a-zA-Z0-9]+)\s*(?:=\s*\(|[({])',
                    _original_tsx
                ))
                _any_equality_jsx = len(set(re.findall(
                    r'===?\s*["\']([^"\']+)["\']\s*&&',
                    index_tsx
                ))) >= 2
                has_multi_views = (
                    len(_direct_view_values) >= 2
                    or len(_switch_cases) >= 2
                    or _map_access
                    or len(_component_defs) >= 3
                    or _any_equality_jsx
                )
                if not has_multi_views:
                    errors.append("UI_ERROR: Tabs/Navigation logic detected but no distinct views found. Ensure multiple view components are implemented.")
            
            _uses_leaflet = "from 'leaflet'" in index_tsx or 'from "leaflet"' in index_tsx
            if _uses_leaflet:
                if "useref" not in index_tsx:
                    errors.append("UI_ERROR: Leaflet map detected but no useRef found for map initialization guard. This causes React re-render crashes.")
                _map_ref_assigned = bool(re.search(r'\w+\.current\s*=\s*(?:new\s+)?(?:l|L)\.(?:map|Map)\s*\(', index_tsx, re.IGNORECASE))
                if not _map_ref_assigned:
                    _has_ref_and_map = ('.current' in index_tsx and ('l.map(' in index_tsx or 'l.map (' in index_tsx))
                    if not _has_ref_and_map:
                        errors.append("UI_ERROR: Leaflet map detected but no ref is assigned via `.current = L.map(...)`. This causes React re-render crashes.")
                _lmap_ids = re.findall(r"""l\d*\.map\(['"]([a-z][\w-]*)['"]""", index_tsx, re.IGNORECASE)
                for _lid in _lmap_ids:
                    if f"getelementbyid('{_lid}')" not in index_tsx and f'getelementbyid("{_lid}")' not in index_tsx:
                        errors.append(f"UI_ERROR: Leaflet L.map('{_lid}') called without a document.getElementById guard. If the container div is hidden behind a loading state, this crashes the React tree.")
                        break

            if "<input" in index_tsx:
                if "onkeydown" not in index_tsx and "onkeypress" not in index_tsx:
                    # Only fail when there is an <input> tag whose own attributes indicate it is
                    # a search input (type="search", or a search/city/location/address/find
                    # placeholder).  Checking the whole file for "search" / "query" causes false
                    # positives when those words appear in API URLs, variable names, or comments.
                    _has_search_input = bool(re.search(
                        r'<input\b[^>]*(?:type=["\']search["\']|placeholder=["\'][^"\']{0,80}'
                        r'(?:search|city|location|address|find)[^"\']{0,80}["\'])',
                        index_tsx
                    ))
                    if _has_search_input:
                        errors.append("UI_ERROR: Search input detected but no onKeyDown/Enter key handler found.")

        return len(errors) == 0, errors

    def process_build(self, module_name: str, blob_json: str, task_prompt: str = None) -> Dict[str, Any]:
        """
        Orchestrates the validation and writing of a module.
        """
        try:
            blob = json.loads(blob_json)
        except Exception as e:
            return {"success": False, "error": "Invalid JSON blob", "details": str(e)}

        narrate("Dr. Mira Kessler", f"Validating structural integrity of '{module_name}'...")
        is_valid, errors = self.validate_blob(module_name, blob, task_prompt=task_prompt)
        if not is_valid:
            narrate("Dr. Mira Kessler", f"FAILED: {'; '.join(errors)}")
            # CLEANUP: Ensure no empty folder is left behind
            module_path = self.project_root / "backend" / "modules" / module_name
            if module_path.exists():
                import shutil
                narrate("Integrity Monitor", f"Cleaning up failed module directory: {module_name}")
                shutil.rmtree(module_path)
            return {"success": False, "error": "Validation failed", "details": "; ".join(errors)}

        narrate("Dr. Mira Kessler", "SUCCESS: Module passed basic validation.")
        
        # Write to disk
        module_path = self.project_root / "backend" / "modules" / module_name
        module_path.mkdir(parents=True, exist_ok=True)

        narrate("Integrity Monitor", f"Writing {len(blob)} files to {module_path}...")
        for filename, content in blob.items():
            file_path = module_path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            narrate("Integrity Monitor", f"  -> Writing {filename} ({len(content)} chars)...")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        narrate("Integrity Monitor", f"SUCCESS: Module '{module_name}' written to disk and verified.")
        return {"success": True, "module_path": str(module_path)}

build_gate = BuildGate()
