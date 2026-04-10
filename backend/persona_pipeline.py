from task_models import PipelineRequest, PipelineResponse
from core.llm_client import call_llm

def run_persona_pipeline(request: PipelineRequest, persona) -> PipelineResponse:
    """
    Executes a persona-specific LLM call through the central pipeline.
    """
    system_instruction = persona.system_prompt if hasattr(persona, "system_prompt") else ""
    persona_name = persona.name if hasattr(persona, "name") else "Architect"
    
    # Use the blocking call_llm wrapper from core.llm_client
    response_data = call_llm(
        model_name=request.model if request.model != "default" else "gemini-3.1-flash-lite-preview",
        prompt=request.prompt,
        system_instruction=system_instruction,
        persona_name=persona_name
    )
    
    return PipelineResponse(output=response_data.get("text", "Error: No output generated."))
