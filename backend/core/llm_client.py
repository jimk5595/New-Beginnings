import os
import asyncio
import logging
from google import genai
from google.genai import types
from core.config import Config
from persona_logger import narrate
from providers.local_qwen_provider import LocalQwenProvider
from datetime import datetime

logger = logging.getLogger("LLMClient")
logger.setLevel(logging.INFO)

config = Config()

# --- TOKEN OPTIMIZATION: PROMPT CACHING (Tier 1) ---
# Structures system instructions and core physics constants as immutable headers
# to trigger provider-side caching.
SYSTEM_CACHE_PREFIX = f"""
<cache-tier-1-immutable>
CORE SYSTEM INSTRUCTIONS:
- Act as the central intelligence for the platform.
- Maintain absolute high-fidelity in all technical builds.
- Adhere to the Reasoning Protocol and Modular Architecture.

CORE RUNTIME CONSTANTS:
- Workspace: {config.PROJECT_ROOT}
- Stack: FastAPI, React/Vite, PostgreSQL, Local Qwen 14B
- Deployment: Local Execution Environment
</cache-tier-1-immutable>
"""

TEXT_MIME_PREFIXES = ("text/",)
TEXT_MIME_EXACT = {
    "application/json", "application/xml", "application/javascript",
    "application/x-python", "application/x-sh", "application/x-yaml",
    "application/toml", "application/csv",
}

def _is_text_mime(mime: str) -> bool:
    return mime.startswith(TEXT_MIME_PREFIXES) or mime in TEXT_MIME_EXACT


def _build_attachment_parts(att) -> list:
    """Convert an attachment dict into a list of Part dicts for generate_content contents."""
    import base64
    if isinstance(att, str):
        return [{"text": att}]
    if not isinstance(att, dict):
        return [att]

    name = att.get("name", "file")
    mime = att.get("mimeType", "application/octet-stream")
    data = att.get("data", "")
    is_text = att.get("isText", False) or _is_text_mime(mime)

    if is_text:
        return [{"text": f"[Attached file: {name}]\n{data}"}]

    try:
        raw = base64.b64decode(data)
        return [{"inline_data": {"mime_type": mime, "data": raw}}]
    except Exception:
        return [{"text": f"[Attached file: {name} — could not decode binary data]"}]


def _build_sdk_parts(att) -> list:
    """Convert an attachment dict into a list of genai.types.Part objects for chat.send_message."""
    import base64
    if isinstance(att, str):
        return [genai.types.Part(text=att)]
    if not isinstance(att, dict):
        return [att]

    name = att.get("name", "file")
    mime = att.get("mimeType", "application/octet-stream")
    data = att.get("data", "")
    is_text = att.get("isText", False) or _is_text_mime(mime)

    if is_text:
        return [genai.types.Part(text=f"[Attached file: {name}]\n{data}")]

    try:
        raw = base64.b64decode(data)
        return [genai.types.Part(inline_data=genai.types.Blob(mime_type=mime, data=raw))]
    except Exception:
        return [genai.types.Part(text=f"[Attached file: {name} — could not decode binary data]")]


def get_client(api_version: str = "v1beta"):
    """Lazily initialize version-specific Gemini clients."""
    attr_name = f"_client_{api_version.replace('.', '_')}"
    if not hasattr(get_client, attr_name):
        if not config.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY is missing from configuration!")
        client = genai.Client(
            api_key=config.GEMINI_API_KEY,
            http_options={'api_version': api_version}
        )
        setattr(get_client, attr_name, client)
    return getattr(get_client, attr_name)


def reset_client(api_version: str = None):
    """Reset cached Gemini client(s) to force fresh HTTP connections on the next call.

    When asyncio.wait_for() times out, the thread running the Gemini SDK call cannot
    be cancelled — it continues as a zombie, holding the old client's connection pool
    slots open. If the fallback model uses the same cached client, it competes for
    those same slots and is often slow or stalled too. Resetting the client forces a
    brand-new connection pool for the fallback, completely isolated from zombie threads.
    """
    if api_version:
        attr_name = f"_client_{api_version.replace('.', '_')}"
        if hasattr(get_client, attr_name):
            delattr(get_client, attr_name)
    else:
        for attr in list(vars(get_client)):
            if attr.startswith("_client_"):
                delattr(get_client, attr)

