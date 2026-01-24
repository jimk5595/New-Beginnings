class BaseProvider:
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError("Providers must implement generate()")
