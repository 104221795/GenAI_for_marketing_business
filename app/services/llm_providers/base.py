from abc import ABC, abstractmethod


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def generate(self, product_name, visual_prompt, content_prompt, tone) -> dict:
        pass
