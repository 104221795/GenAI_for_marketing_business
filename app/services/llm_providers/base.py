from abc import ABC, abstractmethod


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def generate(
        self,
        product_name,
        visual_prompt,
        content_prompt,
        tone,
        campaign_context=None,
        product_image_path: str | None = None,
    ) -> dict:
        pass
