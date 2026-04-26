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

    def _run_validation_rules(self, app_py: str, tsx_raw: str, errors: list) -> None:
        """
        Load resources/validation_rules.json and apply each check generically.
        Module-specific route names, variable names, and trigger strings live
        in that JSON file — NOT in this core gate file.
        """
        _vr_path = Path(__file__).resolve().parent.parent / "resources" / "validation_rules.json"
        try:
            with open(_vr_path, "r", encoding="utf-8") as _vrf:
                _vr = json.load(_vrf)
        except Exception as _vre:
            logger.warning(f"[BuildGate] Could not load validation_rules.json: {_vre}")
            return

        _flag_map = {"IGNORECASE": re.IGNORECASE, "MULTILINE": re.MULTILINE, "DOTALL": re.DOTALL}

        for _c in _vr.get("checks", []):
            if _c.get("id", "").startswith("_"):
                continue
            _ctype = _c.get("check_type", "")
            _flags = 0
            for _fn in _c.get("flags", []):
                _flags |= _flag_map.get(_fn, 0)
            _cat = _c.get("error_category", "DATA_ERROR")
            _msg = _c.get("error_message", "")
            _fw = _c.get("fire_when", "guard_absent")

            if _ctype == "body_guard":
                _src = app_py if _c.get("target") == "app.py" else tsx_raw
                _anchor = _c.get("anchor", "")
                _idx = _src.find(_anchor)
                if _idx < 0:
                    continue
                _body = _src[_idx: _idx + _c.get("body_chars", 3000)]
                _gp = _c.get("guard_pattern")
                _fp = _c.get("fail_pattern")
                _guard_found = bool(re.search(_gp, _body, _flags)) if _gp else True
                _fail_found = bool(re.search(_fp, _body, _flags)) if _fp else False
                if _fw == "guard_absent_and_fail_present":
                    if not _guard_found and _fail_found:
                        errors.append(f"{_cat}: {_msg}")
                elif _fw == "guard_absent":
                    if not _guard_found:
                        errors.append(f"{_cat}: {_msg}")
                elif _fw == "guard_present":
                    if _guard_found:
                        errors.append(f"{_cat}: {_msg}")

            elif _ctype == "presence_guard":
                _src = app_py if _c.get("target") == "app.py" else tsx_raw
                if not any(t in _src for t in _c.get("trigger_any", [])):
                    continue
                _gp = _c.get("guard_pattern")
                _guard_found = bool(re.search(_gp, _src, _flags)) if _gp else True
                if not _guard_found:
                    errors.append(f"{_cat}: {_msg}")

            elif _ctype == "tsx_autoload":
                _route = _c.get("route_substr", "")
                if not _route or _route not in tsx_raw:
                    continue
                _autoload_pats = _c.get("autoload_patterns", [])
                _handler_pats = _c.get("handler_patterns", [])
                _autoloaded = any(
                    bool(re.search(p, tsx_raw, _flags)) for p in _autoload_pats
                )
                _only_in_handler = (
                    not _autoloaded
                    and any(bool(re.search(p, tsx_raw, _flags)) for p in _handler_pats)
                )
                if _only_in_handler:
                    errors.append(f"{_cat}: {_msg}")

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
        
        # Hardcoded API key check — flag 32-char hex keys in frontend code.
        # EXCEPTION: OWM map tile layer URLs (tile.openweathermap.org) MUST embed the key in the
        # client-side URL because tile requests go directly from the browser to OWM's CDN tile server.
        # There is no practical way to proxy tile requests without serving every tile through our own
        # server. Strip known tile URL patterns before checking so the auto-fix that injects the OWM
        # key into tileLayer() calls doesn't cause a false-positive rejection.
        _hex32 = _re_proxy.compile(r'[a-f0-9]{32}', _re_proxy.IGNORECASE)
        _tsx_no_tile_keys = _re_proxy.sub(
            r'https://tile\.openweathermap\.org/map/[^?]+\?appid=[a-f0-9]{32}',
            'https://tile.openweathermap.org/map/LAYER/TILE_URL?appid=TILE_KEY_EXEMPT',
            tsx_content,
            flags=_re_proxy.IGNORECASE
        )
        if _hex32.search(_tsx_no_tile_keys):
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
        elif _tsx_net < -5:
            errors.append(
                f"SYNTAX_ERROR: index.tsx has excess closing braces: {_tsx_opens} open vs {_tsx_closes} close "
                f"(net={_tsx_net}). At least one domain component has too many `}};` closers — "
                f"esbuild will fail with 'Unexpected }}'. Strip excess closing braces from the affected component."
            )
        if re.search(r'\};[ \t]*\};', tsx_content):
            errors.append(
                "SYNTAX_ERROR: index.tsx contains a same-line cascading close-brace sequence (e.g. `}};}};}};`). "
                "This is caused by a domain component auto-closing braces that were already closed. "
                "The assembled file will fail esbuild with 'Unexpected }}'."
            )

        # Truncated component detection — an LLM response cut off mid-JSX leaves dangling
        # operators/keywords immediately before the next const component declaration.
        # Pattern: a line ending with ?? / && / || / , / ( followed by }; on the next line(s)
        # then immediately a new component (const XxxView = ...).
        _truncation_boundary_re = re.compile(
            r'(?:[\?\:\,\(\[\+\-]|\?\?|&&|\|\||=>|return)\s*\n(?:\s*\};\s*\n)+\s*const\s+[A-Z]',
            re.MULTILINE
        )
        if _truncation_boundary_re.search(tsx_content):
            errors.append(
                "SYNTAX_ERROR: index.tsx contains a truncated domain component — a dangling operator "
                "(e.g. `??`, `&&`, `,`) appears immediately before a closing `}};` and the next component. "
                "The LLM response was cut off mid-expression. The truncated component must be regenerated."
            )

        _ul_in_block_comment = False
        _ul_in_template = False
        for _ul_num, _ul_line in enumerate(tsx_content.splitlines(), 1):
            _ul_in_single = False
            _ul_in_double = False
            _ul_lqcol = -1
            _ul_i = 0
            while _ul_i < len(_ul_line):
                _ul_ch = _ul_line[_ul_i]
                if _ul_in_block_comment:
                    if _ul_line[_ul_i:_ul_i + 2] == '*/':
                        _ul_in_block_comment = False
                        _ul_i += 2
                    else:
                        _ul_i += 1
                    continue
                if not (_ul_in_single or _ul_in_double or _ul_in_template):
                    if _ul_line[_ul_i:_ul_i + 2] == '//':
                        break
                    if _ul_line[_ul_i:_ul_i + 2] == '/*':
                        _ul_in_block_comment = True
                        _ul_i += 2
                        continue
                if _ul_ch == '\\' and (_ul_in_single or _ul_in_double):
                    _ul_i += 2
                    continue
                if _ul_ch == '`':
                    _ul_in_template = not _ul_in_template
                elif not _ul_in_template:
                    if _ul_ch == "'" and not _ul_in_double:
                        _ul_in_single = not _ul_in_single
                        if _ul_in_single:
                            _ul_lqcol = _ul_i
                    elif _ul_ch == '"' and not _ul_in_single:
                        _ul_in_double = not _ul_in_double
                _ul_i += 1
            if _ul_in_single or _ul_in_double:
                _ul_jsx_text_apos = False
                if _ul_in_single and _ul_lqcol >= 0:
                    for _jxt_i in range(_ul_lqcol - 1, -1, -1):
                        _jxt_ch = _ul_line[_jxt_i]
                        if _jxt_ch == '>':
                            _ul_jsx_text_apos = True
                            break
                        if _jxt_ch in ('{', '<', '(', '"', '='):
                            break
                if not _ul_jsx_text_apos:
                    errors.append(
                        f"SYNTAX_ERROR: index.tsx has an unterminated string literal at line {_ul_num}. "
                        f"esbuild will fail with 'Unterminated string literal'. Fix the broken string by closing it with the matching quote."
                    )
                    break

        _regex_open_lines = [
            i + 1 for i, ln in enumerate(tsx_content.splitlines())
            if re.search(r'\.\s*(?:replace|match|search|split|test|exec|filter)\s*\(\s*/[^/\n]*$', ln)
        ]
        if _regex_open_lines:
            errors.append(
                f"SYNTAX_ERROR: index.tsx has an unterminated regular expression literal at line {_regex_open_lines[0]}. "
                f"esbuild will fail with 'Unterminated regular expression'. The regex starting with '/' is not closed on the same line. "
                f"Join the split regex onto one line or close it properly."
            )

        _broken_named_import_re = re.compile(r'^import\s*\{[^}]*\bimport\b', re.MULTILINE)
        if _broken_named_import_re.search(tsx_content):
            errors.append(
                "SYNTAX_ERROR: index.tsx has a malformed import statement — the `import` keyword appears "
                "inside a named import list (e.g. `import { Foo, import * as L from '...'`). "
                "This is caused by incorrect import injection inside a multiline named-import block. "
                "esbuild will fail with 'Expected \"as\" but found \"*\"'. Fix the broken import line."
            )

        _escaped_jsx_tag_re = re.compile(r"\{['\"]<['\"]\}[A-Za-z]")
        if _escaped_jsx_tag_re.search(tsx_content):
            errors.append(
                "SYNTAX_ERROR: index.tsx contains an incorrectly escaped JSX tag opener — "
                "the pattern `{'<'}TagName` appears in a non-JSX-text context (e.g. inside render() or a function call). "
                "This is caused by _fix_jsx_bare_operators incorrectly escaping a JSX element opening tag. "
                "esbuild will fail with 'Expected \":\" but found \"}\"'. "
                "Replace `{'<'}TagName` with `<TagName`."
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

        # Map ref inside conditional render check — LLMs frequently wrap entire content sections
        # in `{data && (...)}` while also using `useEffect(..., [])` to init the map.
        # The empty-dep effect fires on mount when the div is still null (inside the hidden conditional),
        # and React never re-runs it — so the map NEVER initializes. The correct pattern is a callback ref.
        # Detect: `useEffect` with `L.map(` AND empty `[]` dep array AND a `useRef` for the same identifier.
        _map_useeffect_empty = _re_proxy.search(
            r'useEffect\s*\(\s*\(\s*\)\s*=>\s*\{[^}]*L\.map\s*\([^)]*\)[^}]*\}\s*,\s*\[\s*\]',
            tsx_content,
            _re_proxy.DOTALL
        )
        if _map_useeffect_empty:
            errors.append(
                "CONTRACT_ERROR: index.tsx initializes a Leaflet map inside useEffect(..., []) with empty deps. "
                "If the map container div is inside any conditional render branch ({data && ...}, {!loading && ...}), "
                "the map NEVER initializes because the empty-dep effect fires once on mount when the div is null, "
                "and React won't re-run it. Use the CALLBACK REF pattern instead: "
                "`const mapCallbackRef = React.useCallback((node) => { if (!node || mapInstanceRef.current) return; "
                "mapInstanceRef.current = L.map(node, { scrollWheelZoom: false }); ... }, []);` "
                "and attach it as `<div ref={mapCallbackRef} style={{height:'480px',width:'100%'}}></div>`. "
                "The callback ref fires whenever the DOM element mounts — immune to conditional rendering."
            )

        # CDN Leaflet pattern check — `declare var L: any;` is a TypeScript type stub only.
        # It provides no runtime Leaflet object, so L.map() crashes with "L is not defined".
        # The correct pattern is always `import * as L from 'leaflet'` (npm bundle).
        if _re_proxy.search(r'\bdeclare\s+var\s+L\s*:\s*any', tsx_content):
            errors.append(
                "CONTRACT_ERROR: index.tsx contains 'declare var L: any;' which is a TypeScript type declaration only "
                "— it provides no runtime Leaflet object. Use 'import * as L from \"leaflet\";' instead. "
                "'declare var L' causes 'L is not defined' runtime crashes because L never gets assigned a value."
            )
        if _re_proxy.search(r'\bwindow\.L\b', tsx_content) or _re_proxy.search(r'\(window\s+as\s+any\)\.L\b', tsx_content):
            errors.append(
                "CONTRACT_ERROR: index.tsx accesses Leaflet via 'window.L' or '(window as any).L'. "
                "Leaflet is bundled via npm and NOT available as a CDN window global. "
                "window.L is always undefined in bundled environments. Use 'import * as L from \"leaflet\";'."
            )

        # Non-ASCII characters inside JS string literals / SVG attribute values.
        # Gemini occasionally hallucinates Unicode (Bengali, Arabic, CJK, etc.) inside URLs or
        # JavaScript identifier contexts — this causes silent runtime failures (broken SVG, bad URLs).
        # We scan line-by-line and flag the first line that has non-ASCII outside of a comment.
        for _na_i, _na_ln in enumerate(tsx_content.splitlines(), 1):
            _na_stripped = _na_ln.strip()
            if _na_stripped.startswith("//") or _na_stripped.startswith("*"):
                continue
            try:
                _na_ln.encode("ascii")
            except UnicodeEncodeError:
                # Allow common safe Unicode: emoji in string literals are fine; only flag if
                # non-ASCII appears directly in what looks like a URL or attribute context.
                if re.search(r'[^\x00-\x7F]', _na_ln) and re.search(
                    r'(?:https?://|xmlns=|stroke|fill|viewBox|src=|href=|url\()', _na_ln
                ):
                    errors.append(
                        f"SYNTAX_ERROR: index.tsx line {_na_i} contains non-ASCII characters inside a URL or "
                        f"SVG attribute. This is a hallucinated character from the LLM that breaks the URL or "
                        f"SVG at runtime. Remove or replace the non-ASCII characters."
                    )
                    break

        # Duplicate route path check — FastAPI uses only the first matching route, silently ignoring the rest.
        # Duplicates typically come from multiple domain generators writing the same endpoint path.
        _route_paths = _re_proxy.findall(r'@router\.(?:get|post|put|delete)\(["\']([^"\']+)["\']', app_py)
        _seen_paths = {}
        for _rp in _route_paths:
            if _rp in _seen_paths:
                errors.append(
                    f"CONTRACT_ERROR: app.py defines duplicate route path '{_rp}'. "
                    f"FastAPI registers only the first occurrence — all others are silently ignored, "
                    f"causing incorrect responses. Each route path must be unique."
                )
                break
            _seen_paths[_rp] = True

        # Weak RETURNS CONTRACT check — `# Returns: {fieldname}` with only one bare identifier
        # gives the frontend no information about list item fields, causing field-name mismatches.
        _weak_rc = _re_proxy.findall(r'#\s*Returns:\s*\{(\w+)\}\s*$', app_py, _re_proxy.MULTILINE)
        if _weak_rc:
            errors.append(
                f"CONTRACT_ERROR: app.py has weak Returns contracts with only a bare field name "
                f"(e.g., '# Returns: {{{_weak_rc[0]}}}'). For list fields, document the exact field names "
                f"of each list item: '# Returns: {{items: [{{time: str, temp: float, ...}}]}}'. "
                f"The frontend reads these names literally — vague contracts cause field-name mismatches."
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

            # ── RULES.MD COMPLIANCE GATE ────────────────────────────────────────
            # Pattern-based, NOT module-name based. Only fires when a corresponding
            # feature is actually present in the generated tsx. Each violation forces
            # a re-generation cycle so the personas catch the same bugs we keep seeing.
            _tsx_raw = _original_tsx
            _app_py = blob.get("app.py", "")

            # 1. STAR MAP NASA IMAGERY RULE — if a star map / sky map view exists,
            # tsx must fetch SkyView and draw the image to canvas.
            _has_star_map = bool(re.search(
                r'(?:star\s*map|sky\s*map|planetary[\s_]?explorer|night\s*sky|celestial\s*map)',
                _tsx_raw, re.IGNORECASE
            ))
            if _has_star_map:
                _has_skyview_fetch = ("astronomy/skyview" in _tsx_raw) or ("/skyview" in _tsx_raw)
                _has_drawimage = "drawImage(" in _tsx_raw
                if not (_has_skyview_fetch and _has_drawimage):
                    errors.append(
                        "RULES_COMPLIANCE: STAR MAP NASA IMAGERY RULE violated — star map view present but tsx is missing "
                        "either the `/astronomy/skyview` fetch or `ctx.drawImage(` call. The map MUST render real NASA SkyView "
                        "imagery as the canvas background, NOT synthetic dots. Regenerate the star map view to comply."
                    )

            # 2. WEATHER CITY GEOCODING RULE — if a weather hero exists, must NOT
            # show raw `Region ${lat}` coordinates.
            if re.search(r'Region\s*[`{$]+\s*\w*\s*lat', _tsx_raw, re.IGNORECASE) or \
               re.search(r'Region\s+\$\{[^}]*lat', _tsx_raw):
                errors.append(
                    "RULES_COMPLIANCE: WEATHER CITY GEOCODING RULE violated — tsx renders raw "
                    "`Region ${lat}, ${lon}` coordinates in the hero. The hero MUST display a "
                    "city/state name from reverse geocoding. Add OWM reverse-geocoding to /weather/current "
                    "and use `${city}, ${state}` in the hero. Regenerate to comply."
                )

            # 3. RECHARTS RESPONSIVECONTAINER HEIGHT RULE — every ResponsiveContainer must
            # have an explicit height literal within ~200 chars before it.
            for _rc_match in re.finditer(r'<ResponsiveContainer\b', _tsx_raw):
                _rc_pos = _rc_match.start()
                _rc_window = _tsx_raw[max(0, _rc_pos - 250):_rc_pos]
                if not re.search(r'height\s*[:=]\s*[\'"]?\d', _rc_window) and \
                   not re.search(r'height\s*=\s*\{[^}]*\d', _rc_window):
                    errors.append(
                        "RULES_COMPLIANCE: RECHARTS RESPONSIVECONTAINER HEIGHT RULE violated — "
                        "<ResponsiveContainer> appears without an explicit pixel height in its parent "
                        "(within 200 chars). Wrap it in `<div style={{height: 400}}>`. This causes "
                        "'Invariant failed' crashes through the ErrorBoundary."
                    )
                    break

            # 4. LEAFLET MARKER PLOTTING RULE — if leaflet is used AND backend has
            # at least one route that returns a list (events/quakes/storms/fires/markers),
            # tsx MUST contain a marker creation call.
            if _uses_leaflet:
                _backend_returns_list = bool(re.search(
                    r'(?:earthquakes|quakes|events|fires|storms|alerts|wildfires|volcanoes|hazards)',
                    _app_py, re.IGNORECASE
                ))
                if _backend_returns_list:
                    _has_marker_call = bool(re.search(
                        r'L\.(?:circleMarker|marker|circle|layerGroup)\s*\(',
                        _tsx_raw
                    ))
                    if not _has_marker_call:
                        errors.append(
                            "RULES_COMPLIANCE: LEAFLET MARKER PLOTTING RULE violated — backend exposes "
                            "event/hazard data but tsx contains no `L.circleMarker(`, `L.marker(`, or "
                            "`L.layerGroup(` calls. Data is fetched but never plotted on the map. "
                            "Add a useEffect keyed on `[map, dataArray]` that creates markers for every item."
                        )

            # 5. ERROR BOUNDARY NAMING CONVENTION RULE — if an ErrorBoundary class exists,
            # the fallback UI must use canonical "Module View Error" + "Retry" strings so the
            # render check can detect failures.
            _has_error_boundary = bool(re.search(
                r'class\s+\w*ErrorBoundary\w*\s+extends\s+(?:React\.)?Component',
                _tsx_raw
            ))
            if _has_error_boundary:
                # Disallowed non-canonical phrases that indicate the LLM invented its own UI.
                _bad_eb_phrases = [
                    "View Crashed", "Module Rendering Error", "View Render Failure",
                    "Attempt Recovery", "Retry View Initialization",
                ]
                _found_bad = [p for p in _bad_eb_phrases if p in _tsx_raw]
                if _found_bad:
                    errors.append(
                        f"RULES_COMPLIANCE: ERROR BOUNDARY NAMING CONVENTION RULE violated — "
                        f"ErrorBoundary uses non-canonical fallback text: {', '.join(_found_bad)}. "
                        f"MUST use exact heading 'Module View Error' and exact button label 'Retry' so "
                        f"the headless render check can detect crashes (otherwise false-pass results)."
                    )

            # 6. BACKEND EMPTY-PAYLOAD GUARD RULE — every upstream-calling route should
            # return 503 (or raise HTTPException) on failure, NOT 200 with empty data.
            # Heuristic: count routes that catch exceptions but return {} or [].
            _empty_return_pattern = re.compile(
                r'except[^:]*:\s*\n(?:\s*(?:logger|logging|print|narrate)[^\n]*\n)*\s*return\s*(?:\{\s*\}|\[\s*\])',
                re.MULTILINE
            )
            _empty_returns = _empty_return_pattern.findall(_app_py)
            if len(_empty_returns) >= 2:
                errors.append(
                    f"RULES_COMPLIANCE: BACKEND EMPTY-PAYLOAD GUARD RULE violated — app.py has "
                    f"{len(_empty_returns)} except-handlers that return empty `{{}}` or `[]` instead of "
                    f"raising HTTPException(503). Failed upstream calls MUST return 503 so the frontend "
                    f"can show a 'Live data temporarily unavailable' banner instead of all-zero cards."
                )

            if "<input" in index_tsx:
                # Case-insensitive check: React uses camelCase `onKeyDown` / `onKeyPress`
                # but a raw `in` test against the original source misses those. Lowercase
                # the haystack so the auto-fix (which injects `onKeyDown={...}`) is actually
                # recognised on re-validation — previously this flagged even repaired files.
                _lower_tsx = index_tsx.lower()
                if "onkeydown" not in _lower_tsx and "onkeypress" not in _lower_tsx:
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



            # -- FRONTEND-BACKEND ROUTE COMPLETENESS CHECK -------------------
            # Every fetch('/api/MODULE/path') in TSX must have a matching
            # @router.get/post('/path') in app.py. Missing routes cause 404.
            _frontend_fetch_paths = set()
            # Strip JavaScript regex literals first so route paths inside
            # `path.match(/\/weather\/current$/)` style code are not picked up
            # as "missing fetch routes" — those `$`-anchored strings can never
            # have a backend match because `$` is not legal in a FastAPI route
            # path. Same protection blocks `/...\b/`, `/...*/`, etc.
            _tsx_no_regex = _re_proxy.sub(
                r"/(?:\\.|[^/\\\n])+/[gimsuy]*",
                "",
                _original_tsx,
            )
            for _fm in _re_proxy.finditer(
                r"/api/[^/\"'`\)\s]+/([^\"'`\)\s?${}*+\\][^\"'`\)\s?${}*+\\]*)",
                _tsx_no_regex,
            ):
                _raw = _fm.group(1).rstrip("/")
                # Hard-skip anything still carrying regex meta-chars or template
                # placeholders. These never represent a literal HTTP path.
                if any(c in _raw for c in ("$", "{", "}", "*", "+", "\\", ";")):
                    continue
                if _raw:
                    _frontend_fetch_paths.add("/" + _raw)

            _backend_route_defs = set()
            for _rm in _re_proxy.finditer(
                r"@router[.](?:get|post|put|delete)\s*\([\'\"](/[^\'\"]+)[\'\"]",
                _app_py
            ):
                _backend_route_defs.add(_rm.group(1))

            _orphan_fetches = sorted(
                p for p in _frontend_fetch_paths if p not in _backend_route_defs
            )
            if _orphan_fetches:
                _orphan_list = ", ".join(_orphan_fetches[:6])
                errors.append(
                    f"CONTRACT_ERROR: index.tsx fetches {len(_orphan_fetches)} route(s) with no "
                    f"matching @router.get/post in app.py: {_orphan_list}. "
                    f"Every frontend fetch(/api/MODULE/path) MUST have a backend route. "
                    f"Missing routes return 404 and cause silent API failures in the UI."
                )

            # -- LAYOUT CRAMPING CHECK ----------------------------------------
            # h-screen + overflow-y-auto on the root view div locks all content
            # into 100vh. For multi-section pages use min-h-screen instead.
            # NOTE: `\bh-screen\b` alone matches INSIDE `min-h-screen` because `-` is a
            # non-word character, so the boundary between `-` and `h` qualifies. Use a
            # negative lookbehind for `-` so the fixed token `min-h-screen` does not
            # trip this check after the LAYOUT REPAIR auto-fix rewrites the file.
            _has_hscreen_scroll = bool(_re_proxy.search(
                r"(?<!-)h-screen\b[^\"']{0,60}\boverflow-y-auto\b"
                r"|\boverflow-y-auto\b[^\"']{0,60}(?<!-)h-screen\b",
                _original_tsx
            ))
            if _has_hscreen_scroll:
                _sec_count = len(_re_proxy.findall(
                    r"<(?:section|div)\b[^>]*\bclassName=",
                    _original_tsx
                ))
                if _sec_count >= 10:
                    errors.append(
                        "LAYOUT_ERROR: index.tsx uses `h-screen overflow-y-auto` on a view root "
                        "container that has many child sections. This locks all content into 100vh "
                        "so sections fight for space (hero hidden, map cut off, cards cramped). "
                        "Use `min-h-screen` for scrollable multi-section pages so the page grows "
                        "naturally. Reserve `h-screen` ONLY for true single-screen layouts "
                        "(a lone full-screen map with no other sections)."
                    )

            # -- SYNTHETIC GRID DATA CHECK ------------------------------------
            # Catches the "5x5 identical arrows" failure mode where a developer
            # synthesizes a uniform grid of markers client-side instead of fetching
            # real geospatial data. Pattern: nested for-loops (or .map of indices)
            # whose iteration variable is multiplied by a constant offset and fed
            # directly into a Leaflet marker constructor. Domain-agnostic — fires
            # for currents, wind, flow, traffic, anything that should be real data.
            _synth_grid_re = _re_proxy.compile(
                r"for\s*\([^)]*\)\s*\{[^}]{0,400}for\s*\([^)]*\)\s*\{[^}]{0,400}"
                r"L\.(?:marker|circleMarker|circle|polyline|polygon)\s*\(",
                _re_proxy.DOTALL,
            )
            if _synth_grid_re.search(_original_tsx):
                errors.append(
                    "DATA_ERROR: index.tsx contains a nested for-loop that constructs "
                    "L.marker / L.circleMarker / L.polyline calls from index variables. "
                    "This synthesizes a uniform grid of fake markers (identical arrows / dots / "
                    "vectors) instead of fetching real geospatial data. Replace the loop with a "
                    "fetch() to a backend route that returns real coordinates + values."
                )

            # -- LEAFLET MAP CONTAINER HEIGHT CHECK ---------------------------
            # A `<div ref={mapRef}>` with no explicit pixel/vh height collapses
            # in flex layouts so only a sliver of the map renders (the seismic
            # "map cut off at bottom" failure). Require an explicit height literal.
            _map_div_iter = _re_proxy.finditer(
                r"<div\b[^>]*\bref=\{(\w+)\}[^>]*>",
                _original_tsx,
            )
            _map_refs_in_jsx = []
            for _md in _map_div_iter:
                _ref_name = _md.group(1)
                if not _re_proxy.search(rf"\b{_ref_name}\b\s*=\s*L\.map\(", _original_tsx) and \
                   not _re_proxy.search(rf"L\.map\(\s*{_ref_name}\b", _original_tsx) and \
                   not _re_proxy.search(rf"useCallback\([^)]*\b{_ref_name}\b", _original_tsx):
                    continue
                _attrs = _md.group(0)
                if not _re_proxy.search(
                    r"(?:height\s*[:=]\s*[\"']?\d|h-\[?\d|h-(?:48|56|64|72|80|96|screen)\b|min-h-\[)",
                    _attrs,
                ):
                    _map_refs_in_jsx.append(_ref_name)
            if _map_refs_in_jsx:
                errors.append(
                    f"LAYOUT_ERROR: Leaflet map container <div ref={{{_map_refs_in_jsx[0]}}}> "
                    f"has no explicit height (style={{{{height: ...}}}} or className h-[NNN]/h-96). "
                    f"In flex/grid parents the map collapses to ~0px and only a sliver renders. "
                    f"Add an explicit pixel height (e.g. style={{{{height:'480px',width:'100%'}}}}) "
                    f"to every map container div."
                )

            # -- MAP-IN-CONDITIONAL MOUNT CHECK -------------------------------
            # `useEffect(..., [])` with `L.map(refName)` blows up with
            # 'Invariant failed' when the ref's <div> is inside a `{cond && (...)}`
            # branch — the empty-dep effect runs once on mount when the div is
            # still null. Forces the safer callback-ref pattern.
            for _eff in _re_proxy.finditer(
                r"useEffect\s*\(\s*\(\s*\)\s*=>\s*\{([^}]{0,1200})\}\s*,\s*\[\s*\]\s*\)",
                _original_tsx,
                _re_proxy.DOTALL,
            ):
                _body = _eff.group(1)
                _map_init = _re_proxy.search(r"L\.map\(\s*(\w+)", _body)
                if not _map_init:
                    continue
                _ref_target = _map_init.group(1)
                if _re_proxy.search(
                    rf"\{{[^{{}}]*&&[^{{}}]*<div[^>]*\bref=\{{{_ref_target}\}}",
                    _original_tsx,
                    _re_proxy.DOTALL,
                ):
                    errors.append(
                        f"RUNTIME_ERROR: index.tsx initializes Leaflet via "
                        f"`useEffect(..., [])` against ref `{_ref_target}` whose <div> lives "
                        f"inside a conditional render branch. The empty-dep effect fires once "
                        f"on mount when the div is still null, then never re-runs — Leaflet "
                        f"throws 'Invariant failed' and the ErrorBoundary takes over. "
                        f"Use a callback ref `const cb = useCallback((node) => {{ if(node && "
                        f"!instanceRef.current) instanceRef.current = L.map(node, ...); }}, [])` "
                        f"and bind `<div ref={{cb}}>` so init fires exactly when the div mounts."
                    )
                    break

            # -- TEMPORAL FRAMES PAYLOAD CHECK --------------------------------
            # Catches the "PAST 13 / FUTURE 0" radar failure: any backend route
            # that exposes a *_frames payload (radar, satellite, animation, timeline,
            # playback) MUST return BOTH a past array AND a forward-looking array.
            # Returning past_frames=[...] alone leaves the playback timeline stuck
            # in the past with no nowcast/forecast extension.
            _frames_route_re = _re_proxy.compile(
                r"@router\.(?:get|post)\([\"'](/[^\"']*(?:radar|frames|playback|"
                r"animation|timeline|loop)[^\"']*)[\"']",
                _re_proxy.IGNORECASE,
            )
            for _fm in _frames_route_re.finditer(_app_py):
                _route_path = _fm.group(1)
                _route_start = _fm.end()
                _route_body = _app_py[_route_start:_route_start + 4000]
                _next_route = _re_proxy.search(r"\n@router\.", _route_body)
                if _next_route:
                    _route_body = _route_body[:_next_route.start()]
                _has_past = bool(_re_proxy.search(
                    r"past(?:_frames)?|history|historical|previous", _route_body, _re_proxy.IGNORECASE
                ))
                _has_future = bool(_re_proxy.search(
                    r"nowcast|forecast|future|upcoming|projected|predicted",
                    _route_body, _re_proxy.IGNORECASE
                ))
                if _has_past and not _has_future:
                    errors.append(
                        f"DATA_ERROR: app.py route `{_route_path}` returns past/historical frames "
                        f"but no nowcast/forecast frames. The timeline UI will be stuck showing "
                        f"only past data (e.g. radar shows 06:30 when current time is 06:37, "
                        f"FUTURE: 0 FRAMES). Fetch and return both arrays in the response payload."
                    )
                    break

            # -- SPAN-AS-INTERACTIVE-TAB DETECTION ----------------------------
            # GENERIC: a <span> is flagged only when its className carries clear
            # interactive affordances (cursor-pointer, hover:, tab/chip styling,
            # border-b-2, rounded w/ bg-) AND the span itself has no onClick.
            # This is domain-agnostic — no module-specific vocabulary.
            _span_tab_matches = _re_proxy.findall(
                r"<span\b[^>]*className=[\"'][^\"']*"
                r"(?:cursor-pointer|hover:|border-b-2|rounded(?:-\w+)?\s+bg-\w|"
                r"tab-\w|chip-\w)"
                r"[^\"']*[\"'][^>]*>[^<]{1,80}</span>",
                _original_tsx, _re_proxy.IGNORECASE
            )
            if _span_tab_matches:
                # Only flag spans that lack onClick AND are styled interactively.
                _interactive_without_onclick = [
                    m for m in _span_tab_matches
                    if not _re_proxy.search(r"\bonClick\b", m)
                ]
                if _interactive_without_onclick:
                    errors.append(
                        f"UI_ERROR: index.tsx contains {len(_interactive_without_onclick)} <span> "
                        f"element(s) styled as interactive controls (cursor-pointer / hover / tab / "
                        f"chip affordances) but missing onClick handlers. Replace with "
                        f"<button onClick={{...}}> wired to the relevant React state."
                    )

            # -- HARDCODED US-CENTER COORDINATES CHECK ------------------------
            # lat=39.8283 / lon=-98.5795 is the geographic center of the USA
            # (Smith County, Kansas). LLMs routinely hardcode these as default
            # weather coordinates, so every user sees Kansas weather.
            # Flag as a RULES_COMPLIANCE violation regardless of module.
            _has_us_center_lat = "39.8283" in _tsx_raw or "39.82" in _tsx_raw
            _has_us_center_lon = "-98.5795" in _tsx_raw or "-98.57" in _tsx_raw
            if _has_us_center_lat and _has_us_center_lon:
                errors.append(
                    "RULES_COMPLIANCE: BROWSER GEOLOCATION INITIALIZATION RULE violated — "
                    "index.tsx contains hardcoded US geographic center coordinates "
                    "(39.8283, -98.5795 — Smith County, Kansas). NEVER use these as a default. "
                    "Every user will see Kansas weather regardless of their location. "
                    "Replace with `navigator.geolocation.getCurrentPosition()` on mount. "
                    "On denial, show a 'Location access denied' banner with city search enabled."
                )

            # -- BROWSER GEOLOCATION PRESENCE CHECK ---------------------------
            # Any module with a weather / forecast / conditions view MUST call
            # navigator.geolocation to get the user's real location. Without it
            # the app uses whatever hardcoded default the LLM chose.
            _has_weather_view = bool(_re_proxy.search(
                r'(?:weather|forecast|current\s*conditions|temperature)',
                _tsx_raw, _re_proxy.IGNORECASE
            )) and bool(_re_proxy.search(
                r'(?:weatherview|weatherpage|weather_view|weather-view|WeatherView|WeatherPage)',
                _tsx_raw
            ))
            if _has_weather_view and "navigator.geolocation" not in _tsx_raw:
                errors.append(
                    "RULES_COMPLIANCE: BROWSER GEOLOCATION INITIALIZATION RULE violated — "
                    "Weather view detected but tsx has no `navigator.geolocation.getCurrentPosition()` "
                    "call. The app will show weather for a hardcoded default location. "
                    "Add geolocation on mount: `navigator.geolocation.getCurrentPosition("
                    "(pos) => { setLat(pos.coords.latitude); setLon(pos.coords.longitude); }, "
                    "() => setLocationError('Location access denied — enter your city above.'));`"
                )

            # -- SKYVIEW CANVAS CORS PROXY CHECK ------------------------------
            # If the star map fetches /astronomy/skyview AND draws it on canvas
            # via ctx.drawImage(), the backend MUST return a base64 data URL —
            # NOT an external HTTPS URL. Browsers block ctx.drawImage() on
            # cross-origin images (CORS canvas taint), causing a silent failure
            # where the canvas background stays black even though the fetch succeeded.
            _has_skyview_canvas = (
                ("astronomy/skyview" in _tsx_raw or "/skyview" in _tsx_raw) and
                "drawImage(" in _tsx_raw
            )
            if _has_skyview_canvas and _app_py:
                _sv_idx = _app_py.find("skyview")
                if _sv_idx >= 0:
                    _sv_snippet = _app_py[_sv_idx:_sv_idx + 2500]
                    _sv_next = _re_proxy.search(r"\n@router\.", _sv_snippet)
                    if _sv_next:
                        _sv_snippet = _sv_snippet[:_sv_next.start()]
                    _returns_https = bool(_re_proxy.search(
                        r"""['"]\s*image_url\s*['"]\s*:\s*(?:url|f['"]\s*https?|f\"https?)""",
                        _sv_snippet
                    ))
                    _returns_base64 = bool(_re_proxy.search(
                        r"base64|data:image", _sv_snippet
                    ))
                    if _returns_https and not _returns_base64:
                        errors.append(
                            "RULES_COMPLIANCE: STAR MAP NASA IMAGERY RULE violated — "
                            "/astronomy/skyview route returns an external HTTPS URL as `image_url` "
                            "but the frontend draws it on canvas via ctx.drawImage(). "
                            "Browsers block ctx.drawImage() on cross-origin images (CORS canvas taint) — "
                            "the sky background will stay black even though the fetch succeeds. "
                            "The backend MUST proxy the NASA SkyView PNG and return a base64 data URL: "
                            "`import base64 as _b64; img_b64 = _b64.b64encode(resp.content).decode(); "
                            "return {'image_url': f'data:image/png;base64,{img_b64}'}`"
                        )

            # -- GEOLOCATION TIMEOUT CHECK ------------------------------------
            # navigator.geolocation.getCurrentPosition() called without a
            # { timeout: N } options argument hangs indefinitely when the
            # browser permission dialog is pending — the page freezes on the
            # loading spinner. Every getCurrentPosition call MUST have the
            # three-argument form with timeout: 8000.
            _geo_positions = list(_re_proxy.finditer(
                r"navigator\.geolocation\.getCurrentPosition\s*\(",
                _tsx_raw
            ))
            for _gp in _geo_positions:
                # Use brace-matching to find the FULL call content regardless of
                # argument length. A 400-char lookahead was too short when the
                # success/error callbacks contained many lines of code — the
                # third-arg options object (containing `timeout:`) fell outside
                # the window and the gate produced a false-positive violation even
                # after the deterministic repair had correctly injected the timeout.
                _gp_open = _gp.end() - 1  # position of the opening '('
                _gp_depth = 0
                _gp_i = _gp_open
                while _gp_i < len(_tsx_raw):
                    _gp_c = _tsx_raw[_gp_i]
                    if _gp_c in '({[':
                        _gp_depth += 1
                    elif _gp_c in ')}]':
                        _gp_depth -= 1
                        if _gp_depth == 0:
                            break
                    _gp_i += 1
                _gp_inner = _tsx_raw[_gp_open + 1: _gp_i] if _gp_i > _gp_open else ""
                if "timeout:" not in _gp_inner and "timeout :" not in _gp_inner:
                    errors.append(
                        "RULES_COMPLIANCE: GEOLOCATION TIMEOUT MANDATE violated — "
                        "`navigator.geolocation.getCurrentPosition()` called without a "
                        "`{ timeout: 8000, maximumAge: 30000 }` options argument. "
                        "Without a timeout the browser permission dialog hangs indefinitely "
                        "and the view freezes on the loading spinner. "
                        "ALWAYS use the three-argument form: "
                        "`getCurrentPosition(successFn, errorFn, { timeout: 8000, maximumAge: 30000 })`."
                    )
                    break

            # -- GENERIC STUB ROUTE DETECTION ---------------------------------
            # Any route whose body contains 3+ "baseline normal" placeholder
            # strings has no real LLM calls. Fires on ANY route name — no
            # module-specific route path hardcoded here.
            for _sr_m in re.finditer(r"@router\.(?:get|post)\(['\"]([^'\"]+)['\"]", _app_py):
                _sr_start = _sr_m.end()
                _sr_next = re.search(r"\n@router\.", _app_py[_sr_start:_sr_start + 4000])
                _sr_body = _app_py[_sr_start:_sr_start + (_sr_next.start() if _sr_next else 4000)]
                _bn_count = _sr_body.lower().count("baseline normal")
                if _bn_count >= 3:
                    _sr_path = _sr_m.group(1)
                    errors.append(
                        f"DATA_ERROR: route `{_sr_path}` contains {_bn_count} "
                        f"hardcoded 'baseline normal' placeholder strings — no real LLM calls. "
                        "This makes any tab dependent on this route show static stub text. "
                        "The route MUST call the LLM for synthesis using real fetched data. "
                        "FORBIDDEN strings in route body: 'baseline normal', 'coupling signals baseline normal', "
                        "'precursor signals baseline normal'. Replace with real asyncio.gather() data fetches "
                        "and a call_llm_async() synthesis per the LLM CALL MANDATE."
                    )
                    break

            # -- SKYVIEW URL ENCODING CHECK -----------------------------------
            # SkyView survey names contain spaces (e.g. "DSS2 Red"). If the URL
            # is built with f-string interpolation of the raw survey string,
            # the space makes the URL malformed and NASA returns HTML instead
            # of PNG. The backend then base64-encodes the HTML, the frontend
            # img.onerror fires, and the canvas stays black.
            _sv_route_idx = _app_py.find("skyview.gsfc.nasa.gov")
            if _sv_route_idx >= 0:
                _sv_block = _app_py[max(0, _sv_route_idx - 200):_sv_route_idx + 500]
                _has_url_encode = bool(_re_proxy.search(
                    r"(?:quote|quote_plus|urlencode)\s*\(", _sv_block
                ))
                _has_content_type_check = bool(_re_proxy.search(
                    r"content.type|content_type", _sv_block, _re_proxy.IGNORECASE
                ))
                if not _has_url_encode:
                    errors.append(
                        "RULES_COMPLIANCE: SKYVIEW URL ENCODING MANDATE violated — "
                        "`skyview.gsfc.nasa.gov` URL built without `urllib.parse.quote()` "
                        "on the survey parameter. Survey names like 'DSS2 Red' contain spaces "
                        "that make the URL malformed — NASA returns HTML instead of PNG. "
                        "Fix: `encoded_survey = urllib.parse.quote(survey, safe='')` "
                        "then use `?Survey={encoded_survey}&...` in the URL."
                    )
                if not _has_content_type_check:
                    errors.append(
                        "RULES_COMPLIANCE: SKYVIEW URL ENCODING MANDATE violated — "
                        "/astronomy/skyview route does not verify `resp.headers['content-type']` "
                        "starts with 'image/' before base64-encoding. When NASA returns HTML "
                        "(e.g. on a malformed URL), the backend base64-encodes the HTML page "
                        "and the frontend silently fails with `img.onerror`. "
                        "Add: `if not resp.headers.get('content-type','').startswith('image/'): "
                        "return {'image_url': ''}`"
                    )

            # -- LUCIDE-REACT NATIVE CONSTRUCTOR SHADOW CHECK -----------------
            # `import { ..., Map, ... } from 'lucide-react'` brings a React
            # component named Map into module scope, shadowing the native JS
            # Map constructor. Any `new Map()` in index.tsx then calls the
            # Lucide component as a constructor → "Map is not a constructor"
            # crash. Build gate detects unaliased Map (or other JS builtins)
            # in any icon-library import.
            _NATIVE_BUILTINS = {
                "Map", "Set", "Symbol", "Error", "Event", "URL", "Promise",
                "Date", "Array", "Object", "Function", "Number", "String",
                "Boolean", "Image", "Text", "Comment", "Range", "Screen",
                "Selection", "Navigation", "History", "Location", "Document",
                "Window", "Worker", "Request", "Response", "Headers",
                "FormData", "Blob", "File",
            }
            _icon_lib_pattern = _re_proxy.compile(
                r"""from\s+['"](?:lucide-react|@heroicons/react|react-icons/[^'"]+|phosphor-react)['"]\s*;?\s*\nimport\s*\{[^}]*\}|import\s*\{([^}]*)\}\s*from\s*['"](?:lucide-react|@heroicons/react|react-icons/[^'"]+|phosphor-react)['"]""",
                _re_proxy.MULTILINE | _re_proxy.DOTALL
            )
            for _ilm in _icon_lib_pattern.finditer(_tsx_raw):
                _imports_str = _ilm.group(1) or _ilm.group(0)
                _imported_names = _re_proxy.findall(r'\b(\w+)(?:\s+as\s+\w+)?\s*[,}]', _imports_str)
                _bare_names = _re_proxy.findall(r'\b(\w+)\s*[,}]', _imports_str)
                for _bn in _bare_names:
                    if _bn in _NATIVE_BUILTINS:
                        _in_as = bool(_re_proxy.search(
                            rf'\b{re.escape(_bn)}\s+as\s+\w+', _imports_str
                        ))
                        if not _in_as:
                            errors.append(
                                f"RULES_COMPLIANCE: LUCIDE-REACT NATIVE CONSTRUCTOR SHADOW MANDATE violated — "
                                f"`{_bn}` imported unaliased from an icon library. "
                                f"`{_bn}` is a native JavaScript global constructor; importing it without `as` "
                                f"shadows the built-in for the entire module scope. "
                                f"Any code calling `new {_bn}()` will crash with 'not a constructor'. "
                                f"Fix: `import {{ {_bn} as {_bn}Icon }} from 'lucide-react'` "
                                f"and use `<{_bn}Icon />` everywhere in JSX."
                            )
                            break

            # -- EXTERNAL VALIDATION RULES (validation_rules.json) ------------
            # Module-specific route names, variable identifiers, and feature
            # trigger strings live in resources/validation_rules.json — NOT here.
            # This call applies all JSON-defined checks generically.
            self._run_validation_rules(_app_py, _tsx_raw, errors)

            # -- OCEAN SST LAND MASK OPACITY CHECK ----------------------------
            # dark_nolabels or light_nolabels at opacity > 0.3 on top of SST
            # tiles is a full-world basemap that covers both land AND ocean,
            # completely hiding the SST color gradient.
            _sst_mask_bad = _re_proxy.search(
                r"""(?:dark_nolabels|light_nolabels)[^'"]*['"][^}]*opacity\s*:\s*0\.[6-9]\d*""",
                _tsx_raw
            )
            if _sst_mask_bad:
                errors.append(
                    "RULES_COMPLIANCE: OCEAN SST TILE VISIBILITY MANDATE violated — "
                    "a `dark_nolabels` or `light_nolabels` CartoDB tile layer is configured with opacity > 0.3 "
                    "on top of an SST/temperature data layer. These are full-world tiles that cover BOTH land "
                    "and ocean — at high opacity they completely hide the SST color gradient over ocean. "
                    "Fix: replace the full-world land mask with `dark_only_labels` tiles (transparent "
                    "everywhere except labels) at zIndex 500 and opacity 1.0. "
                    "Per OCEAN SST TILE VISIBILITY MANDATE."
                )

            # -- SST TOGGLE NON-FUNCTIONAL CHECK ------------------------------
            # SST button with empty onClick is a non-functional toggle (UI_ERROR).
            _sst_empty_click = _re_proxy.search(
                r"""onClick\s*=\s*\{\s*\(\s*\)\s*=>\s*\{\s*(?:/\*[^*]*\*/\s*)?\}\s*\}""",
                _tsx_raw
            )
            if _sst_empty_click:
                errors.append(
                    "UI_ERROR: Empty `onClick={() => { /* ... */ }}` found in index.tsx. "
                    "At least one interactive button has a non-functional click handler (no state change). "
                    "This is typically the SST layer toggle button. Every onClick MUST call a state setter "
                    "or dispatch. FORBIDDEN: onClick with only a comment or empty body. "
                    "Per OCEAN SST TILE VISIBILITY MANDATE."
                )

            # -- RAINVIEWER NOWCAST URL SPECIFICITY CHECK ---------------------
            # The TEMPORAL FRAMES check passes if the word "nowcast" appears
            # anywhere in the radar route body. But the frontend still shows
            # "No forecast data" if the backend fetches the WRONG endpoint or
            # only reads `radar.past` and never `radar.nowcast`. Enforce that
            # any radar route actually fetches from api.rainviewer.com AND
            # parses the `nowcast` key from the returned JSON.
            _radar_route_re = _re_proxy.compile(
                r"@router\.(?:get|post)\([\"'](/[^\"']*(?:radar|weather-map)[^\"']*)[\"']",
                _re_proxy.IGNORECASE,
            )
            for _rr in _radar_route_re.finditer(_app_py):
                _rr_start = _rr.end()
                _rr_body = _app_py[_rr_start:_rr_start + 5000]
                _next_route = _re_proxy.search(r"\n@router\.", _rr_body)
                if _next_route:
                    _rr_body = _rr_body[:_next_route.start()]
                _has_rainviewer = bool(_re_proxy.search(r"rainviewer\.com", _rr_body))
                _has_nowcast_parse = bool(_re_proxy.search(
                    r"""(?:["']nowcast["']|\.nowcast\b|nowcast_frames|get\(['"']nowcast)""",
                    _rr_body
                ))
                if _has_rainviewer and not _has_nowcast_parse:
                    errors.append(
                        f"DATA_ERROR: app.py radar route `{_rr.group(1)}` fetches from RainViewer "
                        f"but does not parse the `radar.nowcast` array from the response. "
                        f"The timeline will show 'No forecast data' even though RainViewer always returns "
                        f"nowcast frames in `radar.nowcast`. Fix: after fetching "
                        f"`https://api.rainviewer.com/public/weather-maps.json`, read both "
                        f"`data['radar']['past']` AND `data['radar']['nowcast']` and return them as "
                        f"`past_frames` and `nowcast_frames`. Per RADAR FORECAST FRAMES MANDATE."
                    )
                    break

            # -- HAZARD CENTER MAP OVERFLOW CHECK -----------------------------
            # Hazard center map containers must NOT use flex-grow, h-full, or
            # height calculations based on viewport — this pushes bottom hazard
            # panels (storms/wildfires/floods) below the visible viewport.
            _has_hazard_view = bool(_re_proxy.search(
                r'(?:HazardView|HazardCenter|hazard.center|GlobalHazard|hazard.map)',
                _tsx_raw, _re_proxy.IGNORECASE
            ))
            if _has_hazard_view and _app_py:
                _hazard_overflow = bool(_re_proxy.search(
                    r'(?:flex-grow|flexGrow|h-full|height\s*:\s*["\']100%|calc\s*\(\s*100vh)',
                    _tsx_raw
                ))
                _hazard_map_ref = bool(_re_proxy.search(
                    r'(?:hazardMap|mapRef|threatMap)\s*=\s*(?:useRef|L\.map)',
                    _tsx_raw, _re_proxy.IGNORECASE
                ))
                if _hazard_overflow and _hazard_map_ref:
                    errors.append(
                        "LAYOUT_ERROR: Hazard Center map container uses `flex-grow`, `h-full`, or "
                        "`height: 100%` / `calc(100vh - ...)` which causes the map to fill all "
                        "remaining viewport space and pushes the Active Tropical Storms, Wildfire, "
                        "and Flood panels below the fold with no scroll indicator. "
                        "Fix: set `style={{height: '520px', width: '100%'}}` on the map container div. "
                        "Wrap the entire view in an `overflowY: 'auto'` scrollable column. "
                        "Per HAZARD CENTER MAP VIEWPORT OVERFLOW MANDATE."
                    )



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
