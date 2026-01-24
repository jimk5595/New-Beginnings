import google.generativeai as genai
from core.config import Config
config = Config()
genai.configure(api_key=config.GEMINI_API_KEY)
class GeminiClient:
    def __init__(self, model=None):
        self.model = model or config.DEFAULT_MODEL
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        model = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system_prompt
        )
        response = await model.generate_content_async(user_prompt)
        return response.text
