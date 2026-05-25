from pathlib import Path

from loguru import logger

from app.config import settings
from app.services.visual_providers.cloudflare_flux_provider import CloudflareFluxProvider
from app.services.visual_providers.google_imagen_provider import GoogleImagenProvider
from app.services.visual_providers.gemini_image_provider import GeminiImageProvider
from app.services.visual_providers.replicate_flux_provider import ReplicateFluxProvider
from app.services.visual_providers.mock_provider import MockVisualProvider
from app.services.visual_providers.original_provider import OriginalImageProvider


class VisualService:
    def __init__(self):
        self.providers = self._build_provider_chain()

    def _build_provider_chain(self):
        registry = {
            "cloudflare_flux": CloudflareFluxProvider,
            "google_imagen": GoogleImagenProvider,
            "imagen": GoogleImagenProvider,
            "gemini_image": GeminiImageProvider,
            "replicate_flux": ReplicateFluxProvider,
            "original": OriginalImageProvider,
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
        disabled_providers = {}

        for i in range(num_variants):
            output_path = str(Path(settings.STORAGE_DIR) / "output" / f"{asset_id}_v{i + 1}.jpg")
            result = self._generate_one(
                asset_id,
                i,
                product_image_path,
                reference_image_path,
                visual_prompt,
                output_path,
                disabled_providers,
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
        disabled_providers: dict[str, str],
    ) -> dict:
        errors = []

        for provider in self.providers:
            if provider.name in disabled_providers:
                logger.info(
                    f"Skipping visual provider | provider={provider.name} | "
                    f"variant={variant_index + 1} | reason={disabled_providers[provider.name]}"
                )
                continue

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
                error = self._safe_error(exc)
                logger.warning(f"Visual provider failed | provider={provider.name} | error={error}")
                errors.append(f"{provider.name}: {error}")
                if self._should_disable_for_run(error):
                    disabled_providers[provider.name] = error
                    logger.warning(
                        f"Disabling visual provider for current run | provider={provider.name} | reason={error}"
                    )

        raise RuntimeError("All visual providers failed: " + " | ".join(errors))

    def _safe_error(self, exc: Exception) -> str:
        message = str(exc).replace("\n", " ").strip()
        if len(message) > 240:
            message = message[:240] + "..."
        return f"{type(exc).__name__}: {message}"

    def _should_disable_for_run(self, error: str) -> bool:
        text = error.lower()
        markers = [
            "401",
            "402",
            "429",
            "quota",
            "resource_exhausted",
            "unauthenticated",
            "authentication token",
            "invalid authentication",
            "insufficient credit",
            "billing",
            "payment method",
            "rate limit",
            "throttled",
            "missing cloudflare_account_id",
        ]
        return any(marker in text for marker in markers)
