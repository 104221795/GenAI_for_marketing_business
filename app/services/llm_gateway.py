from loguru import logger

from app.config import settings
from app.services.llm_providers.gemini_text_provider import GeminiTextProvider
from app.services.llm_providers.mock_provider import MockLLMProvider


class LLMGateway:
    """Normalizes marketing content and owns LLM provider failover."""

    def __init__(self):
        self.providers = self._build_provider_chain()

    def _build_provider_chain(self):
        registry = {
            "gemini_text": GeminiTextProvider,
            "mock": MockLLMProvider,
        }
        providers = []
        for name in settings.LLM_PROVIDER_CHAIN.split(","):
            provider_class = registry.get(name.strip().lower())
            if provider_class:
                providers.append(provider_class())
        return providers or [MockLLMProvider()]

    def generate_product_content(
        self,
        product_name,
        visual_prompt,
        content_prompt,
        tone,
        campaign_context: dict | None = None,
        product_image_path: str | None = None,
    ) -> dict:
        errors = []
        for provider in self.providers:
            try:
                logger.info(f"Trying LLM gateway provider | provider={provider.name}")
                content = provider.generate(
                    product_name,
                    visual_prompt,
                    content_prompt,
                    tone,
                    campaign_context=campaign_context or {},
                    product_image_path=product_image_path,
                )
                return self._normalize_content(content)
            except Exception as exc:
                error = self._safe_error(exc)
                errors.append(f"{provider.name}: {error}")
                logger.warning(f"LLM gateway provider failed | provider={provider.name} | error={error}")

        raise RuntimeError("All LLM gateway providers failed: " + " | ".join(errors))

    def _normalize_content(self, content: dict) -> dict:
        hashtags = content.get("hashtags") or []
        if isinstance(hashtags, str):
            hashtags = [tag.strip() for tag in hashtags.split() if tag.strip()]

        channel_outputs = dict(content.get("channel_outputs") or {})
        description = content.get("description") or channel_outputs.get("product_description") or ""
        caption = content.get("caption") or channel_outputs.get("instagram_caption") or ""

        channel_outputs.setdefault("product_description", description)
        channel_outputs.setdefault("instagram_caption", caption)
        channel_outputs.setdefault("hashtags", hashtags)
        if content.get("product_analysis"):
            channel_outputs.setdefault("product_analysis", content["product_analysis"])
        return {
            "provider": content.get("provider", "unknown"),
            "description": description,
            "caption": caption,
            "hashtags": hashtags,
            "channel_outputs": channel_outputs,
        }

    def _safe_error(self, exc: Exception) -> str:
        message = str(exc).replace("\n", " ").strip()
        return f"{type(exc).__name__}: {message[:240]}" + ("..." if len(message) > 240 else "")
