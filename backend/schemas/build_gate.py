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

# Punctuation/operators after which a "/" begins a JS/TS regex literal rather
# than a division operator. Used by the string/template scanners so that
# backticks or quotes INSIDE a regex literal (e.g. /`([^`]*)`/g or /it's/)
# do not corrupt template/string state tracking and produce phantom
# "unterminated string literal" / "unclosed template literal" errors that NO
# repair can satisfy (the source is already valid).
_REGEX_PREV_CHARS = set("(,=:[!&|?{};+-*%<>~^")


def _scan_regex_literal_end(line: str, i: int):
    """Given line[i] == '/' that begins a regex literal, return the index just
    past the closing '/<flags>'. Returns None if the regex is not closed on
    this single line (caller then treats '/' as an ordinary character)."""
    j = i + 1
    n = len(line)
    in_class = False
    while j < n:
        c = line[j]
        if c == '\\':
            j += 2
            continue
        if in_class:
            if c == ']':
                in_class = False
            j += 1
            continue
        if c == '[':
            in_class = True
            j += 1
            continue
        if c == '/':
            j += 1
            while j < n and line[j].isalpha():
                j += 1
            return j
        j += 1
    return None


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

    def _check_undeclared_module_dicts(self, app_py: str, errors: list) -> None:
        """
        AST-based check: find any name X where X[key] is used inside a router handler
        function body but X is never assigned at module scope. This catches the common
        NameError pattern where a caching dict is referenced in a function without a
        corresponding module-level initialization, causing HTTP 500 on every request.
        Only fires for names matching a 'cache/data/state/store' naming pattern since
        those are the overwhelmingly common source of this bug.
        """
        if not app_py or not app_py.strip():
            return
        try:
            tree = ast.parse(app_py)
        except SyntaxError:
            return

        _cache_name_re = re.compile(
            r'^_\w*(?:cache|data|state|store|buffer|queue|result|pool|registry|lock)\w*$',
            re.IGNORECASE
        )

        module_scope_names = set()
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        module_scope_names.add(target.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                module_scope_names.add(node.target.id)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    module_scope_names.add(alias.asname or alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    module_scope_names.add(alias.asname or alias.name)

        _reported = set()
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            local_names = set()
            for child in ast.walk(node):
                if isinstance(child, ast.Assign):
                    for t in child.targets:
                        if isinstance(t, ast.Name):
                            local_names.add(t.id)
                elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                    local_names.add(child.target.id)
                elif isinstance(child, ast.arg):
                    local_names.add(child.arg)
            for child in ast.walk(node):
                if (isinstance(child, ast.Subscript)
                        and isinstance(child.value, ast.Name)):
                    name = child.value.id
                    if (name not in module_scope_names
                            and name not in local_names
                            and name not in _reported
                            and _cache_name_re.match(name)):
                        _reported.add(name)
                        errors.append(
                            f"DATA_ERROR: [app.py] UNDECLARED MODULE-LEVEL DICT '{name}' — "
                            f"used as `{name}[...]` inside function `{node.name}()` but never "
                            f"assigned at module scope. Every request to this route will throw "
                            f"NameError 500. Fix: add `{name} = {{\"result\": None, \"timestamp\": 0, "
                            f"\"running\": False}}` at module scope BEFORE the first @router decorator."
                        )

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

            _rule_target = _c.get("target", "index.tsx")
            _target_tag = " [app.py]" if _rule_target == "app.py" else ""

            if _ctype == "body_guard":
                _src = app_py if _rule_target == "app.py" else tsx_raw
                _anchor = _c.get("anchor", "")
                # Collect EVERY occurrence of the anchor — the first hit is
                # often a comment, route-table string, or import reference
                # rather than the actual @router handler. If we only check
                # the window around the first hit, deterministic injections
                # placed at the real handler site (typically the LAST
                # occurrence) get missed and the validator loops forever.
                _indices = []
                _start = 0
                while True:
                    _i = _src.find(_anchor, _start)
                    if _i < 0:
                        break
                    _indices.append(_i)
                    _start = _i + 1
                if not _indices:
                    continue
                _body_chars = _c.get("body_chars", 3000)
                _gp = _c.get("guard_pattern")
                _fp = _c.get("fail_pattern")
                # Look-behind window. A route anchor (e.g. "/space/current" or the
                # bare word "space") matches the route-path STRING, but the data it
                # depends on is frequently fetched by helper functions defined just
                # ABOVE the route (e.g. `async def _fetch_flux()` returning f107
                # right before `@router.get("/space/current")`). A forward-only
                # window never sees those helpers, producing false-positive
                # DATA_ERRORs that NO idiomatic repair can satisfy — the validator
                # then loops forever. For pure guard_absent mandates (where finding
                # the guard can only REDUCE false positives) we scan a symmetric
                # window around the anchor. Forbidden-pattern checks (guard_present
                # / *_fail_present) stay forward-only so unrelated preceding code
                # cannot trip them. Override per-rule via "back_chars" in the JSON.
                _back_chars = _c.get("back_chars")
                if _back_chars is None:
                    _back_chars = _body_chars if (_fw == "guard_absent" and not _fp) else 0
                # Guard satisfied if ANY window contains the guard pattern;
                # fail-pattern fires only if EVERY window contains it.
                _guard_found = False
                _fail_in_all = True if _fp else False
                for _idx in _indices:
                    _body = _src[max(0, _idx - _back_chars): _idx + _body_chars]
                    if _gp and re.search(_gp, _body, _flags):
                        _guard_found = True
                    if _fp and not re.search(_fp, _body, _flags):
                        _fail_in_all = False
                if not _gp:
                    _guard_found = True
                _fail_found = _fail_in_all if _fp else False
                if _fw == "guard_absent_and_fail_present":
                    if not _guard_found and _fail_found:
                        errors.append(f"{_cat}:{_target_tag} {_msg}")
                elif _fw == "guard_absent":
                    if not _guard_found:
                        errors.append(f"{_cat}:{_target_tag} {_msg}")
                elif _fw == "guard_present":
                    if _guard_found:
                        errors.append(f"{_cat}:{_target_tag} {_msg}")

            elif _ctype == "presence_guard":
                _src = app_py if _rule_target == "app.py" else tsx_raw
                if not any(t in _src for t in _c.get("trigger_any", [])):
                    continue
                _gp = _c.get("guard_pattern")
                _guard_found = bool(re.search(_gp, _src, _flags)) if _gp else True
                if _fw == "guard_present":
                    if _guard_found:
                        errors.append(f"{_cat}:{_target_tag} {_msg}")
                else:
                    if not _guard_found:
                        errors.append(f"{_cat}:{_target_tag} {_msg}")

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
                    errors.append(f"{_cat}:{_target_tag} {_msg}")

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

        # AST check: detect module-level dict variables used inside @router handler functions
        # but never declared at module scope. The most common form is a caching dict like
        # `_precursor_cache["result"]` inside `async def precursor_analysis()` where the
        # dict is never initialized at module scope — causing NameError 500 on every request.
        self._check_undeclared_module_dicts(app_py, errors)

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

        # GENERIC PAREN-BALANCE CHECK — strips strings/comments and tracks paren
        # depth INSIDE each `${...}` template-literal placeholder. Catches the common
        # LLM-output failure mode where an expression like
        # `Math.max(...arr.map(d => Math.max(a,b) - Math.min(a,b)).toFixed(1)` is
        # missing one closing paren on the outer Math.max(. esbuild will fail with
        # `Expected ")" but found "}"` when the placeholder's `}` arrives before the
        # missing `)`. Whole-file paren counts often net to zero (string contents
        # compensate), so per-placeholder accounting is required. Module-agnostic.
        try:
            _pb_src = tsx_content
            _pb_i = 0
            _pb_len = len(_pb_src)
            _pb_open = 0
            _pb_close = 0
            _pb_first_neg_line = 0
            _pb_in_line = 1
            # State: 0=code, 1=line-comment, 2=block-comment,
            # 3=single-string, 4=double-string, 5=template-literal,
            # 6=jsx-text (between > and <)
            # We approximate JSX text as "outside braces immediately after a >"
            # but counting parens in JSX text is fine because JSX text rarely has
            # lone `(` `)`; just skip nothing extra and tolerate noise.
            _pb_state = 0
            # Template-literal placeholder depth (when inside ${...})
            _pb_tpl_stack = []  # stack of brace depths at ${ entry
            _pb_tpl_brace_depth = 0
            # Per-placeholder paren-depth tracking. When entering ${ push 0;
            # increment on (, decrement on ); on placeholder close, value MUST be 0.
            _pb_placeholder_paren_stack = []
            _pb_first_unbalanced_line = 0
            while _pb_i < _pb_len:
                _pb_ch = _pb_src[_pb_i]
                _pb_nx = _pb_src[_pb_i + 1] if _pb_i + 1 < _pb_len else ''
                if _pb_ch == '\n':
                    _pb_in_line += 1
                if _pb_state == 1:  # line comment
                    if _pb_ch == '\n':
                        _pb_state = 0
                    _pb_i += 1
                    continue
                if _pb_state == 2:  # block comment
                    if _pb_ch == '*' and _pb_nx == '/':
                        _pb_state = 0
                        _pb_i += 2
                        continue
                    _pb_i += 1
                    continue
                if _pb_state == 3:  # single quote
                    if _pb_ch == '\\':
                        _pb_i += 2
                        continue
                    if _pb_ch == "'":
                        _pb_state = 0
                    _pb_i += 1
                    continue
                if _pb_state == 4:  # double quote
                    if _pb_ch == '\\':
                        _pb_i += 2
                        continue
                    if _pb_ch == '"':
                        _pb_state = 0
                    _pb_i += 1
                    continue
                if _pb_state == 5:  # template literal raw
                    if _pb_ch == '\\':
                        _pb_i += 2
                        continue
                    if _pb_ch == '`':
                        _pb_state = 0
                        _pb_i += 1
                        continue
                    if _pb_ch == '$' and _pb_nx == '{':
                        # entering placeholder — switch to code, push template marker
                        _pb_tpl_stack.append(_pb_tpl_brace_depth)
                        _pb_tpl_brace_depth += 1
                        _pb_placeholder_paren_stack.append([0, _pb_in_line])
                        _pb_state = 0
                        _pb_i += 2
                        continue
                    _pb_i += 1
                    continue
                # state 0 = code
                if _pb_ch == '/' and _pb_nx == '/':
                    _pb_state = 1
                    _pb_i += 2
                    continue
                if _pb_ch == '/' and _pb_nx == '*':
                    _pb_state = 2
                    _pb_i += 2
                    continue
                if _pb_ch == "'":
                    _pb_state = 3
                    _pb_i += 1
                    continue
                if _pb_ch == '"':
                    _pb_state = 4
                    _pb_i += 1
                    continue
                if _pb_ch == '`':
                    _pb_state = 5
                    _pb_i += 1
                    continue
                if _pb_ch == '{':
                    if _pb_tpl_stack:
                        _pb_tpl_brace_depth += 1
                if _pb_ch == '}':
                    if _pb_tpl_stack and _pb_tpl_brace_depth - 1 == _pb_tpl_stack[-1]:
                        # closing ${...} placeholder — return to template literal
                        _pb_tpl_stack.pop()
                        _pb_tpl_brace_depth -= 1
                        _pp = _pb_placeholder_paren_stack.pop() if _pb_placeholder_paren_stack else None
                        if _pp and _pp[0] != 0 and _pb_first_unbalanced_line == 0:
                            _pb_first_unbalanced_line = _pp[1]
                        _pb_state = 5
                        _pb_i += 1
                        continue
                    if _pb_tpl_stack:
                        _pb_tpl_brace_depth -= 1
                if _pb_ch == '(':
                    _pb_open += 1
                    if _pb_placeholder_paren_stack:
                        _pb_placeholder_paren_stack[-1][0] += 1
                elif _pb_ch == ')':
                    _pb_close += 1
                    if _pb_close > _pb_open and _pb_first_neg_line == 0:
                        _pb_first_neg_line = _pb_in_line
                    if _pb_placeholder_paren_stack:
                        _pb_placeholder_paren_stack[-1][0] -= 1
                _pb_i += 1
            _pb_net = _pb_open - _pb_close
            if _pb_net > 5:
                errors.append(
                    f"SYNTAX_ERROR: index.tsx has unbalanced parentheses: {_pb_open} open vs {_pb_close} close "
                    f"(net=+{_pb_net}). At least one expression is missing a closing `)` — "
                    f"esbuild will fail with 'Expected \")\" but found \"}}\"' or similar. "
                    f"Common cause: `Math.max(...arr.map(d => ...)).toFixed(N)` missing outer close. Regenerate the affected component."
                )
            elif _pb_net < -5:
                errors.append(
                    f"SYNTAX_ERROR: index.tsx has excess closing parentheses: {_pb_open} open vs {_pb_close} close "
                    f"(net={_pb_net}, first excess at line ~{_pb_first_neg_line}). "
                    f"esbuild will fail with 'Unexpected \")\"'. Regenerate the affected component."
                )
            if _pb_first_unbalanced_line:
                errors.append(
                    f"SYNTAX_ERROR: index.tsx has unbalanced parentheses inside a `${{...}}` template-literal "
                    f"placeholder near line {_pb_first_unbalanced_line}. The placeholder closes before its "
                    f"parens balance — esbuild will fail with 'Expected \")\" but found \"}}\"'. "
                    f"Common cause: `Math.max(...arr.map(d => ...)).toFixed(N)` missing the outer Math.max close paren. "
                    f"Regenerate the affected component."
                )
        except Exception:
            # Lexer is best-effort — never crash the gate over scanner edge cases.
            pass

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
            _ul_last_sig = ''
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
                    # Skip JS/TS regex literals so backticks/quotes inside them
                    # (e.g. /`([^`]*)`/g) never toggle template/string state.
                    if _ul_ch == '/' and (_ul_last_sig == '' or _ul_last_sig in _REGEX_PREV_CHARS):
                        _ul_re_end = _scan_regex_literal_end(_ul_line, _ul_i)
                        if _ul_re_end is not None:
                            _ul_i = _ul_re_end
                            _ul_last_sig = '/'
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
                if not _ul_ch.isspace():
                    _ul_last_sig = _ul_ch
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

        # TEMPLATE-LITERAL PARITY CHECK: count unescaped backticks outside
        # strings and comments. An odd parity means a backtick was opened but
        # never closed — esbuild then mis-parses subsequent template literals
        # as TS ternary expressions ("Expected ':' but found '{'") far from
        # the true source line. Root cause is typically a stray triple-fence
        # ``` left behind by an LLM that produced markdown around its code.
        _tp_in_sq = False
        _tp_in_dq = False
        _tp_in_blk = False
        _tp_in_line = False
        _tp_in_tpl = False
        _tp_tpl_count = 0
        _tp_first_open_line = -1
        _tp_lines = tsx_content.splitlines()
        for _tp_ln, _tp_line in enumerate(_tp_lines, 1):
            _tp_in_line = False
            # Single/double-quote string state MUST reset per line: JS/TS string
            # literals cannot contain a raw newline, so an unbalanced quote is
            # confined to its own line. Carrying _tp_in_sq/_tp_in_dq across lines
            # let a lone apostrophe in JSX text (e.g. <div>It's clear</div>) poison
            # quote parity for the ENTIRE file, which then mis-counts every real
            # backtick after it and emits a phantom unterminated-template error.
            # Block-comment (_tp_in_blk) and template-literal (_tp_in_tpl) state
            # legitimately span lines and are intentionally NOT reset here.
            _tp_in_sq = False
            _tp_in_dq = False
            _tp_last_sig = ''
            _tp_i = 0
            while _tp_i < len(_tp_line):
                _tp_c = _tp_line[_tp_i]
                if _tp_in_blk:
                    if _tp_line[_tp_i:_tp_i + 2] == '*/':
                        _tp_in_blk = False; _tp_i += 2; continue
                    _tp_i += 1; continue
                if _tp_in_line:
                    _tp_i += 1; continue
                if not _tp_in_sq and not _tp_in_dq and not _tp_in_tpl:
                    if _tp_line[_tp_i:_tp_i + 2] == '//':
                        _tp_in_line = True; _tp_i += 2; continue
                    if _tp_line[_tp_i:_tp_i + 2] == '/*':
                        _tp_in_blk = True; _tp_i += 2; continue
                    # Skip regex literals so backticks inside them (e.g.
                    # /`([^`]*)`/g) are not counted as template-literal fences.
                    if _tp_c == '/' and (_tp_last_sig == '' or _tp_last_sig in _REGEX_PREV_CHARS):
                        _tp_re_end = _scan_regex_literal_end(_tp_line, _tp_i)
                        if _tp_re_end is not None:
                            _tp_i = _tp_re_end; _tp_last_sig = '/'; continue
                if _tp_c == '\\' and (_tp_in_sq or _tp_in_dq or _tp_in_tpl):
                    _tp_i += 2; continue
                if _tp_in_sq:
                    if _tp_c == "'": _tp_in_sq = False
                    _tp_i += 1; continue
                if _tp_in_dq:
                    if _tp_c == '"': _tp_in_dq = False
                    _tp_i += 1; continue
                if _tp_c == '`':
                    if not _tp_in_tpl:
                        _tp_in_tpl = True
                        _tp_tpl_count += 1
                        if _tp_first_open_line < 0:
                            _tp_first_open_line = _tp_ln
                    else:
                        _tp_in_tpl = False
                    _tp_i += 1; continue
                if _tp_in_tpl:
                    _tp_i += 1; continue
                if _tp_c == "'":
                    _tp_in_sq = True; _tp_i += 1; continue
                if _tp_c == '"':
                    _tp_in_dq = True; _tp_i += 1; continue
                if not _tp_c.isspace():
                    _tp_last_sig = _tp_c
                _tp_i += 1
        if _tp_in_tpl:
            # JSX-TEXT BACKTICK FALSE-POSITIVE GUARD: the scanner above is NOT
            # JSX-aware. A literal backtick character that appears as JSX text
            # content (between JSX tags) is counted as a template-literal
            # opener, but esbuild treats it as plain JSX text. If the file ends
            # in a complete top-level statement (e.g. `createRoot(...).render(...);`)
            # the parity miscount is a JSX false-positive — flagging it makes
            # the repair pipeline blindly append a backtick at EOF that
            # esbuild then rejects as 'Unterminated string literal' (the very
            # bug this check was meant to prevent).
            _tp_trailing = tsx_content.rstrip()
            _tp_last_stmt_ok = bool(
                re.search(r'(?:\)|\}|;|>)\s*$', _tp_trailing)
                and not re.search(r'`\s*$', _tp_trailing)
            )
            if not _tp_last_stmt_ok:
                errors.append(
                    f"SYNTAX_ERROR: index.tsx has an unclosed template literal — backtick opened (first unclosed near line {_tp_first_open_line}) but never closed. "
                    f"esbuild will mis-parse downstream template literals as TypeScript ternaries (\"Expected ':' but found '{{'\") thousands of lines later. "
                    f"Strip any stray markdown ``` fences and re-balance backticks."
                )

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
        # Key on (METHOD, path): FastAPI dispatches per (method, path) pair, so
        # `@router.get("/items")` and `@router.post("/items")` are BOTH valid and
        # must NOT be flagged as duplicates. Keying on path alone produced a false
        # CONTRACT_ERROR for every REST resource that exposes GET + POST/PUT/DELETE
        # on the same path — a routine, correct pattern.
        _route_pairs = _re_proxy.findall(r'@router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', app_py)
        _seen_pairs = {}
        for _rm, _rp in _route_pairs:
            _key = (_rm.lower(), _rp)
            if _key in _seen_pairs:
                errors.append(
                    f"CONTRACT_ERROR: app.py defines duplicate route path '{_rp}' for method {_rm.upper()}. "
                    f"FastAPI registers only the first occurrence — all others are silently ignored, "
                    f"causing incorrect responses. Each (method, path) pair must be unique."
                )
                break
            _seen_pairs[_key] = True

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
            # Extract fetch('/api/MODULE/path') URLs by searching specifically
            # for fetch( string ) call sites in the original tsx. This avoids the
            # previous approach of stripping JS regex literals first, which
            # accidentally destroyed URL path segments like /api/ and /ocean/climate
            # because the regex literal pattern /token/ matched URL segments too —
            # causing orphan fetches to go undetected and survive as runtime 404s.
            for _fm in _re_proxy.finditer(
                r"""fetch\s*\(\s*[`'"]([^`'"]+)[`'"]""",
                _original_tsx,
            ):
                _url = _fm.group(1)
                _api_m = _re_proxy.match(r'/api/[^/]+/(.+)', _url)
                if not _api_m:
                    continue
                _raw = _api_m.group(1).split("?")[0].rstrip("/")
                # Hard-skip template placeholders and regex meta-chars.
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

            # -- ARRAY NULL SAFETY CHECK --------------------------------------
            # API routes can fail and return error payloads without expected
            # array keys. When `setFooData(data)` replaces initial state
            # `{ items: [] }` with `{ error: '...' }`, any code accessing
            # `fooData.items.map(...)` without `?.` crashes: "Cannot read
            # properties of undefined (reading 'map')".
            # Pattern: word.word.(arrayMethod)( with no `?.` before the method.
            # The `(?<![?.])` lookbehind ensures we only flag expressions that
            # START at a fresh identifier (not mid-chain, not already optional).
            _unsafe_array_re = _re_proxy.compile(
                r'(?<![?.])\b\w+\.\w+\.(?:map|reduce|filter|forEach|slice|find|findIndex|some|every)\s*\(',
            )
            _unsafe_array_matches = _unsafe_array_re.findall(_tsx_raw)
            # Exclude legitimate false-positives: library method chains, prototype
            # calls, and expressions where the second word contains 'prototype',
            # 'length', 'toString', 'constructor' or is a capitalized class name.
            _safe_identifiers = {
                'prototype', 'length', 'toString', 'constructor', 'call', 'apply',
                'bind', 'name', 'type', 'key', 'value', 'props', 'state', 'ref',
            }
            _true_unsafe = [
                m for m in _unsafe_array_matches
                if not any(s in m.lower() for s in _safe_identifiers)
                and not _re_proxy.search(r'\b[A-Z][a-z]\w*\.', m)
            ]
            if len(_true_unsafe) >= 2:
                errors.append(
                    f"RULES_COMPLIANCE: ARRAY NULL SAFETY MANDATE violated — "
                    f"index.tsx contains {len(_true_unsafe)} array method call(s) on object "
                    f"properties without optional chaining: e.g. `{_true_unsafe[0].strip()}`. "
                    f"When an API route returns an error payload (missing the expected array key), "
                    f"`data.items.map(...)` crashes with 'Cannot read properties of undefined'. "
                    f"Fix: add `?.` before every array method call on state-derived properties: "
                    f"`data.items?.map(...)`, `data.items?.reduce(...)`, `data.items?.forEach(...)`. "
                    f"Per ARRAY NULL SAFETY MANDATE."
                )

            # -- HOOKS AFTER EARLY RETURN CHECK (React error #310) -----------
            # React rule: hooks must be called in the same order on EVERY render.
            # When a component has an early `return` BEFORE a hook call (useMemo,
            # useCallback, useRef, etc.), React calls a different number of hooks
            # on the first render vs subsequent renders → error #310
            # "Rendered more hooks than during the previous render."
            # Strategy: for each top-level *View component, scan the body for
            # early return statements (lines that are `return ...` NOT inside a
            # JSX block) that appear before any hook call.
            # Reliable detection requires accurate brace nesting, which is
            # impossible while string literals, template literals, comments, and
            # regex literals contribute stray '{','}','<','>' to the count — the
            # naive char scanner used previously drifted and produced FALSE
            # POSITIVES (e.g. flagging a `<React.useEffect` token embedded inside
            # returned JSX, or `return` statements inside a nested helper). A false
            # positive here is unsatisfiable by any repair and stalls the build
            # forever. We therefore (1) MASK out the contents of strings/templates/
            # comments so brace depth is exact, and (2) only flag a hook that is a
            # genuine STATEMENT (it begins its line, optionally as `const x = `) —
            # never a hook-looking token inside JSX (`<React.useEffect`) or a JSX
            # expression (`{useX()}`). High precision is the goal: a missed true
            # positive merely surfaces at runtime (status quo for a runtime error),
            # whereas a false positive blocks an otherwise-valid build.
            def _mask_code_for_scan(_s):
                _out = list(_s)
                _i = 0
                _n = len(_s)
                _state = None  # 'sq','dq','tpl','line','block'
                while _i < _n:
                    _c = _s[_i]
                    if _state is None:
                        if _c == '/' and _i + 1 < _n and _s[_i + 1] == '/':
                            _state = 'line'; _out[_i] = ' '; _out[_i + 1] = ' '; _i += 2; continue
                        if _c == '/' and _i + 1 < _n and _s[_i + 1] == '*':
                            _state = 'block'; _out[_i] = ' '; _out[_i + 1] = ' '; _i += 2; continue
                        if _c == "'":
                            _state = 'sq'; _out[_i] = ' '; _i += 1; continue
                        if _c == '"':
                            _state = 'dq'; _out[_i] = ' '; _i += 1; continue
                        if _c == '`':
                            _state = 'tpl'; _out[_i] = ' '; _i += 1; continue
                        _i += 1; continue
                    if _state == 'line':
                        if _c == '\n':
                            _state = None
                        else:
                            _out[_i] = ' '
                        _i += 1; continue
                    if _state == 'block':
                        if _c == '*' and _i + 1 < _n and _s[_i + 1] == '/':
                            _out[_i] = ' '; _out[_i + 1] = ' '; _state = None; _i += 2; continue
                        if _c != '\n':
                            _out[_i] = ' '
                        _i += 1; continue
                    # inside sq / dq / tpl
                    if _c == '\\' and _i + 1 < _n:
                        _out[_i] = ' '; _out[_i + 1] = ' '; _i += 2; continue
                    if (_state == 'sq' and _c == "'") or (_state == 'dq' and _c == '"') or (_state == 'tpl' and _c == '`'):
                        _out[_i] = ' '; _state = None; _i += 1; continue
                    if _c != '\n':
                        _out[_i] = ' '
                    _i += 1; continue
                return ''.join(_out)

            _hook_alt = (
                r'(?:useMemo|useCallback|useRef|useEffect|useState|useContext|'
                r'useReducer|useLayoutEffect|useImperativeHandle)'
            )
            _comp_decl_re = _re_proxy.compile(
                r'(?:const\s+\w+View\w*\s*(?::[^=]*)?\s*=\s*(?:async\s*)?\(\s*\)\s*=>\s*\{|'
                r'function\s+\w+View\w*\s*\([^)]*\)\s*\{)'
            )
            # A hook used as a STATEMENT: the (optionally assigned) hook call begins
            # the (lstripped) line. Rejects `<React.useEffect` and `{useX()}`.
            _hook_stmt_re = _re_proxy.compile(
                r'^(?:export\s+)?(?:(?:const|let|var)\s+[\w{}\[\],:\s]+=\s*)?'
                r'(?:await\s+)?(?:React\s*\.\s*)?' + _hook_alt + r'\s*[(<]'
            )
            _comp_name_re = _re_proxy.compile(r'(?:const|function)\s+(\w+)')
            _return_kw_re = _re_proxy.compile(r'\breturn\b')
            _masked_tsx = _mask_code_for_scan(_tsx_raw)
            _masked_lines = _masked_tsx.split('\n')
            _orig_lines = _tsx_raw.split('\n')
            _early_return_violations = []
            for _hm in _comp_decl_re.finditer(_masked_tsx):
                _hbody_start = _hm.end()
                # Walk the masked body recording brace depth at each line start.
                _h_depth = 1
                _h_pos = _hbody_start
                _hn = len(_masked_tsx)
                _cur_line = _masked_tsx.count('\n', 0, _hbody_start)
                _line_start_depth = {_cur_line: 1}
                while _h_pos < _hn and _h_depth > 0:
                    _hc = _masked_tsx[_h_pos]
                    if _hc == '{':
                        _h_depth += 1
                    elif _hc == '}':
                        _h_depth -= 1
                        if _h_depth == 0:
                            break
                    elif _hc == '\n':
                        _line_start_depth[_cur_line + 1] = _h_depth
                        _cur_line += 1
                    _h_pos += 1
                _start_line = _masked_tsx.count('\n', 0, _hbody_start)
                _end_line = _masked_tsx.count('\n', 0, _h_pos)
                _h_first_return_line = None
                _h_first_hook_after_return = None
                for _ln in range(_start_line, _end_line + 1):
                    if _line_start_depth.get(_ln) != 1:
                        continue
                    _mline = _masked_lines[_ln] if _ln < len(_masked_lines) else ''
                    if _h_first_return_line is None:
                        if _return_kw_re.search(_mline):
                            _h_first_return_line = _ln
                        continue
                    if _ln > _h_first_return_line and _hook_stmt_re.match(_mline.lstrip()):
                        _hk = _hook_stmt_re.search(_mline.lstrip())
                        _h_first_hook_after_return = _re_proxy.search(_hook_alt, _hk.group(0)).group(0)
                        break
                if _h_first_hook_after_return:
                    _cn_m = _comp_name_re.search(_tsx_raw[_hm.start():_hm.end()])
                    _comp_name = _cn_m.group(1) if _cn_m else "component"
                    _early_return_violations.append(f"{_comp_name}: `{_h_first_hook_after_return}` called after early return")
            if _early_return_violations:
                errors.append(
                    f"RULES_COMPLIANCE: HOOKS AFTER EARLY RETURN MANDATE violated — "
                    f"{len(_early_return_violations)} component(s) call React hook(s) AFTER an early return statement. "
                    f"React requires hooks to be called in the same order on every render. "
                    f"Violations: {'; '.join(_early_return_violations[:3])}. "
                    f"Fix: move ALL hook declarations (useMemo, useCallback, useRef, useEffect, useState) "
                    f"to the TOP of the component body, BEFORE any conditional return or early return. "
                    f"Per HOOKS AFTER EARLY RETURN MANDATE."
                )

            # -- EXTERNAL VALIDATION RULES (validation_rules.json) ------------
            # Module-specific route names, variable identifiers, and feature
            # trigger strings live in resources/validation_rules.json — NOT here.
            # This call applies all JSON-defined checks generically.
            self._run_validation_rules(_app_py, _tsx_raw, errors)

            # -- CALL_LLM_ASYNC MODULE-LEVEL IMPORT CHECK ----------------------
            # The LLM generates call_llm_async() calls in route function bodies
            # but often omits the top-level import, relying on inline per-function
            # imports inside SOME functions. Functions that call call_llm_async()
            # without a preceding local import raise NameError at runtime, which
            # is caught by the route's except block and silently returns the generic
            # "Service temporarily unavailable" zero-data fallback. Entire data pages
            # appear broken with all values at 0 when the APIs themselves succeed.
            # The PRE-GATE AUTO-FIX injects the import; this gate is the safety net.
            if "call_llm_async" in _app_py:
                if not _re_proxy.search(
                    r'^from\s+core\.llm_client\s+import\s+call_llm_async',
                    _app_py,
                    _re_proxy.MULTILINE
                ):
                    errors.append(
                        "DATA_ERROR: CALL_LLM_ASYNC IMPORT MANDATE violated — app.py calls "
                        "call_llm_async() in one or more route function bodies but has no "
                        "module-level 'from core.llm_client import call_llm_async'. "
                        "Functions with the inline import work; functions without it raise "
                        "NameError at runtime, which the except block catches and returns "
                        "'Service temporarily unavailable' with all-zero data. "
                        "Fix: add 'from core.llm_client import call_llm_async' at the TOP of "
                        "app.py (after the standard imports, before router = APIRouter()). "
                        "Per CALL_LLM_ASYNC IMPORT MANDATE."
                    )

            # -- JSX NATIVE BUILTIN COMPONENT USAGE CHECK ---------------------
            # Lucide icons are aliased (e.g. MapIcon) but LLMs still write <Map>
            # in JSX, which refers to the native JS Map constructor — React tries
            # to call it as a function, causing "Constructor Map requires 'new'".
            # Detect any bare native builtin name used as a JSX opening tag when
            # it is NOT imported from an icon library under that exact name.
            _JSX_BUILTIN_TAGS = {
                "Map", "Set", "Symbol", "Error", "Event", "URL", "Promise",
                "Date", "Array", "Object", "Function", "Number", "String",
                "Boolean", "Image", "Text", "Comment", "Range", "Screen",
                "Selection", "Navigation", "History", "Location", "Document",
                "Window", "Worker", "Request", "Response", "Headers",
                "FormData", "Blob", "File",
            }
            _icon_import_names = set()
            for _iim in _re_proxy.finditer(
                r"import\s*\{([^}]*)\}\s*from\s*['\"](?:lucide-react|@heroicons/react|react-icons/[^'\"]+|phosphor-react)['\"]",
                _tsx_raw
            ):
                for _iit in _re_proxy.finditer(r'\b(\w+)\s+as\s+(\w+)|\b(\w+)\s*[,}]', _iim.group(1)):
                    if _iit.group(2):
                        _icon_import_names.add(_iit.group(2))
                    elif _iit.group(3):
                        _icon_import_names.add(_iit.group(3))
            for _jbt in _JSX_BUILTIN_TAGS:
                if _jbt in _icon_import_names:
                    continue
                if _re_proxy.search(rf'<{_jbt}[\s/]', _tsx_raw):
                    errors.append(
                        f"RUNTIME_ERROR: index.tsx uses `<{_jbt}` as a JSX component but `{_jbt}` is "
                        f"the native JavaScript {_jbt} constructor — not a React component. "
                        f"React calls it as a function without `new`, causing 'Constructor {_jbt} requires "
                        f"'new'' at runtime and the ErrorBoundary catches the crash. "
                        f"Fix: if a {_jbt} icon is intended, import it with an alias: "
                        f"`import {{ {_jbt} as {_jbt}Icon }} from 'lucide-react'` and use `<{_jbt}Icon />`. "
                        f"If a JS {_jbt} data structure is needed, use `new {_jbt}()` (never as JSX). "
                        f"Per LUCIDE-REACT NATIVE CONSTRUCTOR SHADOW MANDATE."
                    )
                    break

            # -- SVG GROUP CSS HOVER SCALE CHECK ------------------------------
            # Applying Tailwind hover:scale-* on a <g> element inside <svg
            # viewBox> causes violent visual shaking on hover. CSS transforms
            # in the browser's pixel coordinate system conflict with the SVG
            # internal coordinate system — the element oscillates between
            # scaled and unscaled states at 60fps (seizure-like effect).
            # Fix: remove hover:scale-* from all SVG <g> elements and use
            # SVG-native stroke/opacity hover instead.
            _svg_g_hover_scale = _re_proxy.search(
                r'<g\b[^>]*className=["\'][^"\']*hover:scale-',
                _tsx_raw
            )
            if _svg_g_hover_scale:
                errors.append(
                    "UI_ERROR: index.tsx applies `hover:scale-*` (Tailwind CSS transform) to a `<g>` "
                    "element inside an SVG. CSS pixel-space transforms on SVG coordinate-space elements "
                    "cause violent visual oscillation (seizure-like shaking) on hover — the element "
                    "rapidly alternates between scaled and unscaled positions at 60fps because the "
                    "CSS layout engine and SVG coordinate system fight each other. "
                    "Fix: remove ALL `hover:scale-*` and `transition-transform` classes from `<g>` "
                    "elements. Use SVG-native hover instead: on mouseEnter set a React state flag "
                    "and conditionally change `stroke` color or `opacity` on the `<circle>`. "
                    "FORBIDDEN: Tailwind scale/transform classes on any SVG `<g>`, `<circle>`, "
                    "`<rect>`, or `<path>` element. Per SVG GROUP HOVER SCALE MANDATE."
                )

            # -- TRIPLE SEMICOLON IMPORT ARTIFACT CHECK -----------------------
            # The deterministic import injector occasionally appends an extra `;`
            # after an existing statement, producing `from 'lib';;;`. While
            # harmless at runtime, it indicates a broken injection pass that
            # may have left duplicate or malformed imports.
            if _re_proxy.search(r"from\s+['\"][^'\"]+['\"]\s*;{2,}", _tsx_raw):
                errors.append(
                    "SYNTAX_ERROR: index.tsx contains a triple (or double) semicolon after an import "
                    "statement (e.g. `from 'lucide-react';;;`). This is caused by the import injector "
                    "appending a `;` to a line that already ends with `;;`. While esbuild tolerates it, "
                    "it signals a malformed import injection pass that may have produced duplicate imports. "
                    "Fix: collapse all consecutive semicolons after import statements to a single `;`."
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
