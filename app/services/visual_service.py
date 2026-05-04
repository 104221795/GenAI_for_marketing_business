from loguru import logger

from app.config import settings
from app.services.visual_providers.gemini_image_provider import GeminiImageProvider
from app.services.visual_providers.replicate_flux_provider import ReplicateFluxProvider
from app.services.visual_providers.mock_provider import MockVisualProvider


class VisualService:
    def __init__(self):
        self.providers = self._build_provider_chain()

    def _build_provider_chain(self):
        registry = {
            "gemini_image": GeminiImageProvider,
            "replicate_flux": ReplicateFluxProvider,
            "mock": MockVisualProvider,
        }

        providers = []
        for name in settings.VISUAL_PROVIDER_CHAIN.split(","):
            name = name.strip().lower()
            if name in registry:
                providers.append(registry[name]())

        if not providers:
            providers.append(MockVisualProvider())

        return providers

    def generate_variants(
        self,
        asset_id: str,
        product_image_path: str,
        reference_image_path: str | None,
        visual_prompt: str,
        num_variants: int,
    ) -> list[dict]:
        results = []

        for i in range(num_variants):
            output_path = f"storage/output/{asset_id}_v{i + 1}.jpg"
            result = self._generate_one(
                asset_id,
                i,
                product_image_path,
                reference_image_path,
                visual_prompt,
                output_path,
            )
            results.append(result)

        return results

    def _generate_one(
        self,
        asset_id: str,
        variant_index: int,
        product_image_path: str,
        reference_image_path: str | None,
        visual_prompt: str,
        output_path: str,
    ) -> dict:
        errors = []

        for provider in self.providers:
            try:
                logger.info(f"Trying visual provider | provider={provider.name} | variant={variant_index + 1}")
                return provider.generate_variant(
                    asset_id=asset_id,
                    variant_index=variant_index,
                    product_image_path=product_image_path,
                    reference_image_path=reference_image_path,
                    visual_prompt=visual_prompt,
                    output_path=output_path,
                )
            except Exception as exc:
                logger.exception(f"Visual provider failed | provider={provider.name} | error={exc}")
                errors.append(f"{provider.name}: {exc}")

        raise RuntimeError("All visual providers failed: " + " | ".join(errors))
