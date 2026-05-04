import json
from app.config import settings
from app.services.llm_providers.base import LLMProvider


class GeminiTextProvider(LLMProvider):
    name = "gemini_text"

    def generate(self, product_name, visual_prompt, content_prompt, tone) -> dict:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("Missing GEMINI_API_KEY")

        from google import genai

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        name = product_name or "pre-owned fashion product"

        prompt = f'''
You are a professional Vietnamese fashion retail copywriter.

Product name: {name}
Visual concept: {visual_prompt}
User task: {content_prompt}
Tone: {tone}

Write product marketing content for a pre-owned fashion retail shop.

Return ONLY valid JSON:
{{
  "description": "...",
  "caption": "...",
  "hashtags": ["#tag1", "#tag2", "#tag3"]
}}
'''

        response = client.models.generate_content(
            model=settings.GEMINI_TEXT_MODEL,
            contents=prompt,
        )

        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)

        return {
            "provider": self.name,
            "description": data.get("description", ""),
            "caption": data.get("caption", ""),
            "hashtags": data.get("hashtags", []),
        }
