from uuid import uuid4
from loguru import logger

from app.core.schemas import GenerationRequest, GenerationResult, VariantResult
from app.core.status import PENDING_REVIEW, FAILED
from app.services.visual_service import VisualService
from app.services.scoring_service import ScoringService
from app.services.llm_service import LLMService


class ProductPromotionPipeline:
    def __init__(self):
        self.visual_service = VisualService()
        self.scoring_service = ScoringService()
        self.llm_service = LLMService()

    def run(
        self,
        product_image_path: str,
        reference_image_path: str | None,
        request: GenerationRequest,
    ) -> GenerationResult:
        asset_id = str(uuid4())

        try:
            logger.info(f"Pipeline started | asset_id={asset_id}")

            variants = self.visual_service.generate_variants(
                asset_id=asset_id,
                product_image_path=product_image_path,
                reference_image_path=reference_image_path,
                visual_prompt=request.visual_prompt,
                num_variants=request.num_variants,
            )

            scored_variants = self.scoring_service.score_variants(
                variants=variants,
                visual_prompt=request.visual_prompt,
                reference_image_path=reference_image_path,
            )

            best = self.scoring_service.pick_best(scored_variants)

            content = self.llm_service.generate_product_content(
                product_name=request.product_name,
                visual_prompt=request.visual_prompt,
                content_prompt=request.content_prompt,
                tone=request.tone,
            )

            visual_provider_used = ",".join(sorted(set(v.get("provider", "unknown") for v in scored_variants)))
            llm_provider_used = content.get("provider", "unknown")

            logger.info(
                f"Pipeline completed | asset_id={asset_id} | visual_provider={visual_provider_used} | llm={llm_provider_used}"
            )

            return GenerationResult(
                asset_id=asset_id,
                status=PENDING_REVIEW,
                product_image_path=product_image_path,
                reference_image_path=reference_image_path,
                best_image_path=best["image_path"],
                variants=[VariantResult(**v) for v in scored_variants],
                best_variant_id=best["variant_id"],
                visual_provider_used=visual_provider_used,
                llm_provider_used=llm_provider_used,
                description=content["description"],
                caption=content["caption"],
                hashtags=content["hashtags"],
            )

        except Exception as exc:
            logger.exception(f"Pipeline failed | asset_id={asset_id} | error={exc}")
            return GenerationResult(
                asset_id=asset_id,
                status=FAILED,
                product_image_path=product_image_path,
                reference_image_path=reference_image_path,
                best_image_path="",
                variants=[],
                best_variant_id="",
                visual_provider_used="",
                llm_provider_used="",
                description="",
                caption="",
                hashtags=[],
                error_message=str(exc),
            )
