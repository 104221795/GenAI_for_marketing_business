from app.services.llm_providers.base import LLMProvider


class MockLLMProvider(LLMProvider):
    name = "mock"

    def generate(
        self,
        product_name,
        visual_prompt,
        content_prompt,
        tone,
        campaign_context=None,
        product_image_path: str | None = None,
    ) -> dict:
        campaign_context = campaign_context or {}
        name = product_name or "pre-owned fashion item"
        brand = campaign_context.get("brand_name") or "the shop"
        audience = campaign_context.get("target_audience") or "style-conscious buyers"
        platform = campaign_context.get("platform") or "Instagram"
        objective = campaign_context.get("marketing_objective") or "conversion"
        offer = campaign_context.get("offer") or "limited availability"
        selling_points = campaign_context.get("selling_points") or (
            "authentic product identity, stronger visual presentation, ready-to-post content"
        )

        description = (
            f"{name} is prepared for {brand} with a {tone} direction. "
            f"The campaign targets {audience}, highlights {selling_points}, and supports a "
            f"{objective} objective on {platform}."
        )
        caption = (
            f"{name} with a fresh AI-assisted product visual. "
            f"Designed for {audience}. {offer}. Message now to reserve."
        )
        hashtags = [
            "#preownedfashion",
            "#fashionmarketing",
            "#aiproductstudio",
            "#productphotography",
            "#socialcommerce",
        ]
        channel_outputs = {
            "seo_title": f"{name} | AI-ready product listing",
            "product_description": description,
            "instagram_caption": caption,
            "facebook_ad": (
                f"Looking for a standout fashion item? {name} is presented with a clean "
                f"marketing visual and a {tone} story for {audience}. {offer}."
            ),
            "tiktok_script": (
                f"Hook: Need a product photo that sells?\n"
                f"Scene 1: Show the original {name}.\n"
                f"Scene 2: Reveal the AI-edited marketing visual.\n"
                f"CTA: Check the item before it is gone."
            ),
            "shopee_description": (
                f"{name}\nKey selling points: {selling_points}\nTone: {tone}\nOffer: {offer}"
            ),
            "email_subject": f"New arrival: {name}",
            "cta_suggestions": ["Message to buy", "Reserve this item", "View product details"],
            "hashtags": hashtags,
        }

        return {
            "provider": self.name,
            "description": description,
            "caption": caption,
            "hashtags": hashtags,
            "channel_outputs": channel_outputs,
        }
