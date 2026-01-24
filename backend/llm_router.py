from google import genai

client = genai.Client()

def call_gemini_flash(prompt: str) -> str:
    # Official Gemini 3.0 Flash ID for January 2026
    response = client.models.generate_content(
        model="gemini-3-flash-preview", 
        contents=prompt
    )
    return response.text

def call_gemini_pro(prompt: str) -> str:
    # Official Gemini 3.0 Pro ID for January 2026
    response = client.models.generate_content(
        model="gemini-3-pro-preview",
        contents=prompt
    )
    return response.text

def call_gemini(model: str, prompt: str) -> str:
    # Mapping 'default' to Gemini 3.0 Flash for medical research speed
    if model == "gemini-3.0-flash" or model == "default" or not model:
        return call_gemini_flash(prompt)
    elif model == "gemini-3.0-pro":
        return call_gemini_pro(prompt)
    else:
        print(f"Warning: Model '{model}' not recognized. Falling back to Gemini 3.0 Flash.")
        return call_gemini_flash(prompt)