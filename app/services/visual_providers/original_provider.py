from pathlib import Path

from PIL import Image

from app.services.visual_providers.base import VisualProvider


class OriginalImageProvider(VisualProvider):
    """Last-resort output that never asks a generator to reinterpret the product."""

    name = "original"

    def generate_variant(
        self,
        asset_id: str,
        variant_index: int,
        product_image_path: str,
        reference_image_path: str | None,
        visual_prompt: str,
        output_path: str,
    ) -> dict:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Image.open(product_image_path).convert("RGB").save(output_path, quality=98)
        return {
            "variant_id": f"v{variant_index + 1}",
            "image_path": output_path,
            "provider": "original_fallback",
        }
