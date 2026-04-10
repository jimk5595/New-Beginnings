from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Any
from core.orchestrator import unified_orchestrator
import json
import time

router = APIRouter()

class AttachmentPayload(BaseModel):
    name: str
    mimeType: str
    data: str
    isText: bool = False

class ChatRequest(BaseModel):
    persona: str
    message: str
    background: bool = False
    daemon: bool = False
    attachments: Optional[List[AttachmentPayload]] = []
    session_id: Optional[str] = "default"
    user_name: Optional[str] = "default"

@router.post("/chat", response_model=None)
async def chat_endpoint(payload: ChatRequest):
    attachments = [a.model_dump() for a in payload.attachments] if payload.attachments else None

    result = await unified_orchestrator.handle_task(
        payload.message,
        session_id=payload.session_id or "default",
        background=payload.background,
        daemon=payload.daemon,
        attachments=attachments,
        forced_persona=payload.persona or None,
        user_name=payload.user_name or "default"
    )

    if not payload.background and not payload.daemon:
        try:
            from memory_system.memory_core import MemoryEngine
            engine = MemoryEngine()
            persona_details = result.get('orchestration', {}).get('persona_details', {})
            role = persona_details.get('role') or persona_details.get('description', 'AI Assistant')
            engine.log_persona_activity(
                name=result['assigned_to'],
                role=role,
                category=result['category'],
                module="",
                description=payload.message
            )
        except Exception:
            pass

    return result
