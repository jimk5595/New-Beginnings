import os
import torch
import logging
import uvicorn
import time
import threading # Added for serialization
from typing import List, Optional, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import whisper
from PIL import Image
import io
import base64
from core.config import Config

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LocalAIServer")

app = FastAPI(title="NewBeginnings Local AI Server (PyTorch/Transformers)")
config = Config()

# Model Cache and Serialization
MODELS = {}
TOKENIZERS = {}
model_lock = threading.Lock() # Global lock to prevent GPU/CPU contention

# Friendly Mapping to resolve persona/module names to local paths
MODEL_MAP = {
    "qwen-7b": config.MODEL_QWEN_7B,
    "qwen-14b": config.MODEL_QWEN_14B,
    "qwen-2.5-7b-instruct": config.MODEL_QWEN_7B,
    "qwen-2.5-14b-instruct": config.MODEL_QWEN_14B
}

class InferenceRequest(BaseModel):
    model_id: str
    system_prompt: str = ""
    user_prompt: str
    temperature: float = 0.7
    max_new_tokens: int = 4096

# --- OpenAI Compatibility Schemas ---
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4096
    stream: Optional[bool] = False

class AudioInferenceRequest(BaseModel):
    audio_data: str  # Base64 encoded audio

class VisionInferenceRequest(BaseModel):
    image_data: str  # Base64 encoded image
    prompt: str

@app.on_event("startup")
async def load_initial_models():
    """Load models at startup as per configuration."""
    logger.info("Initializing Local AI Server...")
    # Paths will be provided by main system via environment or config
    pass

def get_model_and_tokenizer(model_key: str):
    # Resolve friendly name to absolute path
    model_path = MODEL_MAP.get(model_key, model_key)
    
    if model_path not in MODELS:
        if not os.path.exists(model_path):
            logger.error(f"Model path does not exist: {model_path}")
            raise HTTPException(status_code=404, detail=f"Model {model_key} not found at {model_path}")
            
        logger.info(f"Loading model from {model_path}...")
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(
                model_path, 
                device_map="auto", 
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                trust_remote_code=True
            )
            MODELS[model_path] = model
            TOKENIZERS[model_path] = tokenizer
        except Exception as e:
            logger.error(f"Failed to load model {model_path}: {e}")
            raise e
    return MODELS[model_path], TOKENIZERS[model_path]

@app.post("/v1/chat/completions")
def chat_completions(request: ChatCompletionRequest):
    """OpenAI-compatible endpoint for chat completions using local Qwen models."""
    with model_lock: # Serialize generations to prevent GPU/CPU contention
        try:
            model, tokenizer = get_model_and_tokenizer(request.model)
            
            # Format prompt from message list (Simplified chat template)
            prompt = ""
            for msg in request.messages:
                role = "System" if msg.role == "system" else "User" if msg.role == "user" else "Assistant"
                prompt += f"{role}: {msg.content}\n"
            prompt += "Assistant:"
            
            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
            
            with torch.no_grad():
                output_ids = model.generate(
                    **inputs,
                    max_new_tokens=request.max_tokens,
                    temperature=request.temperature,
                    do_sample=True if request.temperature > 0 else False,
                    pad_token_id=tokenizer.eos_token_id
                )
            
            response_text = tokenizer.decode(output_ids[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
            
            return {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": len(inputs.input_ids[0]),
                    "completion_tokens": len(output_ids[0]) - len(inputs.input_ids[0]),
                    "total_tokens": len(output_ids[0])
                }
            }
        except Exception as e:
            logger.error(f"Chat completion error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate")
def generate(request: InferenceRequest):
    """Synchronous generation to run in FastAPI's threadpool."""
    with model_lock: # Serialize generations
        try:
            model, tokenizer = get_model_and_tokenizer(request.model_id)
            
            prompt = f"System: {request.system_prompt}\nUser: {request.user_prompt}\nAssistant:"
            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
            
            with torch.no_grad():
                output_ids = model.generate(
                    **inputs,
                    max_new_tokens=request.max_new_tokens,
                    temperature=request.temperature,
                    do_sample=True if request.temperature > 0 else False,
                    pad_token_id=tokenizer.eos_token_id
                )
            
            response = tokenizer.decode(output_ids[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            return {"response": response.strip()}
        except Exception as e:
            logger.error(f"Inference error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/whisper")
async def transcribe(request: AudioInferenceRequest):
    try:
        if "whisper" not in MODELS:
            logger.info("Loading Whisper model...")
            MODELS["whisper"] = whisper.load_model("base") # Or path to local
            
        # Decode audio
        # ... logic to save to tmp and process ...
        return {"text": "Audio transcription not fully implemented in this stub."}
    except Exception as e:
        logger.error(f"Whisper error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/moondream")
async def vision_inference(request: VisionInferenceRequest):
    try:
        # Moondream 2 logic
        return {"response": "Vision inference not fully implemented in this stub."}
    except Exception as e:
        logger.error(f"Moondream error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok", "loaded_models": list(MODELS.keys())}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
