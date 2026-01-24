import aiohttp
from config import settings

class ZencoderAPI:
    BASE_URL = "https://api.zencoder.ai/v1/generate"

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "api_key": settings.ZENCODER_API_KEY
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.BASE_URL, json=payload) as response:
                data = await response.json()
                return data.get("response", "")
