import os
import subprocess
import shutil
import sys
import json
import argparse
from pathlib import Path

# Configuration
BACKEND_DIR = Path(__file__).parent
MODULES_DIR = BACKEND_DIR / "modules"
FRONTEND_DIR = BACKEND_DIR / "frontend"
BUILD_DIR = BACKEND_DIR / "static" / "built"  # single live build directory
MANIFEST_PATH = BACKEND_DIR / "system_manifest.json"


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
      var resp = await fetch('http://127.0.0.1:8000/api/chat/chat', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{ persona: p.id, message: text, attachments: attachments, session_id: SESSION_ID }})
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
                content = content.replace("</head>", f"  {LEAFLET_CDN}\n</head>")
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
        content = content.replace("</head>", f"  {TAILWIND_CDN}\n</head>")
        html_path.write_text(content, encoding="utf-8", errors="replace")
        print(f"    Injected Tailwind CDN into {html_path.name}")
    except Exception as e:
        print(f"    WARNING: Could not inject Tailwind CDN into {html_path}: {e}")


def inject_chat_bubble(html_path: Path, personas: list):
    try:
        content = html_path.read_text(encoding="utf-8", errors="replace")
        if "__nb_chat_root__" in content:
            return
        bubble = build_chat_bubble_html(personas)
        content = content.replace("</body>", bubble + "\n</body>")
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

    # 1.5 Ensure node_modules junction for esbuild
    shared_nm = MODULES_DIR / "node_modules"
    source_nm = FRONTEND_DIR / "node_modules"
    
    if not shared_nm.exists() and source_nm.exists():
        import subprocess as _sp
        print(f"Attempting to create node_modules junction: {shared_nm} -> {source_nm}")
        # On Windows, mklink /J is preferred for node_modules
        if os.name == 'nt':
            _mklink_result = _sp.run(
                ['cmd', '/c', 'mklink', '/J', str(shared_nm), str(source_nm)],
                capture_output=True, text=True
            )
            if _mklink_result.returncode != 0:
                print(f"WARNING: node_modules junction failed (rc={_mklink_result.returncode}): {_mklink_result.stderr.strip()}")
                print("Falling back to NODE_PATH for module resolution.")
            else:
                print(f"SUCCESS: node_modules junction created.")
        else:
            # On Unix, use symbolic link
            try:
                os.symlink(source_nm, shared_nm, target_is_directory=True)
                print(f"SUCCESS: node_modules symlink created.")
            except Exception as e:
                print(f"WARNING: node_modules symlink failed: {e}")

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
            for item in os.listdir(module_path):
                source = module_path / item
                if source.is_file() and source.suffix.lower() not in _EXCLUDED_SUFFIXES and source.name not in _EXCLUDED_NAMES:
                    shutil.copy2(source, target_dir / item)

            # Bundle entry point
            entry = None
            for candidate in ["index.tsx", "index.ts", "index.js"]:
                if (module_path / candidate).exists():
                    entry = module_path / candidate
                    break
            
            if entry:
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
                    result = subprocess.run(
                        esbuild_cmd,
                        cwd=str(module_path),
                        env=build_env,
                        capture_output=True,
                        text=True,
                        timeout=300,
                    )
                    # Always print full output so integration.py can surface real errors
                    if result.stdout:
                        print(result.stdout)
                    if result.stderr:
                        print(f"    esbuild output: {result.stderr}")
                    if result.returncode != 0:
                        print(f"    esbuild FAILED (rc={result.returncode}) for {module_folder}")
                        failed_modules.append(module_folder)
                        continue
                    elif not out_file.exists():
                        print(f"    esbuild exited 0 but {out_file} was NOT produced for {module_folder}")
                        failed_modules.append(module_folder)
                        continue
                    else:
                        print(f"    Bundle written: {out_file}")
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
