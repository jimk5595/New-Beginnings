from fastapi import APIRouter, Body, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
import os
import asyncio
import json
from core.orchestrator import unified_orchestrator
# Import world logic
from core.world.controller_3d import ThreeDController
from core.eliza_logic import ElizaCore

router = APIRouter()

@router.post("/task")
async def eliza_task(background_tasks: BackgroundTasks, payload: dict = Body(...)):
    text = payload.get("task_text") or payload.get("task")
    attachments = payload.get("attachments") or None
    session_id = payload.get("session_id") or "default"
    user_name = payload.get("user_name") or "default"

    if not text:
        return {"response": "Missing task or task_text"}

    if text.upper().strip() == "READY":
        return {"response": "READY", "status": "ok"}

    # Step 1: Use Unified Orchestrator to classify and handle
    result = await unified_orchestrator.handle_task(text, session_id=session_id, attachments=attachments, user_name=user_name)

    # LOG PERSONA ACTIVITY
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
            description=text
        )
    except Exception:
        pass

    return result

@router.get("/poll")
async def poll_notifications(session_id: str = "default"):
    """Returns and clears any pending background-task completion notifications for a session."""
    msgs = unified_orchestrator._pending_notifications.pop(session_id, [])
    return {"notifications": msgs}


@router.get("/stream")
async def stream_notifications(session_id: str = "default"):
    """SSE endpoint — holds one persistent connection and pushes events when background tasks complete."""
    async def event_generator():
        try:
            while True:
                msgs = unified_orchestrator._pending_notifications.pop(session_id, [])
                if msgs:
                    for msg in msgs:
                        yield f"data: {json.dumps(msg)}\n\n"
                else:
                    yield ": heartbeat\n\n"
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/scene")
async def eliza_scene(payload: dict = Body(...)):
    """
    Handles requests to create or modify 3D scenes based on Eliza's analysis.
    """
    user_input = payload.get('input')
    if not user_input:
        raise HTTPException(status_code=400, detail="Missing 'input' field")

    eliza = ElizaCore()
    controller = ThreeDController()

    # 1. Analyze input
    analysis = eliza.analyze_input(user_input)
    
    # 2. Get Eliza response (includes next_action)
    eliza_output = eliza.respond(analysis)
    
    # 3. Generate scene request
    scene_req = eliza.generate_scene_request(eliza_output)
    
    # 4. Process scene request via ThreeDController
    if scene_req:
        if 'scene' in scene_req and scene_req['scene'] == 'basic_room':
            controller.build_basic_room()
        elif 'object' in scene_req:
            controller.add_prop(scene_req['object'])
            
    # Return the full scene data
    scene_data = controller.get_scene_data()
    
    return {
        "status": "ok",
        "intent": eliza_output.get("intent"),
        "next_action": eliza_output.get("next_action"),
        "scene": scene_data
    }
