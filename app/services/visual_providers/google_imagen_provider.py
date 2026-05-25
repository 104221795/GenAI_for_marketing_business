from pathlib import Path

from PIL import Image
from loguru import logger

from app.config import settings
from app.services.visual_providers.base import VisualProvider


class GoogleImagenProvider(VisualProvider):
    name = "google_imagen"

    def generate_variant(
        self,
        asset_id: str,
        variant_index: int,
        product_image_path: str,
        reference_image_path: str | None,
        visual_prompt: str,
        output_path: str,
    ) -> dict:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("Missing GEMINI_API_KEY")

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        product_summary = self._describe_product(client, product_image_path)
        reference_summary = self._describe_reference(client, reference_image_path)
        prompt = self._build_prompt(
            visual_prompt=visual_prompt,
            variant_index=variant_index,
            reference_image_path=reference_image_path,
            product_summary=product_summary,
            reference_summary=reference_summary,
        )

        response = client.models.generate_images(
            model=settings.GOOGLE_IMAGEN_MODEL,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=settings.GOOGLE_IMAGEN_ASPECT_RATIO,
            ),
        )

        generated_images = getattr(response, "generated_images", None) or []
        if not generated_images:
            raise RuntimeError("Google Imagen returned no images")

        image = generated_images[0].image
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        image_bytes = getattr(image, "image_bytes", None)
        if image_bytes:
            Path(output_path).write_bytes(image_bytes)
        else:
            image.save(output_path)

        # Normalize to RGB JPG so the rest of the pipeline can treat providers consistently.
        Image.open(output_path).convert("RGB").save(output_path, quality=95)

        return {
            "variant_id": f"v{variant_index + 1}",
            "image_path": output_path,
            "provider": f"{self.name}:{settings.GOOGLE_IMAGEN_MODEL}",
        }

    def _describe_product(self, client, product_image_path: str) -> str:
        try:
            product_image = Image.open(product_image_path).convert("RGB")
            response = client.models.generate_content(
                model=settings.GEMINI_TEXT_MODEL,
                contents=[
                    """
Describe this product for a luxury product photography generator.
Focus on product category, shape, color, material, texture, visible logo/text placement,
condition details, silhouette, and details that must remain visually consistent.
Return a concise paragraph. Do not invent a brand if it is not visible.
""",
                    product_image,
                ],
            )
            return response.text.strip()
        except Exception as exc:
            logger.warning(f"Google Imagen fallback could not describe product input | error={type(exc).__name__}: {exc}")
            return ""

    def _describe_reference(self, client, reference_image_path: str | None) -> str:
        if not reference_image_path:
            return ""

        try:
            reference_image = Image.open(reference_image_path).convert("RGB")
            response = client.models.generate_content(
                model=settings.GEMINI_TEXT_MODEL,
                contents=[
                    """
Describe this reference image as a product photography style guide.
Focus on composition, camera angle, background, lighting, surface, color mood, spacing, and styling props.
Return a concise paragraph.
""",
                    reference_image,
                ],
            )
            return response.text.strip()
        except Exception as exc:
            logger.warning(f"Google Imagen fallback could not describe reference input | error={type(exc).__name__}: {exc}")
            return ""

    def _build_prompt(
        self,
        visual_prompt: str,
        variant_index: int,
        reference_image_path: str | None,
        product_summary: str,
        reference_summary: str,
    ) -> str:
        reference_note = (
            "A separate reference image was uploaded. Its style summary is included below."
            if reference_image_path
            else "No reference image is available to Imagen."
        )
        product_context = product_summary or "No reliable product-image description was available. Follow the written product direction carefully."
        reference_context = reference_summary or "No reliable reference-image description was available. Follow the written visual direction carefully."

        return f"""
Create a premium luxury product marketing image.

Important limitation:
Google Imagen through the Gemini API is used here as an input-aware fallback, not pixel-level image editing.
The uploaded product/reference images were summarized by a vision model, then passed into this prompt.
Preserve the described product identity as closely as possible, but do not invent brand marks or false details.

{reference_note}

Product image summary:
{product_context}

Reference/style summary:
{reference_context}

Visual direction:
{visual_prompt}

Variant instruction:
Create variant {variant_index + 1} with a distinct but commercially usable composition.

Quality requirements:
- Realistic luxury product photography.
- Clear product focus.
- Premium lighting and believable shadows.
- Clean ecommerce/social commerce composition.
- No people unless the prompt explicitly asks for a person.
- Avoid fake logos, misleading brand claims, or unreadable text.
"""
