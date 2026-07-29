import os
import subprocess
import shutil
import sys
import json
import re
import argparse
from pathlib import Path

# Configuration
BACKEND_DIR = Path(__file__).parent
MODULES_DIR = BACKEND_DIR / "modules"
FRONTEND_DIR = BACKEND_DIR / "frontend"
BUILD_DIR = BACKEND_DIR / "static" / "built"  # single live build directory
MANIFEST_PATH = BACKEND_DIR / "system_manifest.json"


def _strip_balanced_call(src, call_start):
    """Given src and the index of the 'a' in 'await NAME(' at call_start, return
    (await_start, end_index_after_close_paren) spanning the full `await NAME(...)`
    expression, with paren matching that is string/comment aware. Returns None if
    the parentheses never balance (malformed source — leave untouched)."""
    # Find the opening paren after the call name.
    open_paren = src.find("(", call_start)
    if open_paren == -1:
        return None
    i = open_paren
    depth = 0
    n = len(src)
    sq = dq = False
    tsq = tdq = False  # triple-quote states
    esc = False
    while i < n:
        ch = src[i]
        nx3 = src[i:i+3]
        if tsq:
            if nx3 == "'''":
                tsq = False
                i += 3
                continue
            i += 1
            continue
        if tdq:
            if nx3 == '"""':
                tdq = False
                i += 3
                continue
            i += 1
            continue
        if sq:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == "'":
                sq = False
            i += 1
            continue
        if dq:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                dq = False
            i += 1
            continue
        if ch == "#":
            # skip to end of line
            nl = src.find("\n", i)
            if nl == -1:
                return None
            i = nl
            continue
        if nx3 == "'''":
            tsq = True
            i += 3
            continue
        if nx3 == '"""':
            tdq = True
            i += 3
            continue
        if ch == "'":
            sq = True
            i += 1
            continue
        if ch == '"':
            dq = True
            i += 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return (call_start, i + 1)
        i += 1
    return None


def _find_safe_llm_helper_span(src):
    """Return the (start, end) char span of the `_safe_call_llm` helper definition, or
    None. This helper is the ONE legitimate place an LLM await lives outside an AI route
    (its body wraps the raw client and is what AI-button routes call); the data-route
    scrub MUST NOT touch it or every AI button would also be neutralized. The helper is
    frequently emitted in the MIDDLE of the file (sandwiched between two route blocks),
    so a naive per-route-block scrub would clobber it — hence we locate it explicitly and
    exclude its span. The body ends at the first following line that starts at column 0
    (the next top-level statement / decorator), skipping blank lines."""
    m = re.search(r'^[ \t]*async\s+def\s+_safe_call_llm\b', src, re.MULTILINE)
    if not m:
        return None
    start = m.start()
    nl = src.find("\n", start)
    if nl == -1:
        return (start, len(src))
    # First newline followed immediately by a non-whitespace char == a column-0 line.
    em = re.compile(r'\n(?=\S)').search(src, nl + 1)
    end = (em.start() + 1) if em else len(src)
    return (start, end)


def scrub_llm_from_data_routes(src):
    """GENERIC, SPEC-DRIVEN SELF-HEALING (no module specifics):

    The platform contract is explicit: the LLM (Qwen) is NEVER a chat model and is
    ONLY invoked as a tool when a user clicks an AI button. Despite this, the route
    generator routinely embeds blocking persona LLM call(s) (`await _safe_call_llm(...)`
    / `await call_llm_async(...)`) directly inside DATA routes (e.g. /weather/current,
    /ocean/current, /space/current, and worst of all /precursor/analysis which fans out
    SEVEN persona calls + a synthesis call). Each such call blocks the HTTP request for
    the full model latency (15-90s+), so the frontend's primary fetch never resolves and
    the page is stuck on "Loading…"/"Awaiting…" forever — the exact runtime failure users
    see on every data page.

    Fix (deterministic, generic): split app.py into route regions by `@router.<verb>(...)`
    decorators. For every region whose PATH is NOT a dedicated AI-button route (path
    segment `ai`, or containing `explain`/`narrative`), neutralize any in-request LLM call
    by replacing the whole `await <llm_fn>(...)` expression with `{"text": ""}`. Callers do
    `.get('text', fallback)`, so they degrade to their existing fallback string while the
    real upstream-API data returns instantly. AI-button routes (/ai/explain,
    /ai/risk_narrative, etc.) keep their LLM calls untouched.

    The `_safe_call_llm` HELPER DEFINITION is explicitly located and excluded from the
    scrub even when it is emitted in the middle of a (non-AI) route region — neutralizing
    its body would silently break every AI button too. Works on absolute offsets and
    applies replacements back-to-front so indices stay valid. Idempotent.
    """
    if not src or "router" not in src:
        return src, 0
    llm_fns = ("_safe_call_llm", "call_llm_async", "_raw_call_llm_async")
    if not any(fn in src for fn in llm_fns):
        return src, 0

    decl_re = re.compile(r'@router\.(?:get|post|put|delete|patch)\(\s*[\'"]([^\'"]+)[\'"]', re.IGNORECASE)
    matches = list(decl_re.finditer(src))
    if not matches:
        return src, 0

    ai_re = re.compile(r'(^|/)ai(/|$)|explain|narrative', re.IGNORECASE)
    call_re = re.compile(r'await\s+(?:' + "|".join(re.escape(f) for f in llm_fns) + r')\s*\(')

    helper_span = _find_safe_llm_helper_span(src)

    # Non-AI route regions as absolute (start, end) spans.
    regions = []
    for idx, m in enumerate(matches):
        start = m.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(src)
        if not ai_re.search(m.group(1)):
            regions.append((start, end))

    # Collect every LLM-call span to neutralize (absolute), skipping the helper body.
    spans = []
    for (rstart, rend) in regions:
        pos = rstart
        guard = 0
        while guard < 500:
            guard += 1
            cm = call_re.search(src, pos, rend)
            if not cm:
                break
            sp = _strip_balanced_call(src, cm.start())
            if not sp:
                pos = cm.end()
                continue
            a, b = sp
            pos = b
            if helper_span and not (b <= helper_span[0] or a >= helper_span[1]):
                # Call lies inside the _safe_call_llm helper — preserve it.
                continue
            spans.append((a, b))

    if not spans:
        return src, 0

    spans.sort()
    out = src
    for (a, b) in reversed(spans):
        out = out[:a] + '{"text": ""}' + out[b:]
    return out, len(spans)


