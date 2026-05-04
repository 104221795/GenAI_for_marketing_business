from pathlib import Path
from PIL import Image, ImageEnhance, ImageDraw, ImageFilter
from app.services.visual_providers.base import VisualProvider


class MockVisualProvider(VisualProvider):
    name = "mock"

    def generate_variant(
        self,
        asset_id: str,
        variant_index: int,
        product_image_path: str,
        reference_image_path: str | None,
        visual_prompt: str,
        output_path: str,
    ) -> dict:
        product = Image.open(product_image_path).convert("RGBA")
        product.thumbnail((850, 850))

        if reference_image_path:
            bg = Image.open(reference_image_path).convert("RGB").resize((1280, 1280))
            bg = bg.filter(ImageFilter.GaussianBlur(radius=2))
        else:
            bg = Image.new("RGB", (1280, 1280), (70, 120, 60))
            draw_bg = ImageDraw.Draw(bg)
            for i in range(0, 1280, 28):
                draw_bg.line([i, 0, i + 250, 1280], fill=(80, 140, 70), width=3)
            draw_bg.ellipse([850, 60, 1220, 430], fill=(250, 230, 160))

        overlay = Image.new("RGBA", (1280, 1280), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        product = ImageEnhance.Contrast(product).enhance(1.08 + variant_index * 0.02)
        product = ImageEnhance.Sharpness(product).enhance(1.12)

        x = (1280 - product.width) // 2
        y = (1280 - product.height) // 2 + 70

        draw.ellipse([310, 1015, 970, 1135], fill=(0, 0, 0, 70))
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=10))
        bg_rgba = Image.alpha_composite(bg.convert("RGBA"), overlay)
        bg_rgba.alpha_composite(product, (x, y))

        draw_final = ImageDraw.Draw(bg_rgba)
        draw_final.text((40, 40), "MOCK FALLBACK - use Gemini Image / FLUX for real editing", fill=(255,255,255,255))
        draw_final.text((40, 75), f"Variant {variant_index + 1}", fill=(255,255,255,255))

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        bg_rgba.convert("RGB").save(output_path, quality=95)

        return {
            "variant_id": f"v{variant_index + 1}",
            "image_path": output_path,
            "provider": self.name,
        }
