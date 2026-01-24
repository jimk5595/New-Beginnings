class LLMService:
    def __init__(self, client):
        self.client = client

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = await self.client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        return response
