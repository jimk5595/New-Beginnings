class ModelClient:
    def __init__(self, provider):
        self.provider = provider

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        return await self.provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
