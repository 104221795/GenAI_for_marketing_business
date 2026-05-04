from pathlib import Path
from io import BytesIO
from PIL import Image
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

        response = client.models.generate_content(
            model=settings.GEMINI_IMAGE_MODEL,
            contents=contents,
        )

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        for part in response.candidates[0].content.parts:
            if getattr(part, "inline_data", None) is not None:
                img = Image.open(BytesIO(part.inline_data.data))
                img.convert("RGB").save(output_path, quality=95)
                return {
                    "variant_id": f"v{variant_index + 1}",
                    "image_path": output_path,
                    "provider": self.name,
                }

        raise RuntimeError("Gemini image provider returned no image")

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

Hard constraints:
- Preserve the same product identity.
- Preserve visible logo, sponsor text, color, collar, sleeves, fabric texture and product details.
- Do not invent a different product.
- Do not add a person.
- Do not hang the shirt unless the prompt asks for it.
- Make the final image look like a natural product marketing photograph, not a sticker pasted on a background.
- Match realistic perspective, realistic shadows, realistic wrinkles and lighting.
- Output only the edited image.

Variant:
Create variant {variant_index + 1} with slightly different lighting/composition while preserving the same target style.
'''
