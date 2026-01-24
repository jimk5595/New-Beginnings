from fastapi import Depends
from core.gemini_client import GeminiClient
from providers.zencoder_provider import ZencoderProvider
from services.llm_service import LLMService

async def get_llm_service():
    client = GeminiClient()
    provider = ZencoderProvider(client)
    service = LLMService(provider)
    return service

LLMServiceDep = Depends(get_llm_service)
