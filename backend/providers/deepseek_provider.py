import os
import httpx
import json
import logging
from providers.base_provider import BaseProvider

logger = logging.getLogger("DeepSeekProvider")

# Endpoint and default model are env-overridable so swapping DeepSeek tiers
# (deepseek-chat / deepseek-reasoner / deepseek-v4-pro / deepseek-v4-flash)
# does NOT require touching system-core code.
_DEFAULT_API_URL = "https://api.deepseek.com/chat/completions"
_DEFAULT_MODEL = "deepseek-v4-pro"

# DeepSeek's Chat Completions API rejects max_tokens above the per-model
# ceiling with HTTP 400 ("max_tokens out of range"). DeepSeek-v4 supports
# 64K output; older tiers cap at 8K. Default high so file-rewrite repairs
# don't get silently truncated mid-stream — earlier 8K cap caused the
# size-loss guard to reject every patched index.tsx (returned 23K of
# 127K original). Override via DEEPSEEK_MAX_TOKENS for older tiers.
_HARD_MAX_TOKENS = int(os.getenv("DEEPSEEK_MAX_TOKENS", "65536"))


class DeepSeekProvider(BaseProvider):
    def __init__(self, api_url: str = None, default_model: str = None):
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.api_url = api_url or os.getenv("DEEPSEEK_API_URL", _DEFAULT_API_URL)
        self.default_model = default_model or os.getenv("DEEPSEEK_MODEL", _DEFAULT_MODEL)

    async def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, model: str = None) -> str:
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY not set")

        # Pick the requested model, falling back to the provider default.
        # Defensive: if the caller passed a non-DeepSeek model name (e.g. a
        # Gemini id was wired up by mistake), fall back to the configured
        # DeepSeek default rather than sending an invalid model and getting
        # a confusing 400 from the DeepSeek API.
        chosen_model = (model or self.default_model or _DEFAULT_MODEL).strip()
        if not chosen_model.startswith("deepseek"):
            chosen_model = self.default_model or _DEFAULT_MODEL

        # Clamp to the API's per-model ceiling.  max_tokens=0/negative would
        # also be rejected — guard that too.
        safe_max_tokens = max(1, min(int(max_tokens or _HARD_MAX_TOKENS), _HARD_MAX_TOKENS))

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": chosen_model,
            "messages": messages,
            "max_tokens": safe_max_tokens,
            "temperature": 0.0,
            "stream": True,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        collected = []
        # In streaming mode, read timeout applies per-chunk — not total response time.
        # Tokens arrive continuously so this never fires during active generation.
        # Total generation time is unlimited as long as chunks keep arriving.
        timeout = httpx.Timeout(connect=30.0, read=180.0, write=30.0, pool=30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", self.api_url, json=payload, headers=headers) as resp:
                # If the API rejects the request before streaming begins
                # (auth error, bad model, max_tokens out of range, etc.),
                # raise_for_status would raise an HTTPStatusError whose
                # body is a closed stream — surface the actual server
                # message so callers can log the real failure reason.
                if resp.status_code >= 400:
                    err_body = ""
                    try:
                        err_body = (await resp.aread()).decode("utf-8", errors="replace")
                    except Exception:
                        pass
                    raise RuntimeError(
                        f"DeepSeek API {resp.status_code} for model '{chosen_model}': {err_body[:500]}"
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
