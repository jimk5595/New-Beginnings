import os
import asyncio
import inspect
import functools
import threading
import httpx
import json
import logging
from providers.base_provider import BaseProvider

logger = logging.getLogger("QwenProvider")

_PYTHON_TYPE_TO_JSON = {
    "str": "string", "int": "integer", "float": "number",
    "bool": "boolean", "list": "array", "dict": "object",
}


def _fn_to_openai_tool(fn) -> dict:
    sig = inspect.signature(fn)
    properties = {}
    required = []
    for name, param in sig.parameters.items():
        ann = param.annotation
        if ann is inspect.Parameter.empty:
            json_type = "string"
        else:
            ann_name = ann.__name__ if hasattr(ann, "__name__") else str(ann)
            json_type = _PYTHON_TYPE_TO_JSON.get(ann_name, "string")
        properties[name] = {"type": json_type}
        if param.default is inspect.Parameter.empty:
            required.append(name)
    return {
        "type": "function",
        "function": {
            "name": fn.__name__,
            "description": (fn.__doc__ or "").strip(),
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


_DEFAULT_API_BASE = "https://ws-ghu2x5pzia8itwe4.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
_DEFAULT_MAX_TOKENS = int(os.getenv("QWEN_MAX_TOKENS", "16384"))

_CONCURRENCY_LIMIT = int(os.getenv("QWEN_CONCURRENCY", "3"))
_qwen_semaphores: dict = {}
_qwen_semaphores_lock = threading.Lock()


def _get_qwen_semaphore() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    loop_id = id(loop)
    with _qwen_semaphores_lock:
        if loop_id not in _qwen_semaphores:
            _qwen_semaphores[loop_id] = asyncio.Semaphore(_CONCURRENCY_LIMIT)
        return _qwen_semaphores[loop_id]


class QwenProvider(BaseProvider):
    def __init__(self, default_model: str = None):
        self.api_key = os.getenv("ALIBABA_API_KEY", "")
        self.api_base = os.getenv("ALIBABA_API_BASE", _DEFAULT_API_BASE)
        self.api_url = f"{self.api_base.rstrip('/')}/chat/completions"
        self.default_model = default_model or os.getenv("QWEN_MAX_MODEL", "qwen3.7-max-2026-06-08")

    async def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = _DEFAULT_MAX_TOKENS, model: str = None, tools: list = None) -> str:
        if not self.api_key:
            raise ValueError("ALIBABA_API_KEY not set")

        chosen_model = (model or self.default_model).strip()
        safe_max_tokens = max(1, min(int(max_tokens or _DEFAULT_MAX_TOKENS), _DEFAULT_MAX_TOKENS))

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        timeout = httpx.Timeout(connect=30.0, read=180.0, write=30.0, pool=30.0)
        max_retries = 4
        backoff = 5

        if tools:
            tool_defs = [_fn_to_openai_tool(fn) for fn in tools if callable(fn)]
            tool_map = {fn.__name__: fn for fn in tools if callable(fn)}
            payload = {
                "model": chosen_model,
                "messages": messages,
                "max_tokens": safe_max_tokens,
                "temperature": 0.6,
                "tools": tool_defs,
                "tool_choice": "auto",
            }
            loop = asyncio.get_running_loop()
            max_tool_rounds = 12

            async with _get_qwen_semaphore():
                for _round in range(max_tool_rounds):
                    last_error = None
                    for attempt in range(max_retries):
                        try:
                            async with httpx.AsyncClient(timeout=timeout) as client:
                                resp = await client.post(self.api_url, json=payload, headers=headers)
                            if resp.status_code == 429:
                                wait = backoff * (2 ** attempt)
                                logger.warning(f"Qwen 429 on tool round {_round} attempt {attempt + 1}, retrying in {wait}s...")
                                await asyncio.sleep(wait)
                                continue
                            if resp.status_code >= 400:
                                raise RuntimeError(f"Qwen API {resp.status_code}: {resp.text[:500]}")
                            data = resp.json()
                            choice = data["choices"][0]
                            msg = choice["message"]
                            tool_calls = msg.get("tool_calls") or []
                            if not tool_calls:
                                return msg.get("content") or ""
                            messages.append(msg)
                            for tc in tool_calls:
                                fn_name = tc["function"]["name"]
                                try:
                                    fn_args = json.loads(tc["function"].get("arguments") or "{}")
                                except json.JSONDecodeError:
                                    fn_args = {}
                                fn = tool_map.get(fn_name)
                                if fn:
                                    try:
                                        tool_result = await loop.run_in_executor(
                                            None, functools.partial(fn, **fn_args)
                                        )
                                    except Exception as _te:
                                        tool_result = f"Error calling {fn_name}: {_te}"
                                else:
                                    tool_result = f"Error: Unknown tool '{fn_name}'"
                                logger.info(f"Qwen tool call: {fn_name}({fn_args}) -> {str(tool_result)[:120]}")
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tc["id"],
                                    "content": str(tool_result),
                                })
                            payload["messages"] = messages
                            break
                        except RuntimeError:
                            raise
                        except Exception as e:
                            last_error = e
                            if attempt < max_retries - 1:
                                wait = backoff * (2 ** attempt)
                                logger.warning(f"Qwen tool-call error on attempt {attempt + 1}: {e}. Retrying in {wait}s...")
                                await asyncio.sleep(wait)
                            else:
                                raise
                raise RuntimeError(f"Qwen tool-calling loop exceeded {max_tool_rounds} rounds for model '{chosen_model}'")

        payload = {
            "model": chosen_model,
            "messages": messages,
            "max_tokens": safe_max_tokens,
            "temperature": 0.6,
            "stream": True,
        }

        async with _get_qwen_semaphore():
            for attempt in range(max_retries):
                collected = []
                try:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        async with client.stream("POST", self.api_url, json=payload, headers=headers) as resp:
                            if resp.status_code == 429:
                                err_body = ""
                                try:
                                    err_body = (await resp.aread()).decode("utf-8", errors="replace")
                                except Exception:
                                    pass
                                wait = backoff * (2 ** attempt)
                                logger.warning(f"Qwen 429 rate limit on attempt {attempt + 1}, retrying in {wait}s...")
                                await asyncio.sleep(wait)
                                continue
                            if resp.status_code >= 400:
                                err_body = ""
                                try:
                                    err_body = (await resp.aread()).decode("utf-8", errors="replace")
                                except Exception:
                                    pass
                                raise RuntimeError(
                                    f"Qwen API {resp.status_code} for model '{chosen_model}': {err_body[:500]}"
                                )
                            async for line in resp.aiter_lines():
                                if not line or not line.startswith("data: "):
                                    continue
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data_str)
                                    delta = chunk["choices"][0]["delta"].get("content", "")
                                    if delta:
                                        collected.append(delta)
                                except (json.JSONDecodeError, KeyError, IndexError):
                                    continue
                    return "".join(collected)
                except RuntimeError:
                    raise
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait = backoff * (2 ** attempt)
                        logger.warning(f"Qwen request error on attempt {attempt + 1}: {e}. Retrying in {wait}s...")
                        await asyncio.sleep(wait)
                    else:
                        raise

        raise RuntimeError(f"Qwen API rate limit exceeded after {max_retries} retries for model '{chosen_model}'")