_CONT_KEYWORD_RE = re.compile(r'Unexpected "(catch|finally|else)"', re.IGNORECASE)
_ESB_LOC_RE = re.compile(r'index\.(?:tsx|ts|js):(\d+):(\d+)')


def repair_unexpected_continuation(entry_path, esbuild_output):
    """GENERIC, DETERMINISTIC esbuild self-heal for the 'missing }' family the
    generation-time net-count auto-closer cannot fix.

    The component generator's brace auto-closer (see llm_router.py) only balances the
    NET { vs } count by APPENDING `}` at the END of a component. When a `}` is dropped in
    the MIDDLE of a block (e.g. an `if (...) { ... }` body whose closing brace is omitted
    right before the next sibling statement), appending at the end keeps the count looking
    balanced but leaves the STRUCTURE broken: a later `}` closes the inner block instead of
    the enclosing one, and esbuild stops at the next try/catch/finally/else continuation
    keyword with `Unexpected "catch"` (or "finally"/"else"). No existing handler repairs
    this class, and esbuild ran with no retry, so the failure reached integration with no
    chance to self-heal.

    Strategy (module-agnostic): esbuild pinpoints `index.tsx:LINE:COL` of the offending
    continuation keyword. The block immediately before it is missing exactly one closing
    `}`, so insert a single `}` line right before the offending line. Guarded by the file's
    net brace surplus — we only ADD a `}` while the file has more `{` than `}` (net > 0),
    so a wrong diagnosis can never spiral into runaway brace insertion. Returns True if the
    file was modified (caller should re-run esbuild)."""
    if not esbuild_output or not _CONT_KEYWORD_RE.search(esbuild_output):
        return False
    m = _ESB_LOC_RE.search(esbuild_output)
    if not m:
        return False
    line_no = int(m.group(1))
    try:
        src = entry_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False
    # Only ever ADD a closing brace when the file is genuinely short of them.
    if src.count('{') - src.count('}') <= 0:
        return False
    lines = src.splitlines(keepends=True)
    idx = line_no - 1
    if idx < 1 or idx >= len(lines):
        return False
    offending = lines[idx]
    indent = offending[:len(offending) - len(offending.lstrip())]
    eol = "\n" if (not offending or offending.endswith("\n")) else ""
    lines.insert(idx, f"{indent}}}{eol}")
    new_src = "".join(lines)
    if new_src == src:
        return False
    try:
        entry_path.write_text(new_src, encoding="utf-8")
    except Exception:
        return False
    return True


_TWO_TAG_MISMATCH_RE = re.compile(
    r'Unexpected closing\s+["\']?(\w+)["\']?\s+tag\s+does\s+not\s+match\s+opening\s+["\']?(\w+)["\']?\s+tag',
    re.IGNORECASE
)


def repair_tag_mismatch(entry_path, esbuild_output):
    """GENERIC, DETERMINISTIC esbuild self-heal for mismatched JSX tags."""
    if not esbuild_output:
        return False
    mismatches = _TWO_TAG_MISMATCH_RE.findall(esbuild_output)
    if not mismatches:
        return False
    loc_m = _ESB_LOC_RE.search(esbuild_output)
    if not loc_m:
        return False
    line_no = int(loc_m.group(1))
    col_no = int(loc_m.group(2))
    try:
        src = entry_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False
    lines = src.splitlines(keepends=True)
    idx = line_no - 1
    if idx < 0 or idx >= len(lines):
        return False
    line = lines[idx]
    changed = False
    for _close_name, _open_name in mismatches:
        _closer = '</>' if _close_name.lower() == 'fragment' else f'</{_close_name}>'
        _close_tag = f'</{_open_name}>'
        _ci = line.find(_closer, max(0, col_no - 10))
        if _ci >= 0:
            line = line[:_ci] + _close_tag + line[_ci:]
            lines[idx] = line
            changed = True
            break
    if not changed:
        return False
    new_src = "".join(lines)
    try:
        entry_path.write_text(new_src, encoding="utf-8")
        return True
    except Exception:
        return False


def scrub_trailing_markdown(src):
    """GENERIC, ALWAYS-SAFE trailing markdown scrubber.

    Qwen/LLMs often append markdown notes, summaries, or tables after the actual
    code in both TSX/TS and Python files (e.g. `---`, `**BUILD PLAN SUMMARY**`, etc.).
    This function locates these trailing blocks and truncates them, returning
    the cleaned code and a boolean indicating if changes were made.
    """
    if not src:
        return src, False
    m = re.search(r'\n(?:---|===|\*\*(?:BUILD PLAN|CONVERGENCE|DECISION|NOTES|SUMMARY)\b|#+\s+(?:BUILD PLAN|CONVERGENCE)\b)', src, re.IGNORECASE)
    if m:
        return src[:m.start()], True
    return src, False


