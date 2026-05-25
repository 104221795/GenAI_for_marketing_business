import base64
import binascii
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

from app.config import settings
from app.services.visual_providers.base import VisualProvider


class CloudflareFluxProvider(VisualProvider):
    """Direct image editing through Workers AI FLUX.2 Klein 4B."""

    name = "cloudflare_flux"
    _MAX_INPUT_EDGE = 511

    def generate_variant(
        self,
        asset_id: str,
        variant_index: int,
        product_image_path: str,
        reference_image_path: str | None,
        visual_prompt: str,
        output_path: str,
    ) -> dict:
        if not settings.CLOUDFLARE_ACCOUNT_ID or not settings.CLOUDFLARE_API_TOKEN:
            raise RuntimeError("Missing CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN")

        has_reference = bool(reference_image_path)
        exact_overlay = self._has_transparent_foreground(product_image_path)
        source_product_overlay = (
            self._build_source_product_overlay(product_image_path) if exact_overlay else None
        )
        files = {
            "input_image_0": (
                "product.png",
                self._prepare_input_image(product_image_path, source_product_overlay),
                "image/png",
            )
        }
        if reference_image_path:
            files["input_image_1"] = (
                "scene_reference.png",
                self._prepare_input_image(reference_image_path),
                "image/png",
            )

        response = requests.post(
            self._endpoint(),
            headers={"Authorization": f"Bearer {settings.CLOUDFLARE_API_TOKEN}"},
            data={
                "prompt": self._build_prompt(visual_prompt, variant_index, has_reference, exact_overlay),
                "width": str(settings.CLOUDFLARE_IMAGE_WIDTH),
                "height": str(settings.CLOUDFLARE_IMAGE_HEIGHT),
            },
            files=files,
            timeout=settings.REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Cloudflare Workers AI generation failed: {response.status_code} {response.text[:300]}"
            )

        self._write_output_image(
            self._decode_image(response),
            output_path,
            source_product_overlay,
        )
        provider_name = f"{self.name}:{settings.CLOUDFLARE_IMAGE_MODEL}"
        if exact_overlay:
            provider_name += ":source_product_overlay"
        return {
            "variant_id": f"v{variant_index + 1}",
            "image_path": output_path,
            "provider": provider_name,
        }

    def _endpoint(self) -> str:
        return (
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{settings.CLOUDFLARE_ACCOUNT_ID}/ai/run/{settings.CLOUDFLARE_IMAGE_MODEL}"
        )

    def _build_prompt(
        self,
        visual_prompt: str,
        variant_index: int,
        has_reference: bool,
        exact_overlay: bool = False,
    ) -> str:
        reference_instruction = (
            "Image 1 is a scene and lighting reference only; do not copy any item from it."
            if has_reference
            else "Create the requested scene around the product in image 0."
        )
        overlay_instruction = (
            "A transparent source-product layer from image 0 will be overlaid in the final result. "
            "Maintain its exact canvas position and silhouette; generate a clean environment and external "
            "grounding shadow behind it. Do not place anything across that silhouette."
            if exact_overlay
            else "Treat the product region as a locked photographic foreground layer, not an object to redraw."
        )
        return f"""
Perform conservative background replacement for a professional ecommerce product photograph.
Image 0 is the only source of truth for the product, and its product surface must remain unchanged.
{reference_instruction}
{overlay_instruction}

Scene direction:
{visual_prompt}

Non-destructive product lock, highest priority:
- Copy the visible product identity from image 0 without redesign or retouching: same outline, geometry,
  camera angle, pose, scale, color, material finish, grain, logo, label, text, pattern, hardware, stitching,
  packaging and existing condition.
- Do not regenerate or apply environmental texture inside the product silhouette. Do not add cracks, scratches,
  creases, dents, stains, discoloration, roughness, extra grain, reflections, highlights, wear or damage.
- Do not remove, smooth, repair, conceal, or enhance existing condition details.
- Modify only pixels outside the product silhouette: background, support surface, distant props and external shadow.
- Do not cover the product, add text or graphics, add another product, add hands or people, or crop the product.

Create variant {variant_index + 1}.
"""

    def _prepare_input_image(self, path: str, prepared_image: Image.Image | None = None) -> bytes:
        if prepared_image is not None:
            image = prepared_image.copy()
        else:
            with Image.open(path) as original:
                has_alpha = original.mode in ("RGBA", "LA") or (
                    original.mode == "P" and "transparency" in original.info
                )
                image = original.convert("RGBA" if has_alpha else "RGB")
        image.thumbnail(
            (self._MAX_INPUT_EDGE, self._MAX_INPUT_EDGE),
            Image.Resampling.LANCZOS,
        )
        buffer = BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()

    def _has_transparent_foreground(self, path: str) -> bool:
        with Image.open(path) as image:
            has_alpha_channel = image.mode in ("RGBA", "LA")
            has_palette_transparency = image.mode == "P" and "transparency" in image.info
            if not has_alpha_channel and not has_palette_transparency:
                return False
            alpha = image.convert("RGBA").getchannel("A")
            minimum, maximum = alpha.getextrema()
            return minimum < 255 and maximum > 0

    def _build_source_product_overlay(self, path: str) -> Image.Image:
        canvas_width = max(256, settings.CLOUDFLARE_IMAGE_WIDTH)
        canvas_height = max(256, settings.CLOUDFLARE_IMAGE_HEIGHT)
        with Image.open(path) as source:
            foreground = source.convert("RGBA")
        bounds = foreground.getchannel("A").getbbox()
        if bounds:
            foreground = foreground.crop(bounds)
        maximum_width = round(canvas_width * 0.72)
        maximum_height = round(canvas_height * 0.72)
        scale = min(
            maximum_width / max(1, foreground.width),
            maximum_height / max(1, foreground.height),
        )
        foreground = foreground.resize(
            (
                max(1, round(foreground.width * scale)),
                max(1, round(foreground.height * scale)),
            ),
            Image.Resampling.LANCZOS,
        )
        canvas = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        position = (
            (canvas_width - foreground.width) // 2,
            max(0, canvas_height - foreground.height - round(canvas_height * 0.1)),
        )
        canvas.alpha_composite(foreground, position)
        return canvas

    def _decode_image(self, response) -> bytes:
        try:
            payload = response.json()
            result = payload.get("result", payload)
            encoded_image = result.get("image") if isinstance(result, dict) else None
            if not encoded_image:
                raise ValueError("response has no result.image value")
            encoded_image = encoded_image.split(",", 1)[-1]
            return base64.b64decode(encoded_image, validate=True)
        except (ValueError, KeyError, TypeError, binascii.Error) as exc:
            raise RuntimeError(f"Cloudflare Workers AI returned no decodable image: {exc}") from exc

    def _write_output_image(
        self,
        image_bytes: bytes,
        output_path: str,
        source_product_overlay: Image.Image | None = None,
    ) -> None:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with Image.open(BytesIO(image_bytes)) as image:
            output = image.convert("RGBA")
            if source_product_overlay is not None:
                foreground = source_product_overlay
                if foreground.size != output.size:
                    foreground = foreground.resize(output.size, Image.Resampling.LANCZOS)
                output.alpha_composite(foreground)
            output.convert("RGB").save(output_path, format="JPEG", quality=95)
