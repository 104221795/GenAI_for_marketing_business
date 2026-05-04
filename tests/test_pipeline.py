from pathlib import Path
from PIL import Image
from app.core.pipeline import ProductPromotionPipeline
from app.core.schemas import GenerationRequest


def test_pipeline_runs(tmp_path):
    product_path = tmp_path / "product.jpg"
    Image.new("RGB", (300, 300), (255, 0, 0)).save(product_path)

    req = GenerationRequest(
        product_name="Test Shirt",
        visual_prompt="Put this shirt naturally on a grass field.",
        content_prompt="Write caption",
        num_variants=1,
    )

    result = ProductPromotionPipeline().run(str(product_path), None, req)
    assert result.status in ["pending_review", "failed"]