_IMPORT_LINE_RE = re.compile(r'^(?:import\s+\S|from\s+\S+\s+import\s+\S)')
_ROUTER_DEF_RE = re.compile(r'^router\s*=\s*APIRouter\s*\(')
# (use-pattern, import-statement-to-add, already-imported-pattern). Only ever ADDS a
# module-level stdlib import when the name is genuinely referenced but never imported, so
# it can never shadow or remove anything the module already has.
# The "already-imported" pattern is anchored at column 0 (re.M) ON PURPOSE: an import that
# only appears INDENTED inside one function is scoped to that function and does NOT cover the
# other route handlers, so a module-level import must still be added.
_STDLIB_IMPORT_HINTS = [
    (re.compile(r'\bdatetime\b'),
     'from datetime import datetime, timedelta, timezone',
     re.compile(r'^(?:import[ \t]+datetime\b|from[ \t]+datetime[ \t]+import\b)', re.M)),
    (re.compile(r'\bmath\.'), 'import math', re.compile(r'^import[ \t]+math\b', re.M)),
    (re.compile(r'\bjson\.'), 'import json', re.compile(r'^import[ \t]+json\b', re.M)),
    (re.compile(r'\brandom\.'), 'import random', re.compile(r'^import[ \t]+random\b', re.M)),
    (re.compile(r'(?<![\w.])time\.'), 'import time', re.compile(r'^import[ \t]+time\b', re.M)),
]


def normalize_app_py_preamble(src):
    """GENERIC, ALWAYS-SAFE self-heal for a module app.py assembled by the DOMAIN ASSEMBLY
    route-merge (see llm_router.py PHASE B). That merge concatenates each domain's raw Qwen
    route text verbatim, so when one domain's output carries its own module preamble (a second
    `import` header and/or a second `router = APIRouter()` line) the merged file ends up with:

      1. A DUPLICATE `router = APIRouter()` mid-file. Python rebinds `router` at that point, so
         every `@router.<verb>` defined BEFORE it stays on the original router object while the
         ones AFTER it attach to the new object. Only one `router` is exported, so an entire
         band of routes silently vanishes -> the frontend's fetch() to them returns 404 and the
         view shows "no data". (This is the exact cause of the "N routes 404" render report.)
      2. MISSING imports. The canonical header only has what the base app.py declared (os/httpx/
         asyncio/fastapi); domains that use `datetime` (hourly/daily/seismic/ocean/astronomy),
         `math`, etc. never get those names imported, so every such route raises NameError, is
         swallowed by its broad `try/except`, and returns its zero/empty fallback with HTTP 200
         -> pervasive "0.0 / no data" across pages even though the route IS registered.

    Both are structural, never-valid-anyway conditions, so the fix is module-agnostic:
      - Keep only the FIRST module-level `router = APIRouter()`; drop any later duplicates so all
        routes register on the single exported router.
      - De-duplicate identical module-level import lines (collapses the spliced second header).
      - Add any missing stdlib import whose name is actually referenced (datetime/math/json/
        random/time) — only ADDED, never removed.

    Only column-0 (module-level) statements are touched; imports indented inside functions are
    left alone. Returns (new_src, changed)."""
    lines = src.splitlines(keepends=True)
    seen_imports = set()
    seen_router_def = False
    out = []
    changed = False
    for ln in lines:
        bare = ln.rstrip("\r\n")
        if _ROUTER_DEF_RE.match(bare):
            if seen_router_def:
                changed = True
                continue
            seen_router_def = True
            out.append(ln)
            continue
        if _IMPORT_LINE_RE.match(bare):
            key = bare.strip()
            if key in seen_imports:
                changed = True
                continue
            seen_imports.add(key)
            out.append(ln)
            continue
        out.append(ln)
    new_src = "".join(out)

    inserts = []
    for use_re, imp_stmt, have_re in _STDLIB_IMPORT_HINTS:
        if use_re.search(new_src) and not have_re.search(new_src):
            inserts.append(imp_stmt)
    if inserts:
        changed = True
        nl = new_src.splitlines(keepends=True)
        # Place the added module-level imports in the top header: just before the first
        # `router = APIRouter()` if present (guarantees they precede every route), else
        # after the first top-of-file import line, else at the very top.
        insert_at = None
        for i, l in enumerate(nl):
            if _ROUTER_DEF_RE.match(l.rstrip("\r\n")):
                insert_at = i
                break
        if insert_at is None:
            insert_at = 0
            for i, l in enumerate(nl):
                if _IMPORT_LINE_RE.match(l.rstrip("\r\n")):
                    insert_at = i + 1
                    break
        block = "".join(s + "\n" for s in inserts)
        nl.insert(insert_at, block)
        new_src = "".join(nl)
    return new_src, changed


