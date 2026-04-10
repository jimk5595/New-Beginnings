import json
import logging
import asyncio
from typing import Optional

logger = logging.getLogger("MemoryExtractor")


_EXTRACTION_PROMPT = """You are a memory extraction engine. Analyze the conversation excerpt below and extract any personal, meaningful, or platform-relevant information about the user named "{user_name}".

Extract facts into these categories:
- personal: name, age, family, relationships, background, life events
- preferences: likes, dislikes, habits, hobbies, interests
- goals: ambitions, plans, dreams, what they want to achieve
- platform: their vision, ideas, or decisions about the NewBeginnings AI platform
- emotions: how they felt, current mindset, concerns, excitement
- work: their job, projects, entrepreneurial activities
- family: mentions of spouse, kids, relatives (store as separate facts per person)

Return ONLY a valid JSON object in this exact format:
{{
  "facts": [
    {{"category": "personal", "fact": "..."}},
    {{"category": "platform", "fact": "..."}}
  ],
  "profile_update": {{
    "bio": "one line bio update or null",
    "personality": "personality insight or null",
    "preferences": "key preferences summary or null",
    "life_context": "current life situation or null"
  }},
  "summary": "2-3 sentence summary of what was discussed in this conversation"
}}

If there is nothing meaningful to extract, return: {{"facts": [], "profile_update": {{}}, "summary": ""}}

CONVERSATION:
{conversation}"""


async def extract_and_store_memory(
    user_name: str,
    conversation_turns: list,
    session_id: str = "default",
    min_turns: int = 2
):
    """
    Runs after a conversation to extract facts, update the user profile,
    and persist a summary. Fires asynchronously — never blocks chat responses.

    conversation_turns: list of {"role": "user"/"assistant", "content": "..."}
    """
    if not user_name or user_name.lower() in ("unknown", "default", ""):
        return
    if len(conversation_turns) < min_turns:
        return

    try:
        conversation_text = "\n".join(
            f"{t['role'].upper()}: {t['content'][:400]}"
            for t in conversation_turns[-12:]
        )

        prompt = _EXTRACTION_PROMPT.format(
            user_name=user_name,
            conversation=conversation_text
        )

        from core.llm_client import call_llm_async
        result = await call_llm_async(
            model_name="gemini-3.1-flash-lite-preview",
            prompt=prompt,
            system_instruction="You are a precise memory extraction engine. Return only valid JSON.",
            persona_name="Memory Extractor",
            max_tokens=1000
        )

        raw = result.get("text", "") if isinstance(result, dict) else str(result)
        if not raw:
            return

        raw = raw.strip()
        if raw.startswith("```"):
            import re
            raw = re.sub(r'^```(?:json)?\n?', '', raw)
            raw = re.sub(r'\n?```$', '', raw).strip()

        data = json.loads(raw)

        from memory_system.memory_core import MemoryEngine
        engine = MemoryEngine()

        facts = data.get("facts", [])
        for f in facts:
            category = f.get("category", "general")
            fact = f.get("fact", "").strip()
            if fact:
                engine.add_memory_fact(user_name, category, fact, session_id=session_id)

        profile_update = data.get("profile_update", {})
        if any(v for v in profile_update.values()):
            engine.upsert_user_profile(
                user_name=user_name,
                bio=profile_update.get("bio") or None,
                personality=profile_update.get("personality") or None,
                preferences=profile_update.get("preferences") or None,
                life_context=profile_update.get("life_context") or None,
            )

        summary = data.get("summary", "").strip()
        if summary:
            engine.save_long_term_summary(user_name, summary, session_id=session_id)

        logger.info(f"Memory extraction complete for {user_name}: {len(facts)} facts, summary={'yes' if summary else 'no'}")

    except json.JSONDecodeError:
        logger.debug(f"Memory extraction returned non-JSON for {user_name} — skipping.")
    except Exception as e:
        logger.error(f"Memory extraction failed for {user_name}: {e}")
