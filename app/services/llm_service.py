from loguru import logger

from app.config import settings
from app.services.llm_providers.gemini_text_provider import GeminiTextProvider
from app.services.llm_providers.mock_provider import MockLLMProvider


class LLMService:
    def __init__(self):
        self.providers = self._build_provider_chain()

    def _build_provider_chain(self):
        registry = {
            "gemini_text": GeminiTextProvider,
            "mock": MockLLMProvider,
        }

        providers = []
        for name in settings.LLM_PROVIDER_CHAIN.split(","):
            name = name.strip().lower()
            if name in registry:
                providers.append(registry[name]())

        if not providers:
            providers.append(MockLLMProvider())

        return providers

    def generate_product_content(self, product_name, visual_prompt, content_prompt, tone) -> dict:
        errors = []

        for provider in self.providers:
            try:
                logger.info(f"Trying LLM provider | provider={provider.name}")
                return provider.generate(product_name, visual_prompt, content_prompt, tone)
            except Exception as exc:
                logger.exception(f"LLM provider failed | provider={provider.name} | error={exc}")
                errors.append(f"{provider.name}: {exc}")

        raise RuntimeError("All LLM providers failed: " + " | ".join(errors))