def run_command(cmd, cwd=None, env=None):
    """Runs a shell command and ensures output is visible to avoid hangs."""
    try:
        current_env = os.environ.copy()
        if env:
            current_env.update(env)
        
        # HIDE CMD WINDOW on Windows to prevent flashing screens
        creation_flags = 0
        if os.name == 'nt':
            # CREATE_NO_WINDOW = 0x08000000
            creation_flags = 0x08000000
        
        # Use sys.stdout/stderr to ensure output is not buffered/piped in a way that hangs
        subprocess.run(
            cmd,
            shell=True,
            check=True,
            stdout=sys.stdout,
            stderr=sys.stderr,
            cwd=cwd,
            env=current_env,
            creationflags=creation_flags
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        return False


def load_manifest():
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load system_manifest.json: {e}")
        return {}


def build_chat_bubble_html(personas: list) -> str:
    personas_json = json.dumps(personas)
    return f"""
<!-- Module Chat Bubble — injected by build.py -->
<div id="__nb_chat_root__" style="position:fixed;bottom:24px;right:24px;z-index:99999;font-family:'Inter',sans-serif;font-size:14px">
  <button id="__nb_chat_toggle__" title="Open Module Chat" style="width:56px;height:56px;border-radius:50%;background:#6366f1;color:#fff;border:none;box-shadow:0 4px 16px rgba(0,0,0,0.3);cursor:pointer;font-size:22px;display:flex;align-items:center;justify-content:center;transition:transform .2s">💬</button>
  <div id="__nb_chat_window__" style="display:none;position:absolute;bottom:68px;right:0;width:370px;height:560px;background:#0f172a;border-radius:14px;box-shadow:0 12px 40px rgba(0,0,0,0.5);flex-direction:column;overflow:hidden;border:1px solid #1e293b">
    <div style="padding:10px 14px;background:#1e293b;display:flex;align-items:center;gap:8px;border-bottom:1px solid #334155">
      <span style="flex:1;font-weight:600;color:#e2e8f0;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" id="__nb_chat_persona_label__">Select a Persona</span>
      <select id="__nb_chat_persona_select__" style="background:#0f172a;color:#94a3b8;border:1px solid #334155;border-radius:6px;padding:3px 6px;font-size:11px;cursor:pointer;max-width:140px"></select>
    </div>
    <div id="__nb_chat_messages__" style="flex:1;padding:12px;overflow-y:auto;display:flex;flex-direction:column;gap:10px;background:#0f172a"></div>
    <div id="__nb_staging__" style="display:none;padding:5px 12px;border-top:1px solid #1e293b;flex-wrap:wrap;gap:5px;background:#0a0f1e"></div>
    <div style="padding:8px 10px;border-top:1px solid #1e293b;display:flex;gap:6px;align-items:center;background:#0a0f1e">
      <input type="file" id="__nb_file_input__" multiple style="display:none" />
      <button id="__nb_attach_btn__" title="Attach files" style="background:none;border:none;cursor:pointer;font-size:18px;color:#94a3b8;padding:2px 4px;flex-shrink:0">📎</button>
      <input id="__nb_chat_input__" type="text" placeholder="Ask this persona..." style="flex:1;padding:7px 11px;border-radius:20px;border:1px solid #334155;background:#1e293b;color:#e2e8f0;outline:none;font-size:12px" />
      <button id="__nb_chat_send__" style="padding:7px 13px;border-radius:20px;border:none;background:#6366f1;color:#fff;cursor:pointer;font-size:12px;font-weight:600;flex-shrink:0">Send</button>
    </div>
  </div>
</div>
<script>
(function() {{
  var personas = {personas_json};
  var SESSION_ID = 'session_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
  var isOpen = false;
  var isLoading = false;
  var stagedFiles = [];

  var TEXT_MIMES = new Set(['application/json','application/xml','application/javascript','application/x-python','application/x-sh','application/x-yaml','application/toml','application/csv']);
  function isTextMime(m) {{ return m.startsWith('text/') || TEXT_MIMES.has(m); }}

  var toggle = document.getElementById('__nb_chat_toggle__');
  var win = document.getElementById('__nb_chat_window__');
  var select = document.getElementById('__nb_chat_persona_select__');
  var label = document.getElementById('__nb_chat_persona_label__');
  var messages = document.getElementById('__nb_chat_messages__');
  var input = document.getElementById('__nb_chat_input__');
  var sendBtn = document.getElementById('__nb_chat_send__');
  var fileInput = document.getElementById('__nb_file_input__');
  var attachBtn = document.getElementById('__nb_attach_btn__');
  var staging = document.getElementById('__nb_staging__');

  personas.forEach(function(p) {{
    var opt = document.createElement('option');
    opt.value = p.id;
    opt.textContent = p.name;
    select.appendChild(opt);
  }});

  function getPersona() {{ return personas.find(function(p) {{ return p.id === select.value; }}) || personas[0]; }}

  function updateHeader() {{
    var p = getPersona();
    if (p) label.textContent = p.name + ' \u2014 ' + p.role;
  }}

  select.addEventListener('change', function() {{
    updateHeader();
    appendMsg('system', 'Switched to ' + getPersona().name + '.', []);
  }});
  updateHeader();
  appendMsg('system', 'Select a persona above and ask them anything. Attach any file type with \uD83D\uDCCE', []);

  toggle.addEventListener('click', function() {{
    isOpen = !isOpen;
    win.style.display = isOpen ? 'flex' : 'none';
    toggle.textContent = isOpen ? '\u2715' : '\uD83D\uDCAC';
  }});

  attachBtn.addEventListener('click', function() {{ fileInput.click(); }});
  fileInput.addEventListener('change', function() {{
    Array.from(fileInput.files).forEach(function(f) {{ stagedFiles.push(f); }});
    fileInput.value = '';
    renderStaging();
  }});

  function renderStaging() {{
    staging.style.display = stagedFiles.length ? 'flex' : 'none';
    staging.innerHTML = '';
    stagedFiles.forEach(function(f, i) {{
      var chip = document.createElement('div');
      chip.style.cssText = 'background:#1e293b;border:1px solid #334155;border-radius:4px;padding:2px 7px;font-size:10px;color:#94a3b8;display:flex;align-items:center;gap:4px;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap';
      chip.innerHTML = '\uD83D\uDCC4 ' + f.name + ' <span style="cursor:pointer;color:#64748b;margin-left:2px" data-idx="' + i + '">\u2715</span>';
      chip.querySelector('span').addEventListener('click', function() {{
        stagedFiles.splice(parseInt(this.dataset.idx), 1);
        renderStaging();
      }});
      staging.appendChild(chip);
    }});
  }}

  function readFile(file) {{
    return new Promise(function(resolve) {{
      var mime = file.type || 'application/octet-stream';
      var reader = new FileReader();
      if (isTextMime(mime)) {{
        reader.onloadend = function() {{ resolve({{ name: file.name, mimeType: mime, data: reader.result, isText: true }}); }};
        reader.readAsText(file);
      }} else {{
        reader.onloadend = function() {{
          var r = reader.result;
          var b64 = r.indexOf(',') > -1 ? r.split(',')[1] : r;
          resolve({{ name: file.name, mimeType: mime, data: b64, isText: false }});
        }};
        reader.readAsDataURL(file);
      }}
    }});
  }}

  function appendMsg(sender, text, attachments) {{
    var isUser = sender === 'user';
    var isSys = sender === 'system';
    var wrap = document.createElement('div');
    wrap.style.cssText = 'display:flex;flex-direction:column;align-items:' + (isUser ? 'flex-end' : 'flex-start');
    var bubble = document.createElement('div');
    bubble.style.cssText = 'max-width:88%;padding:8px 12px;border-radius:12px;word-break:break-word;white-space:pre-wrap;font-size:12px;line-height:1.5;' + (
      isSys  ? 'color:#475569;font-style:italic;font-size:10px' :
      isUser ? 'background:#6366f1;color:#fff' :
               'background:#1e293b;color:#e2e8f0;border:1px solid #334155'
    );
    bubble.textContent = text;
    if (!isSys) {{
      var meta = document.createElement('div');
      meta.style.cssText = 'font-size:9px;color:#475569;margin-top:2px';
      meta.textContent = isUser ? 'You' : getPersona().name;
      wrap.appendChild(bubble);
      wrap.appendChild(meta);
    }} else {{
      wrap.appendChild(bubble);
    }}
    if (attachments && attachments.length) {{
      var prev = document.createElement('div');
      prev.style.cssText = 'margin-top:5px;display:flex;flex-wrap:wrap;gap:5px';
      attachments.forEach(function(att) {{
        if (att.mimeType.startsWith('image/') && !att.isText) {{
          var img = document.createElement('img');
          img.src = 'data:' + att.mimeType + ';base64,' + att.data;
          img.style.cssText = 'max-width:180px;max-height:130px;border-radius:6px;border:1px solid #334155';
          prev.appendChild(img);
        }} else if (att.mimeType.startsWith('video/') && !att.isText) {{
          var vid = document.createElement('video');
          vid.src = 'data:' + att.mimeType + ';base64,' + att.data;
          vid.controls = true;
          vid.style.cssText = 'max-width:200px;border-radius:6px';
          prev.appendChild(vid);
        }} else {{
          var chip = document.createElement('span');
          chip.style.cssText = 'background:#1e293b;border:1px solid #334155;border-radius:4px;padding:2px 7px;font-size:10px;color:#94a3b8';
          chip.textContent = '\uD83D\uDCC4 ' + att.name;
          prev.appendChild(chip);
        }}
      }});
      wrap.appendChild(prev);
    }}
    messages.appendChild(wrap);
    messages.scrollTop = messages.scrollHeight;
  }}

  function appendThinking() {{
    var el = document.createElement('div');
    el.id = '__nb_thinking__';
    el.style.cssText = 'font-size:10px;color:#475569;font-style:italic;padding:3px 2px';
    el.textContent = getPersona().name + ' is thinking\u2026';
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
    return el;
  }}

  input.addEventListener('keydown', function(e) {{ if (e.key === 'Enter') sendMessage(); }});
  sendBtn.addEventListener('click', sendMessage);

  async function sendMessage() {{
    var text = input.value.trim();
    if ((!text && stagedFiles.length === 0) || isLoading) return;
    var p = getPersona();
    if (!p) return;
    var filesToSend = stagedFiles.slice();
    stagedFiles = [];
    renderStaging();
    input.value = '';
    isLoading = true;
    sendBtn.disabled = true;
    var attachments = await Promise.all(filesToSend.map(readFile));
    appendMsg('user', text || '(attachment only)', attachments);
    var thinking = appendThinking();
    try {{
      var pageCtx = '';
      try {{
        var pgTitle = document.title || '';
        var pgUrl = window.location.href || '';
        var pgText = (document.body ? document.body.innerText : '').replace(/\\s+/g, ' ').trim().slice(0, 2000);
        pageCtx = '[PAGE CONTEXT]\nTitle: ' + pgTitle + '\nURL: ' + pgUrl + '\nVisible Content: ' + pgText + '\n[/PAGE CONTEXT]\n\n';
      }} catch(e) {{}}
      var fullMessage = pageCtx + (text || '');
      var resp = await fetch(window.location.origin + '/api/chat/chat', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{ persona: p.id, message: fullMessage, attachments: attachments, session_id: SESSION_ID }})
      }});
      var data = await resp.json();
      thinking.remove();
      var reply = (data.response && typeof data.response === 'object')
        ? (data.response.text || JSON.stringify(data.response))
        : (data.response || data.message || JSON.stringify(data));
      appendMsg('persona', reply, []);
    }} catch(err) {{
      thinking.remove();
      appendMsg('system', 'Connection error: ' + err.message, []);
    }} finally {{
      isLoading = false;
      sendBtn.disabled = false;
    }}
  }}
}})();
</script>
"""


LEAFLET_CDN = '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="" />'
TAILWIND_CDN = '<script src="https://cdn.tailwindcss.com"></script>'

def inject_leaflet(html_path: Path):
    """Injects Leaflet CSS CDN if the module uses Leaflet."""
    try:
        content = html_path.read_text(encoding="utf-8", errors="replace")
        if "unpkg.com/leaflet" in content:
            return
        # Scan the JS bundle for leaflet usage to decide if we inject
        js_bundle = html_path.parent / "index.js"
        if js_bundle.exists():
            js_content = js_bundle.read_text(encoding="utf-8", errors="replace")
            if 'leaflet' in js_content.lower() or 'L.map' in js_content:
                content = re.sub(r'</head>', f"  {LEAFLET_CDN}\n</head>", content, count=1, flags=re.IGNORECASE)
                html_path.write_text(content, encoding="utf-8", errors="replace")
                print(f"    Injected Leaflet CSS CDN into {html_path.name}")
    except Exception as e:
        print(f"    WARNING: Could not inject Leaflet CSS into {html_path}: {e}")

def inject_tailwind(html_path: Path):
    """Ensures every module HTML has the Tailwind CDN script for proper class resolution."""
    try:
        content = html_path.read_text(encoding="utf-8", errors="replace")
        if "cdn.tailwindcss.com" in content:
            return
        content = re.sub(r'</head>', f"  {TAILWIND_CDN}\n</head>", content, count=1, flags=re.IGNORECASE)
        html_path.write_text(content, encoding="utf-8", errors="replace")
        print(f"    Injected Tailwind CDN into {html_path.name}")
    except Exception as e:
        print(f"    WARNING: Could not inject Tailwind CDN into {html_path}: {e}")


FULLSCREEN_FIX_STYLE = """<style>
html, body { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; }
#root { display: flex; flex-direction: column; width: 100%; height: 100%; }
#root > * { flex: 1 1 auto; width: 100%; min-height: 0; }
</style>"""

def inject_fullscreen_fix(html_path: Path):
    """Ensures the React root and its direct child fill the full viewport.
    
    Root cause: AI-generated App root divs use 'flex h-screen' but omit 'w-full'.
    Since #root is display:flex (row), children only expand in the cross-axis (height),
    not the main axis (width), leaving a dead zone on the right side of the screen.
    This injected style overrides that unconditionally for every module.
    """
    try:
        content = html_path.read_text(encoding="utf-8", errors="replace")
        if "__nb_fullscreen_fix__" in content:
            return
        marker = FULLSCREEN_FIX_STYLE.replace("<style>", '<style id="__nb_fullscreen_fix__">')
        content = re.sub(r'</head>', f"  {marker}\n</head>", content, count=1, flags=re.IGNORECASE)
        html_path.write_text(content, encoding="utf-8", errors="replace")
        print(f"    Injected fullscreen fix into {html_path.name}")
    except Exception as e:
        print(f"    WARNING: Could not inject fullscreen fix into {html_path}: {e}")


def inject_chat_bubble(html_path: Path, personas: list):
    try:
        content = html_path.read_text(encoding="utf-8", errors="replace")
        if "__nb_chat_root__" in content:
            return
        bubble = build_chat_bubble_html(personas)
        if re.search(r'</body>', content, re.IGNORECASE):
            content = re.sub(r'</body>', lambda _m: bubble + "\n</body>", content, count=1, flags=re.IGNORECASE)
        elif re.search(r'</html>', content, re.IGNORECASE):
            content = re.sub(r'</html>', lambda _m: bubble + "\n</html>", content, count=1, flags=re.IGNORECASE)
            print(f"    WARNING: {html_path.name} has no </body> tag — injected chat bubble before </html> instead.")
        else:
            content = content + "\n" + bubble
            print(f"    WARNING: {html_path.name} has no </body> or </html> tag — appended chat bubble to end of file.")
        html_path.write_text(content, encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"    WARNING: Could not inject chat bubble into {html_path}: {e}")


def build_modules(target_module: str = None):
    print(f"--- Starting Build Process {'(Target: ' + target_module + ')' if target_module else ''} ---")

    manifest = load_manifest()
    manifest_modules = manifest.get("modules", {})

    # 1. Prepare BUILD_DIR
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    (BUILD_DIR / "modules").mkdir(parents=True, exist_ok=True)

    # NODE_PATH: ensures esbuild resolves react-leaflet, recharts, lucide-react, etc.
    # from the shared frontend/node_modules regardless of where esbuild is invoked from.
    node_path_env = str(FRONTEND_DIR / "node_modules")

    # 2. Build Modules
    print("\nBuilding Modules...")
    failed_modules = []
    if MODULES_DIR.exists():
        modules_to_build = [target_module] if target_module else os.listdir(MODULES_DIR)
        
        for module_folder in modules_to_build:
            if module_folder == "node_modules" or not (MODULES_DIR / module_folder).is_dir():
                continue
            
            # MANDATE: Only build if module.json exists (Prevents race conditions with expansion engine)
            if not (MODULES_DIR / module_folder / "module.json").exists():
                print(f"  SKIPPING: {module_folder} (No module.json found)")
                continue
            
            print(f"  Processing: {module_folder}")
            target_dir = BUILD_DIR / "modules" / module_folder
            target_dir.mkdir(parents=True, exist_ok=True)
            module_path = MODULES_DIR / module_folder

            # Copy non-bundle files — exclude .env and source files that don't belong in public static
            _EXCLUDED_SUFFIXES = {".ts", ".tsx", ".py", ".db"}
            _EXCLUDED_NAMES = {".env", ".env.local", ".env.production"}
            for root_w, dirs_w, files_w in os.walk(module_path):
                rel_root = Path(root_w).relative_to(module_path)
                dest_root = target_dir / rel_root
                dest_root.mkdir(parents=True, exist_ok=True)
                for item in files_w:
                    source = Path(root_w) / item
                    if source.suffix.lower() not in _EXCLUDED_SUFFIXES and source.name not in _EXCLUDED_NAMES:
                        shutil.copy2(source, dest_root / item)

            # APP.PY SELF-HEALING SCRUB (generic, spec-driven, no module specifics):
            # Strip blocking in-request LLM calls out of DATA routes. The platform
            # contract requires the LLM be called ONLY from AI-button routes; when a
            # persona LLM call is wired into a data route it blocks the request for the
            # full model latency, so the frontend's primary fetch never resolves and the
            # page hangs on "Loading…" forever. This runs on every build (standalone
            # rebuild AND integration.py subprocess) so the on-disk app.py FastAPI loads
            # is always healed. See scrub_llm_from_data_routes() for the full rationale.
            _app_py_path = module_path / "app.py"
            if _app_py_path.exists():
                try:
                    _app_src = _app_py_path.read_text(encoding="utf-8", errors="replace")
                    _app_clean, _app_clean_changed = scrub_trailing_markdown(_app_src)
                    if _app_clean_changed:
                        _app_src = _app_clean
                        _app_py_path.write_text(_app_src, encoding="utf-8")
                        print(f"    app.py scrub: removed trailing markdown/prose notes.")
                    # PREAMBLE NORMALIZE (generic): collapse duplicate module preambles spliced
                    # in by the domain route-merge — drop the duplicate `router = APIRouter()`
                    # that orphans whole route bands into 404s, de-dupe imports, and add any
                    # referenced-but-unimported stdlib (datetime/math/...) so data routes stop
                    # silently NameError-ing into their zero/empty fallback. See
                    # normalize_app_py_preamble() for the full rationale.
                    _app_norm, _app_norm_changed = normalize_app_py_preamble(_app_src)
                    if _app_norm_changed and _app_norm != _app_src:
                        _app_src = _app_norm
                        _app_py_path.write_text(_app_src, encoding="utf-8")
                        print(f"    app.py preamble normalize: removed duplicate router/imports and/or added missing stdlib imports (fixes orphaned-route 404s and zero-data NameErrors).")
                    _app_healed, _app_n = scrub_llm_from_data_routes(_app_src)
                    if _app_n > 0 and _app_healed != _app_src:
                        _app_py_path.write_text(_app_healed, encoding="utf-8")
                        print(f"    app.py scrub: neutralized {_app_n} blocking LLM call(s) in data route(s) (LLM is reserved for AI-button routes; in-route calls hang the page).")
                except Exception as _app_e:
                    print(f"    WARNING: app.py LLM scrub skipped for {module_folder}: {_app_e}")

            # Bundle entry point
            entry = None
            for candidate in ["index.tsx", "index.ts", "index.js"]:
                if (module_path / candidate).exists():
                    entry = module_path / candidate
                    break
            
            if entry:
                # PRE-ESBUILD SELF-HEALING SCRUB (generic, always-safe, no module specifics):
                # esbuild is the single chokepoint every build path flows through — standalone
                # rebuilds, integration.py subprocess, and AI-pipeline integration alike. The
                # AI pipeline's deterministic JSX scrubs only ever touched its in-memory
                # merged_blob, so a corrupted source file already on disk (e.g. a stale artifact
                # from a build that failed before a fix existed) would re-fail forever on every
                # plain rebuild with no chance to self-heal. Apply the two corruption classes
                # that are *always* safe to rewrite — they are never valid TSX in any module:
                #   1. Numeric closing tags  </3>  -> </div>   (a tag name can't be a digit)
                #   2. Stray-token closing tags </<div> or </.div> -> </div>
                #      (a closing tag start `</` can only be followed by an identifier, `>`,
                #       or a member name — never `<` or `.`)
                # Member-component tags like </Foo.Bar> are untouched (the dot follows the name,
                # not `</`), and `{x.y}` expressions are untouched (no `</` prefix).
                if entry.suffix.lower() in (".tsx", ".ts"):
                    try:
                        _src_heal = entry.read_text(encoding="utf-8", errors="replace")
                        _orig_heal = _src_heal
                        _src_clean, _src_clean_changed = scrub_trailing_markdown(_src_heal)
                        if _src_clean_changed:
                            _src_heal = _src_clean
                        _num_fixes = len(re.findall(r'</\d+\s*>', _src_heal))
                        if _num_fixes:
                            _src_heal = re.sub(r'</\d+\s*>', '</div>', _src_heal)
                        _stray_fixes = len(re.findall(r'</[<.]+(?=[A-Za-z/>])', _src_heal))
                        if _stray_fixes:
                            _src_heal = re.sub(r'</[<.]+(?=[A-Za-z/>])', '</', _src_heal)
                        if _src_heal != _orig_heal:
                            entry.write_text(_src_heal, encoding="utf-8")
                            _msg = f"    Pre-esbuild scrub: healed"
                            if _src_clean_changed:
                                _msg += " trailing markdown notes +"
                            _msg += f" {_num_fixes} numeric + {_stray_fixes} stray-token closing tag(s) in {entry.name}"
                            print(_msg)
                    except Exception as _heal_e:
                        print(f"    WARNING: pre-esbuild scrub skipped for {entry.name}: {_heal_e}")
                out_file = target_dir / "index.js"
                print(f"    Bundling: {entry.name} -> index.js")
                esbuild_bin = FRONTEND_DIR / "node_modules" / ".bin" / "esbuild.cmd"
                if not esbuild_bin.exists():
                    esbuild_bin = FRONTEND_DIR / "node_modules" / ".bin" / "esbuild"
                esbuild_cmd = [
                    str(esbuild_bin),
                    entry.name,
                    f"--outfile={out_file}",
                    "--format=esm",
                    "--bundle",
                    "--platform=browser",
                    "--jsx=automatic",
                    '--define:process.env.NODE_ENV="production"',
                    "--loader:.png=dataurl",
                    "--loader:.jpg=dataurl",
                    "--loader:.jpeg=dataurl",
                    "--loader:.gif=dataurl",
                    "--loader:.svg=dataurl",
                    "--loader:.woff=dataurl",
                    "--loader:.woff2=dataurl",
                    "--loader:.ttf=dataurl",
                ]
                build_env = os.environ.copy()
                build_env["NODE_PATH"] = node_path_env
                try:
                    # esbuild self-heal retry loop. esbuild is the single chokepoint every
                    # build path flows through (standalone rebuild, integration.py subprocess,
                    # AI-pipeline integration), so structural defects the generation-time
                    # repairs miss are healed HERE, generically, before they ever reach
                    # integration as a hard failure. Currently heals the `Unexpected
                    # "catch"/"finally"/"else"` missing-`}` family (see
                    # repair_unexpected_continuation). Bounded; each pass inserts at most one
                    # `}` and only while the file is net-positive on braces.
                    _esb_repair_attempts = 0
                    while True:
                        result = subprocess.run(
                            esbuild_cmd,
                            cwd=str(module_path),
                            env=build_env,
                            capture_output=True,
                            text=True,
                            timeout=300,
                        )
                        if result.returncode == 0:
                            break
                        _esb_out = (result.stderr or "") + "\n" + (result.stdout or "")
                        if _esb_repair_attempts < 8 and repair_unexpected_continuation(entry, _esb_out):
                            _esb_repair_attempts += 1
                            print(f"    esbuild self-heal: inserted a missing closing brace before a continuation keyword (attempt {_esb_repair_attempts}); retrying esbuild...")
                            continue
                        if _esb_repair_attempts < 8 and repair_tag_mismatch(entry, _esb_out):
                            _esb_repair_attempts += 1
                            print(f"    esbuild self-heal: fixed tag mismatch (attempt {_esb_repair_attempts}); retrying esbuild...")
                            continue
                        break
                    # Always print full output so integration.py can surface real errors
                    if result.stdout:
                        print(result.stdout)
                    if result.stderr:
                        print(f"    esbuild output: {result.stderr}")
                    if result.returncode != 0:
                        print(f"    esbuild FAILED (rc={result.returncode}) for {module_folder}")
                        failed_modules.append(module_folder)
                        # Delete stale bundle — if old index.js remains, the module validator sees
                        # it as a "successful" build, mounts the module, and the old frontend JS
                        # hits routes from the NEW app.py that no longer exist → 404s everywhere.
                        if out_file.exists():
                            try:
                                out_file.unlink()
                                print(f"    Deleted stale bundle to prevent mismatched frontend/backend: {out_file}")
                            except Exception as _del_e:
                                print(f"    WARNING: Could not delete stale bundle {out_file}: {_del_e}")
                        continue
                    # Treat esbuild [duplicate-object-key] warnings as BUILD_ERROR.
                    # Covers duplicate style={{}} props (silent CSS discard) AND duplicate onClick/
                    # event-handler attributes (one handler silently dropped by the runtime).
                    # esbuild exits 0 but emits this warning — we must catch it and fail the build
                    # so the repair cycle can patch the source rather than silently deploying broken code.
                    _esbuild_stderr = (result.stderr or "") + (result.stdout or "")
                    if "[duplicate-object-key]" in _esbuild_stderr:
                        print(f"    esbuild BUILD_ERROR: [duplicate-object-key] warning detected in {module_folder} — duplicate JSX attribute (style/onClick/etc). Treating as build failure.")
                        failed_modules.append(module_folder)
                        if out_file.exists():
                            try:
                                out_file.unlink()
                                print(f"    Deleted bundle with duplicate-key defect: {out_file}")
                            except Exception as _del_e:
                                print(f"    WARNING: Could not delete defective bundle {out_file}: {_del_e}")
                        continue
                    elif not out_file.exists():
                        print(f"    esbuild exited 0 but {out_file} was NOT produced for {module_folder}")
                        failed_modules.append(module_folder)
                        continue
                    else:
                        print(f"    Bundle written: {out_file}")
                        # Rewrite script src from index.tsx/index.ts -> index.js in the built HTML.
                        # The source index.html always references the TS source file as the entry
                        # point, but the browser must load the compiled index.js bundle.  Without
                        # this rewrite the script tag 404s silently and the app renders blank.
                        _html_rewrite_path = target_dir / "index.html"
                        if _html_rewrite_path.exists():
                            _html_rw = _html_rewrite_path.read_text(encoding="utf-8", errors="replace")
                            _html_rw_orig = _html_rw
                            _html_rw = _html_rw.replace('src="index.tsx"', 'src="index.js"')
                            _html_rw = _html_rw.replace("src='index.tsx'", "src='index.js'")
                            _html_rw = _html_rw.replace('src="index.ts"', 'src="index.js"')
                            _html_rw = _html_rw.replace("src='index.ts'", "src='index.js'")
                            if _html_rw != _html_rw_orig:
                                _html_rewrite_path.write_text(_html_rw, encoding="utf-8", errors="replace")
                                print(f"    Rewrote script src index.tsx -> index.js in index.html")
                        css_out = target_dir / "index.css"
                        if css_out.exists():
                            html_out_path = target_dir / "index.html"
                            if html_out_path.exists():
                                html_src = html_out_path.read_text(encoding="utf-8", errors="replace")
                                if 'href="index.css"' not in html_src and "href='index.css'" not in html_src:
                                    html_src = html_src.replace("</head>", '  <link rel="stylesheet" href="index.css">\n</head>')
                                    html_out_path.write_text(html_src, encoding="utf-8", errors="replace")
                                    print(f"    Injected index.css link into index.html")
                except Exception as exc:
                    print(f"    esbuild exception: {exc}")
                    failed_modules.append(module_folder)
                    continue
            else:
                print(f"    SKIP: No entry point for {module_folder}")

            # Inject Tailwind CDN, styles.css link, and persona chat bubble into index.html
            html_out = target_dir / "index.html"
            if html_out.exists():
                # Ensure styles.css link is present (safety net if AI forgot to add it)
                styles_out = target_dir / "styles.css"
                if styles_out.exists():
                    html_src = html_out.read_text(encoding="utf-8", errors="replace")
                    if 'href="styles.css"' not in html_src and "href='styles.css'" not in html_src:
                        html_src = html_src.replace("</head>", '  <link rel="stylesheet" href="styles.css">\n</head>')
                        html_out.write_text(html_src, encoding="utf-8", errors="replace")
                        print(f"    Injected styles.css link into index.html")
                inject_tailwind(html_out)
                inject_leaflet(html_out)
                inject_fullscreen_fix(html_out)
                personas = manifest_modules.get(module_folder, {}).get("personas", [])
                if personas:
                    print(f"    Injecting chat bubble with {len(personas)} persona(s)...")
                    inject_chat_bubble(html_out, personas)
                else:
                    print(f"    SKIP chat bubble: no personas defined for {module_folder} in system_manifest.json")

    # 3. Inject Tailwind CDN and chat bubble into any already-built modules not rebuilt above
    print("\nChecking pre-built modules for Tailwind and chat bubble injection...")
    built_modules_dir = BUILD_DIR / "modules"
    if built_modules_dir.exists():
        for built_folder in built_modules_dir.iterdir():
            if not built_folder.is_dir():
                continue
            html_out = built_folder / "index.html"
            if html_out.exists():
                inject_tailwind(html_out)
                inject_leaflet(html_out)
                inject_fullscreen_fix(html_out)
                personas = manifest_modules.get(built_folder.name, {}).get("personas", [])
                if personas:
                    inject_chat_bubble(html_out, personas)

    print("\n--- Build Complete ---")
    if failed_modules:
        print(f"FAILED modules: {', '.join(failed_modules)}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", help="Specific module to build")
    args = parser.parse_args()
    build_modules(args.module)
