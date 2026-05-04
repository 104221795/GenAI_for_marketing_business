from abc import ABC, abstractmethod


class VisualProvider(ABC):
    name: str

    @abstractmethod
    def generate_variant(
        self,
        asset_id: str,
        variant_index: int,
        product_image_path: str,
        reference_image_path: str | None,
        visual_prompt: str,
        output_path: str,
    ) -> dict:
        pass