async def call_llm_async(model_name: str, prompt: str, system_instruction: str = "", tools: list = None, max_tokens: int = 65536, persona_name: str = "Integrity Monitor", history: list = None, attachments: list = None, blocked_models: list = None, thinking_level: str = None, disable_search: bool = False) -> dict:
    """Unified LLM entry point with version-aware routing, Tier-1 caching, and Thought Signature persistence."""
    current_date = datetime.now().strftime("%B %d, %Y")
    
    # Tier 1: Cache-First Immutable Prefix
    full_system_instruction = f"{SYSTEM_CACHE_PREFIX}\n\nDate: {current_date}\n\n{system_instruction}"
    
    # Tier 3: Logic 3 - Request Reconstructor
    # Updated to 2026 SDK requirements: using list of Parts or strings for single-turn
    history_payload = []
    if history:
        for turn in history:
            role = "user" if turn["role"] == "user" else "model"
            part = {"text": turn["content"]}
            if role == "model" and turn.get("thought_signature"):
                part["thought_signature"] = turn["thought_signature"]
            history_payload.append({"role": role, "parts": [part]})
    
    # Current message parts — SDK requires Part dicts {"text": "..."}, NOT raw strings
    current_parts = [{"text": prompt}]
    if attachments:
        for att in attachments:
            current_parts += _build_attachment_parts(att)

    # Proactively use the requested primary
    target_model = model_name if model_name and model_name != "default" else config.DEFAULT_MODEL
    
    async def heartbeat_narrator(model_name: str, persona: str, stop_event: asyncio.Event):
        """Narrates progress every 15 seconds to keep the user informed."""
        import time
        start_time = time.time()
        while not stop_event.is_set():
            await asyncio.sleep(15)
            if not stop_event.is_set():
                elapsed = int(time.time() - start_time)
                narrate(persona, f"Still requesting high-fidelity response from {model_name} (Elapsed: {elapsed}s)...")

    fallbacks = [
        config.GEMINI_MODEL_31_CUSTOMTOOLS,
        config.GEMINI_MODEL_31_PRO,
        config.GEMINI_MODEL_31_FLASH_LITE,
        config.GEMINI_MODEL_31_FLASH,
        config.GEMINI_MODEL_30_FLASH,
        config.GEMINI_MODEL_25_PRO,
        config.GEMINI_MODEL_25_FLASH
    ]

    # Model execution with fallbacks (unique items)
    _blocked = set(blocked_models) if blocked_models else set()
    models_to_try = []
    seen = set()
    for m in [target_model] + fallbacks:
        if m and m not in seen and m not in _blocked:
            models_to_try.append(m)
            seen.add(m)

    for model in models_to_try:
        if not model: continue
        narrate(persona_name, f"Attempting connection to {model}...")
        
        # Timeout: 150s per model. On API-slow days 280s meant one domain could burn 9+ minutes
        # (280s customtools timeout + 280s pro-preview timeout) before moving on.
        # 150s is enough for any legitimate response — if a model hasn't replied in 150s, it's stuck.
        timeout_val = 150 if "3.1" in model else 180
        max_attempts = 1 if "3.1" in model else 2
        
        for attempt in range(max_attempts):
            stop_event = asyncio.Event()
            heartbeat_task = asyncio.create_task(heartbeat_narrator(model, persona_name, stop_event))
            try:
                # --- TRANSIENT NETWORK RETRY LAYER ---
                # Handles DNS failures, connection resets, and server disconnects before failing over to fallback model.
                last_network_error = None
                for network_retry in range(3):
                    try:
                        # Optimized for Gemini 3.x & 2.5 with Thinking Config
                        is_gemini_3 = "gemini-3" in model
                        is_25 = "gemini-2.5" in model
                        is_31 = "3.1" in model
                        
                        # Both Gemini 3.x and 2.5 require v1beta for systemInstruction and tools support.
                        api_version = "v1beta" if (is_gemini_3 or is_25) else "v1"
                        client = get_client(api_version)
                        
                        # System instruction is passed in gen_config for generate_content,
                        # but for chats (with tools) it's often passed during chat creation.
                        # GenAI SDK handles this, but we must ensure it's not None.
                        gen_config = genai.types.GenerateContentConfig(
                            system_instruction=full_system_instruction if not tools else None,
                            max_output_tokens=max_tokens,
                            temperature=1.0 if (is_gemini_3 or is_25) else 0.7
                        )
                        
                        if (is_gemini_3 or is_25) and not tools and not disable_search:
                            gen_config.tools = [types.Tool(google_search=types.GoogleSearch())]
                        
                        if is_31:
                            if thinking_level == "none":
                                gen_config.thinking_config = genai.types.ThinkingConfig(include_thoughts=False)
                            else:
                                level = thinking_level if thinking_level is not None else ("medium" if "pro" in model else "minimal")
                                gen_config.thinking_config = genai.types.ThinkingConfig(
                                    include_thoughts=True,
                                    thinking_level=level
                                )
                        
                        loop = asyncio.get_running_loop()
                        
                        if tools:
                            # For tool-enabled calls, system instruction MUST be in the config passed to create_chat
                            chat_config = genai.types.GenerateContentConfig(
                                system_instruction=full_system_instruction,
                                max_output_tokens=max_tokens,
                                temperature=1.0 if (is_gemini_3 or is_25) else 0.7,
                                tools=tools,
                                automatic_function_calling=genai.types.AutomaticFunctionCallingConfig(disable=False)
                            )
                            
                            def sync_chat_call():
                                chat = client.chats.create(model=model, config=chat_config, history=history_payload)
                                if attachments:
                                    sdk_parts = [genai.types.Part(text=prompt)]
                                    for att in attachments:
                                        sdk_parts += _build_sdk_parts(att)
                                    return chat.send_message(message=sdk_parts)
                                else:
                                    return chat.send_message(message=prompt)
                            
                            response = await asyncio.wait_for(
                                loop.run_in_executor(None, sync_chat_call),
                                timeout=timeout_val
                            )
                        else:
                            def sync_gen_call():
                                full_contents = history_payload + [{"role": "user", "parts": current_parts}]
                                return client.models.generate_content(
                                    model=model,
                                    contents=full_contents,
                                    config=gen_config
                                )
                            
                            response = await asyncio.wait_for(
                                loop.run_in_executor(None, sync_gen_call),
                                timeout=timeout_val
                            )
                        
                        if not response:
                            raise ValueError(f"Empty response from {model}")
                        
                        if hasattr(response, 'thoughts') and response.thoughts:
                            logger.info(f"[{model}] Thoughts: {response.thoughts[:500]}...")
                        
                        text_content = ""
                        thought_signature = None
                        
                        if response.candidates and response.candidates[0].content.parts:
                            for part in response.candidates[0].content.parts:
                                if hasattr(part, 'thought_signature') and part.thought_signature:
                                    ts = part.thought_signature
                                    if isinstance(ts, bytes):
                                        import base64
                                        ts = base64.b64encode(ts).decode("ascii")
                                    thought_signature = ts
                                
                                if hasattr(part, 'text') and part.text and not getattr(part, 'thought', False):
                                    text_content += part.text
                                elif hasattr(part, 'function_call') and part.function_call:
                                    narrate(persona_name, f"SUCCESS: {model} executed tool: {part.function_call.name}")
                                    if tools:
                                        text_content += f"Tool executed: {part.function_call.name}"
                        
                        has_function_call = any(
                            hasattr(p, 'function_call') and p.function_call
                            for p in (response.candidates[0].content.parts if response.candidates else [])
                        )
                        if not thought_signature and is_31 and has_function_call:
                            thought_signature = "skip_thought_signature_validator"

                        if text_content:
                            return {"text": text_content, "thought_signature": thought_signature}
                        
                        if response.candidates and response.candidates[0].content.parts:
                            for part in response.candidates[0].content.parts:
                                if hasattr(part, 'function_call') and part.function_call:
                                    return {"text": f"Task completed via tool call: {part.function_call.name}", "thought_signature": thought_signature}

                        raise ValueError(f"Response from {model} has no usable content.")

                    except (asyncio.TimeoutError, Exception) as e:
                        error_str = str(e).upper()
                        transient_patterns = [
                            "GETADDRINFO FAILED", "SERVER DISCONNECTED", "CONNECTION RESET",
                            "EOF OCCURRED IN VIOLATION OF PROTOCOL", "REMOTE END CLOSED CONNECTION",
                            "DEADLINE EXCEEDED", "INTERNAL ERROR", "SERVICE UNAVAILABLE"
                        ]
                        if any(p in error_str for p in transient_patterns):
                            wait_sec = (network_retry + 1) * 2
                            narrate(persona_name, f"NETWORK ERROR with {model}: {str(e)}. Retrying in {wait_sec}s (Attempt {network_retry + 1}/3)...")
                            await asyncio.sleep(wait_sec)
                            last_network_error = e
                            continue
                        if any(word in error_str for word in ["503", "UNAVAILABLE", "DEMAND", "429", "QUOTA", "LIMIT"]):
                            wait_sec = (network_retry + 1) * 10
                            narrate(persona_name, f"HIGH DEMAND on {model}: {str(e)}. Retrying in {wait_sec}s (Attempt {network_retry + 1}/3)...")
                            await asyncio.sleep(wait_sec)
                            last_network_error = e
                            continue
                        raise e
                
                if last_network_error:
                    raise last_network_error

            except asyncio.TimeoutError:
                narrate(persona_name, f"TIMEOUT: {model} is caught in a thinking loop (> {timeout_val}s). Resetting connection pool and failing over...")
                reset_client()
                break 
            except Exception as e:
                error_str = str(e).upper()
                narrate(persona_name, f"ERROR with {model}: {str(e)}")
                
                if "400" in error_str or "PART TYPE" in error_str or "MESSAGE MUST BE A VALID PART TYPE" in error_str:
                    narrate(persona_name, "CRITICAL: Detected SDK Part Type mismatch. Pivoting to Local Qwen immediately...")
                    break 

                if any(word in error_str for word in ["QUOTA", "LIMIT", "429", "503", "DEMAND"]):
                    narrate(persona_name, f"WARNING: {model} still unavailable after retries. Pivoting to fallback...")
                    break 
                
                if attempt == 0:
                    await asyncio.sleep(1)
                    continue
                break
            finally:
                stop_event.set()
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
    
    # Final Fallback to Local Qwen
    try:
        narrate(persona_name, "CRITICAL: All Gemini models failed. Pivoting to Local Qwen 14B...")
        provider = LocalQwenProvider(model_id=config.MODEL_QWEN_14B, port=8001)
        res = await provider.generate(full_system_instruction, prompt)
        return {"text": res, "thought_signature": None}
    except Exception as e:
        return {"text": f"Error: All LLM paths failed. {str(e)}", "thought_signature": None}

def call_llm(model_name: str, prompt: str, system_instruction: str = "", persona_name: str = "Integrity Monitor", history: list = None, attachments: list = None) -> dict:
    """Consolidated LLM entry point (blocking wrapper)."""
    import nest_asyncio
    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    if loop.is_running():
        return asyncio.run_coroutine_threadsafe(call_llm_async(model_name, prompt, system_instruction, persona_name=persona_name, history=history, attachments=attachments), loop).result()
    return asyncio.run(call_llm_async(model_name, prompt, system_instruction, persona_name=persona_name, history=history, attachments=attachments))
