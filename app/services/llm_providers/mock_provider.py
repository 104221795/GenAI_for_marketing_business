from app.services.llm_providers.base import LLMProvider


class MockLLMProvider(LLMProvider):
    name = "mock"

    def generate(self, product_name, visual_prompt, content_prompt, tone) -> dict:
        name = product_name or "sản phẩm thời trang pre-owned"
        return {
            "provider": self.name,
            "description": (
                f"{name} được tái hiện theo concept: {visual_prompt}. "
                f"Hình ảnh được tối ưu cho mục tiêu quảng bá sản phẩm, giữ trọng tâm vào sản phẩm thật "
                f"và nâng cảm giác chuyên nghiệp cho kênh truyền thông."
            ),
            "caption": (
                f"{name} – item độc bản được nâng cấp bằng reference-based AI image editing. "
                f"Phong cách: {tone}. Sẵn sàng cho social post, catalogue và chiến dịch bán hàng."
            ),
            "hashtags": [
                "#preownedfashion",
                "#luxurythrift",
                "#sustainablefashion",
                "#aiproductstudio",
                "#referencebasedediting",
            ],
        }
