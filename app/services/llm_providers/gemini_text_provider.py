import json

from loguru import logger
from PIL import Image
from pydantic import BaseModel, Field

from app.config import settings
from app.services.llm_providers.base import LLMProvider


class ChannelOutputs(BaseModel):
    seo_title: str = ""
    product_description: str = ""
    instagram_caption: str = ""
    facebook_ad: str = ""
    tiktok_script: str = ""
    shopee_description: str = ""
    email_subject: str = ""
    cta_suggestions: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)


class ProductAnalysis(BaseModel):
    detected_product_type: str = ""
    observed_description: str = ""
    visible_details: list[str] = Field(default_factory=list)
    condition_observations: list[str] = Field(default_factory=list)
    buyer_appeal_points: list[str] = Field(default_factory=list)
    unknown_or_unverified: list[str] = Field(default_factory=list)


class MarketingContent(BaseModel):
    product_analysis: ProductAnalysis = Field(default_factory=ProductAnalysis)
    description: str = ""
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    channel_outputs: ChannelOutputs = Field(default_factory=ChannelOutputs)


class GeminiTextProvider(LLMProvider):
    name = "gemini_text"

    def generate(
        self,
        product_name,
        visual_prompt,
        content_prompt,
        tone,
        campaign_context=None,
        product_image_path: str | None = None,
    ) -> dict:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("Missing GEMINI_API_KEY")

        from google import genai

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        prompt = self._build_prompt(
            product_name=product_name,
            visual_prompt=visual_prompt,
            content_prompt=content_prompt,
            tone=tone,
            campaign_context=campaign_context or {},
            has_product_image=bool(product_image_path),
        )
        contents = [prompt]
        if product_image_path:
            contents.append(self._load_product_image(product_image_path))
        errors = []

        for model_name in self._model_chain():
            try:
                logger.info(f"Trying Gemini text model | model={model_name}")
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config={
                        "response_mime_type": "application/json",
                        "response_json_schema": MarketingContent.model_json_schema(),
                    },
                )
                content = MarketingContent.model_validate_json(response.text)
                return {
                    "provider": f"{self.name}:{model_name}",
                    "product_analysis": content.product_analysis.model_dump(),
                    "description": content.description,
                    "caption": content.caption,
                    "hashtags": content.hashtags,
                    "channel_outputs": content.channel_outputs.model_dump(),
                }
            except Exception as exc:
                error = self._safe_error(exc)
                errors.append(f"{model_name}: {error}")
                logger.warning(f"Gemini text model failed | model={model_name} | error={error}")
                if self._is_account_error(error):
                    break

        raise RuntimeError("All Gemini text models failed: " + " | ".join(errors))

    def _model_chain(self) -> list[str]:
        configured = settings.GEMINI_TEXT_MODEL_CHAIN or settings.GEMINI_TEXT_MODEL
        models = [model.strip() for model in configured.split(",") if model.strip()]
        if settings.GEMINI_TEXT_MODEL and settings.GEMINI_TEXT_MODEL not in models:
            models.insert(0, settings.GEMINI_TEXT_MODEL)
        return list(dict.fromkeys(models)) or ["gemini-2.5-flash-lite"]

    def _build_prompt(
        self,
        product_name,
        visual_prompt,
        content_prompt,
        tone,
        campaign_context: dict,
        has_product_image: bool = False,
    ) -> str:
        name = product_name or "featured product"
        image_instruction = (
            """
An original uploaded product image is attached. Inspect only that original image for product facts.
First produce `product_analysis`: identify the likely product type and describe visible color, shape,
texture/finish, silhouette, hardware, label/text placement, packaging, and visible condition where readable.
List uncertain or invisible details under `unknown_or_unverified`; never convert guesses into claims.
Use observed details and seller-supplied facts to write persuasive copy that helps a buyer understand
why the item is attractive, while staying truthful about condition and identity.
"""
            if has_product_image
            else """
No product image is attached to this text request. Do not claim visual observation. Base all copy only
on seller-supplied campaign facts and list unavailable product-specific facts under `unknown_or_unverified`.
"""
        )
        return f"""
You are a careful ecommerce product analyst and conversion copywriter.

Product name: {name}
Campaign context JSON:
{json.dumps(campaign_context, ensure_ascii=False, indent=2)}
Visual concept: {visual_prompt}
User task: {content_prompt}
Tone: {tone}

{image_instruction}

Write richly descriptive but readable marketing copy in the requested language. Make the product appealing
through specific visible design details, styling value, and a practical call to action.
Never invent brand authenticity, official affiliation, material composition, dimensions, functionality,
condition grading, discount, scarcity, or included accessories when they are not supplied or clearly visible.
Do not describe any background generated by the image model as a product attribute.
"""

    def _load_product_image(self, product_image_path: str) -> Image.Image:
        with Image.open(product_image_path) as source:
            image = source.convert("RGBA")
        if image.getchannel("A").getextrema()[0] < 255:
            white_background = Image.new("RGBA", image.size, (255, 255, 255, 255))
            white_background.alpha_composite(image)
            image = white_background
        return image.convert("RGB")

    def _safe_error(self, exc: Exception) -> str:
        message = str(exc).replace("\n", " ").strip()
        return message[:240] + "..." if len(message) > 240 else message

    def _is_account_error(self, error: str) -> bool:
        text = error.lower()
        return any(marker in text for marker in ["401", "402", "429", "quota", "billing", "resource_exhausted"])
