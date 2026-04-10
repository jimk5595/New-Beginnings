import os
import subprocess
import asyncio
import httpx
import logging
import sys
from providers.base_provider import BaseProvider

logger = logging.getLogger("LocalQwenProvider")

class LocalQwenProvider(BaseProvider):
    def __init__(self, model_id: str, port: int = 8001):
        self.model_id = model_id
        self.port = port
        self.server_url = f"http://localhost:{self.port}/generate"
        # Use a path relative to the project root
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.ai_server_script = os.path.join(project_root, "backend", "local_ai_server.py")

    async def _ensure_server_running(self):
        """Checks if local_ai_server is running on the target port, starts it if not."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"http://localhost:{self.port}/health", timeout=1.0)
                if resp.status_code == 200:
                    return True
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
        except Exception:
            pass

        logger.info(f"Starting local_ai_server on port {self.port}...")
        
        cmd = [
            sys.executable, self.ai_server_script
        ]
        
        creation_flags = 0
        if os.name == 'nt':
            creation_flags = 0x08000000
        
        subprocess.Popen(cmd, creationflags=creation_flags)
        
        for _ in range(60):
            await asyncio.sleep(2)
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"http://localhost:{self.port}/health", timeout=1.0)
                    if resp.status_code == 200:
                        logger.info("local_ai_server is ready.")
                        return True
            except:
                continue
        
        return False

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        await self._ensure_server_running()
        
        payload = {
            "model_id": self.model_id,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "temperature": 0.7,
            "max_new_tokens": 4096
        }
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.server_url, json=payload, timeout=300.0)
                if resp.status_code != 200:
                    return f"Error from local_ai_server: {resp.text}"
                
                result = resp.json()
                return result.get("response", "").strip()
            
        except Exception as e:
            return f"Exception in local model generation: {str(e)}"
