from pathlib import Path
from io import BytesIO
from PIL import Image
from loguru import logger
from app.config import settings
from app.services.visual_providers.base import VisualProvider


class GeminiImageProvider(VisualProvider):
    name = "gemini_image"

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

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        product_image = Image.open(product_image_path).convert("RGB")

        contents = [
            self._build_prompt(visual_prompt, variant_index, has_reference=bool(reference_image_path)),
            product_image,
        ]

        if reference_image_path:
            reference_image = Image.open(reference_image_path).convert("RGB")
            contents.append(reference_image)

        errors = []
        for model_name in self._model_chain():
            try:
                logger.info(
                    f"Trying Gemini image model | model={model_name} | variant={variant_index + 1}"
                )
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                )
                saved = self._save_first_image(response, output_path)
                if saved:
                    return {
                        "variant_id": f"v{variant_index + 1}",
                        "image_path": output_path,
                        "provider": f"{self.name}:{model_name}",
                    }
                errors.append(f"{model_name}: returned no image")
            except Exception as exc:
                error = str(exc).replace("\n", " ").strip()
                if len(error) > 220:
                    error = error[:220] + "..."
                logger.warning(f"Gemini image model failed | model={model_name} | error={error}")
                errors.append(f"{model_name}: {type(exc).__name__}: {error}")

        raise RuntimeError("All Gemini image models failed: " + " | ".join(errors))

    def _model_chain(self) -> list[str]:
        chain = settings.GEMINI_IMAGE_MODEL_CHAIN or settings.GEMINI_IMAGE_MODEL
        models = [model.strip() for model in chain.split(",") if model.strip()]
        if settings.GEMINI_IMAGE_MODEL and settings.GEMINI_IMAGE_MODEL not in models:
            models.insert(0, settings.GEMINI_IMAGE_MODEL)
        return models or ["gemini-2.5-flash-image"]

    def _save_first_image(self, response, output_path: str) -> bool:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        parts = getattr(response, "parts", None)
        if parts is None and getattr(response, "candidates", None):
            parts = response.candidates[0].content.parts

        for part in parts or []:
            if getattr(part, "inline_data", None) is not None:
                img = Image.open(BytesIO(part.inline_data.data))
                img.convert("RGB").save(output_path, quality=95)
                return True

        return False

    def _build_prompt(self, visual_prompt: str, variant_index: int, has_reference: bool) -> str:
        reference_instruction = (
            "Use the second uploaded image as the target composition, format, camera angle, lighting style, and visual reference."
            if has_reference
            else "No separate reference image is provided, so infer a premium product photography composition from the prompt."
        )

        return f'''
You are an expert product photography image editor.

Use the first uploaded image as the exact product identity.
{reference_instruction}

Editing instruction:
{visual_prompt}

Non-destructive product lock, highest priority:
- Treat the product as a locked photographic foreground layer. Preserve the exact product category, silhouette, proportions, geometry, orientation, camera angle, color, material, texture, logo, label, readable text, pattern, hardware, stitching, packaging, and visible condition.
- Treat the first image as the only source of truth for the product. Use a second image only for composition and atmosphere.
- Change only pixels outside the product silhouette: the background, supporting surface, external shadow, and non-obscuring scene props requested in the instruction.
- Do not re-render, retouch, relight, invent, redesign, recolor, repair, rebrand, relabel, or cover any part of the product.
- Do not add cracks, scratches, creases, dents, stains, discoloration, extra texture, new reflections, new wear, or damage to the product.
- Do not remove or hide condition details already visible in the source.
- Do not add a person.
- Make the background and external grounding shadow look like a natural product marketing photograph without altering the product surface.
- Output only the edited image.

Variant:
Create variant {variant_index + 1} with slightly different lighting/composition while preserving the same target style.
'''
