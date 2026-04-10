import os
import re
import logging
import json
import asyncio
import importlib
from dotenv import load_dotenv

try:
    import psycopg2
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    psycopg2 = None
    _PSYCOPG2_AVAILABLE = False

# --- LOAD ENVIRONMENT VARIABLES FIRST ---
load_dotenv()

from fastapi import FastAPI, APIRouter
from starlette.routing import Mount
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from contextlib import asynccontextmanager

# --- CORE IMPORTS ---
from api.router import api_router
from core.integration_engine import run_discovery_and_registration, get_registry
from persona_manager import persona_manager
from persona_logger import narrate
from core.system_status import system_monitor
from core.repair_orchestrator import repair_orchestrator
from providers.local_qwen_provider import LocalQwenProvider

# --- INITIALIZE LOGGER ---
logger = logging.getLogger("SystemOrchestrator")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [CORE] %(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# --- GLOBAL STATE ---
MOUNTED_MODULES = set()
backend_dir = os.path.dirname(os.path.abspath(__file__))

# --- SYSTEM HANDLERS ---
async def refresh_system():
    """Triggers a full system re-scan and mount update."""
    narrate("Integrity Monitor", "API Refresh triggered. Re-syncing all modules and personas...")
    persona_manager.load_personas()
    run_discovery_and_registration()
    load_modules_from_registry()
    return {"status": "success", "active_modules": list(MOUNTED_MODULES)}

def create_fresh_api_app():
    """Creates a new FastAPI instance and populates it with fresh routes."""
    api_app = FastAPI()
    
    # 1. Add Base API Routes (System routes like /eliza/task)
    api_app.include_router(api_router)
    api_app.add_api_route("/system/refresh", refresh_system)
    
    # 2. Add Module Routers from Registry
    registry = get_registry()
    MOUNTED_MODULES.clear()
    
    for name, info in registry.items():
        if info.get("status") == "active":
            metadata = info.get("metadata", {})
            router = metadata.get("router") or (
                metadata.get("app") is not None and hasattr(metadata.get("app"), "router")
                and metadata["app"].router
            )
            
            if router:
                narrate("Integrity Monitor", f"Automatically mounting router for module '{name}' at /api/{name}")
                try:
                    # ALL module routers MUST be attached to api_app using include_router
                    api_app.include_router(router, prefix=f"/{name}", tags=[name])
                    MOUNTED_MODULES.add(name)
                    system_monitor.update_mount(name, success=True, log=f"Mounted at /api/{name}")
                    logger.info(f"Successfully mounted /api/{name}")
                except Exception as e:
                    logger.error(f"Failed to mount module {name}: {e}")
                    system_monitor.update_mount(name, success=False, log=f"Mount Error: {str(e)}")
            else:
                logger.warning(f"Module {name} has no valid router object in metadata.")
                system_monitor.update_mount(name, success=False, log="Missing Router Object")
    
    return api_app

def load_modules_from_registry():
    """Rebuilds the entire application mounting structure on the parent app."""
    # 1. Create a fresh api_app instance
    new_api_app = create_fresh_api_app()
    
    # 2. Identify decorator routes to preserve
    decorator_routes = [r for r in app.router.routes if not isinstance(r, Mount)]
    
    # 3. Construct fresh route list in required order
    new_routes = []
    
    # REQUIREMENT: /api MUST be mounted FIRST
    new_routes.append(Mount("/api", app=new_api_app, name="api"))
    
    # REQUIREMENT: /static (if present) next
    static_built_path = os.path.join(backend_dir, "static")
    if os.path.exists(static_built_path):
        new_routes.append(Mount("/static", StaticFiles(directory=static_built_path), name="static"))
    
    # Add preserved decorator routes
    new_routes.extend(decorator_routes)
    
    # REQUIREMENT: Root "/" MUST be mounted LAST
    frontend_path = os.path.join(backend_dir, "static", "built", "frontend")
    if os.path.exists(frontend_path):
        new_routes.append(Mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend_root"))
    else:
        fallback_frontend = os.path.join(backend_dir, "frontend")
        if os.path.exists(fallback_frontend):
            new_routes.append(Mount("/", StaticFiles(directory=fallback_frontend, html=True), name="frontend_fallback"))

    # Atomically apply new routes
    app.router.routes = new_routes
    app.middleware_stack = app.build_middleware_stack()
    
    narrate("Integrity Monitor", f"API Route Table updated. Active modules: {len(MOUNTED_MODULES)}")

# --- LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles system startup and validation."""
    narrate("Integrity Monitor", "Server started. Verifying database connection...")
    
    # Unified Startup: Ensure Local AI Server is running
    try:
        from core.config import Config
        cfg = Config()
        qwen_provider = LocalQwenProvider(model_id=cfg.MODEL_QWEN_7B, port=8001)
        # Run startup check in background so it doesn't block FastAPI startup entirely but begins immediately
        asyncio.create_task(qwen_provider._ensure_server_running())
        narrate("Integrity Monitor", "Unified Startup: Local AI Server initialization triggered.")
    except Exception as e:
        logger.error(f"Failed to trigger Local AI Server: {e}")

    # Verify PostgreSQL Connection
    if not _PSYCOPG2_AVAILABLE:
        narrate("Integrity Monitor", "PostgreSQL Connection: SKIPPED — psycopg2 not installed")
        logger.warning("psycopg2 not available; skipping PostgreSQL connectivity check")
    else:
        try:
            from config import settings
            conn = psycopg2.connect(settings.DATABASE_URL)
            conn.close()
            narrate("Integrity Monitor", "PostgreSQL Connection: SUCCESS")
            logger.info("Successfully connected to PostgreSQL database")
        except Exception as e:
            narrate("Integrity Monitor", f"PostgreSQL Connection: FAILED - {str(e)}")
            logger.error(f"CRITICAL: Could not connect to PostgreSQL: {e}")

    narrate("Integrity Monitor", "Running live functional validation...")
    
    # Register the reload callback for Hot Reloading
    async def reload_callback():
        load_modules_from_registry()
    
    repair_orchestrator.on_refresh_callback = reload_callback

    # Restore persistent daemons now that the event loop is running
    try:
        from core.orchestrator import unified_orchestrator
        await unified_orchestrator._restore_daemons()
    except Exception as e:
        logger.error(f"Failed to restore daemons during lifespan startup: {e}")

    # Start continuous runtime monitoring (Alex's role)
    await repair_orchestrator.start_continuous_monitoring()
    
    # Discovery and registration already run at module level (bottom of file)
    # The repair sequence will check if anything is broken
    await repair_orchestrator.run_startup_repair_sequence()
    
    load_modules_from_registry()
    yield
    await repair_orchestrator.stop_monitoring()

# --- PARENT APP INSTANCE ---
app = FastAPI(lifespan=lifespan)

# --- DECORATOR ROUTES (PRESERVED ACROSS REFRESH) ---
@app.get("/chat.html")
async def get_chat():
    """Serves chat.html with no-cache headers so updates are always picked up."""
    path = os.path.join(backend_dir, "static", "built", "frontend", "chat.html")
    if not os.path.exists(path):
        path = os.path.join(backend_dir, "frontend", "chat.html")
    return FileResponse(path, headers={"Cache-Control": "no-store, no-cache, must-revalidate"})


@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
async def get_dashboard():
    """Serves the dashboard with dynamic module links."""
    template_path = os.path.join(backend_dir, "static", "built", "frontend", "index.html")
    if not os.path.exists(template_path):
        template_path = os.path.join(backend_dir, "frontend", "index.html")

    if not os.path.exists(template_path):
        return HTMLResponse("<h1>Dashboard Not Found</h1><p>Please run the build process.</p>")

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return HTMLResponse(f"<h1>Error loading dashboard</h1><p>{str(e)}</p>")

    registry = get_registry()
    links_html = "<!-- MODULE_LINKS_START -->\n"
    tiles_html = "<!-- MODULE_TILES_START -->\n"

    for name, info in sorted(registry.items()):
        if info.get("status") == "active":
            display_name = info.get("name", name.replace("_", " ").title())
            ui_link = info.get("ui_link", "index.html")
            if not ui_link.startswith("http"):
                if ui_link.startswith("/"):
                    if not ui_link.startswith("/static/built"):
                        ui_link = f"/static/built{ui_link}"
                else:
                    ui_link = f"/static/built/modules/{name}/{ui_link}"

            links_html += f'                <li onclick="window.location.href=\'{ui_link}\'">{display_name}</li>\n'
            tiles_html += (
                f'                    <div class="card" onclick="window.location.href=\'{ui_link}\'" '
                f'style="cursor:pointer; border-left: 4px solid #00f2fe;">\n'
                f'                        <h3>{display_name}</h3>\n'
                f'                        <p>{info.get("description", "Active module")}</p>\n'
                f'                    </div>\n'
            )

    links_html += "                <!-- MODULE_LINKS_END -->"
    tiles_html += "                    <!-- MODULE_TILES_END -->"

    content = re.sub(r"<!-- MODULE_LINKS_START -->.*?<!-- MODULE_LINKS_END -->", links_html, content, flags=re.DOTALL)
    content = re.sub(r"<!-- MODULE_TILES_START -->.*?<!-- MODULE_TILES_END -->", tiles_html, content, flags=re.DOTALL)
    return content

# --- INITIAL DISCOVERY (Pre-server start) ---
persona_manager.load_personas()
run_discovery_and_registration()
load_modules_from_registry()
