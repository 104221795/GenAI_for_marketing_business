from uuid import uuid4
from loguru import logger

from app.core.schemas import GenerationRequest, GenerationResult, VariantResult
from app.core.status import GENERATED, FAILED
from app.services.visual_service import VisualService
from app.services.scoring_service import ScoringService
from app.services.llm_gateway import LLMGateway


class ProductPromotionPipeline:
    def __init__(self):
        self.visual_service = VisualService()
        self.scoring_service = ScoringService()
        self.llm_service = LLMGateway()

    def run(
        self,
        product_image_path: str,
        reference_image_path: str | None,
        request: GenerationRequest,
    ) -> GenerationResult:
        asset_id = str(uuid4())
        campaign_context = self._campaign_context(request)
        enriched_visual_prompt = self._build_visual_prompt(request, campaign_context)

        try:
            logger.info(f"Pipeline started | asset_id={asset_id}")

            variants = self.visual_service.generate_variants(
                asset_id=asset_id,
                product_image_path=product_image_path,
                reference_image_path=reference_image_path,
                visual_prompt=enriched_visual_prompt,
                num_variants=request.num_variants,
            )

            scored_variants = self.scoring_service.score_variants(
                variants=variants,
                visual_prompt=enriched_visual_prompt,
                reference_image_path=reference_image_path,
                product_image_path=product_image_path,
            )

            best = self.scoring_service.pick_best(scored_variants)
            quality_report = self.scoring_service.build_quality_report(
                scored_variants=scored_variants,
                best_variant_id=best["variant_id"],
                campaign_context=campaign_context,
            )

            content = self.llm_service.generate_product_content(
                product_name=request.product_name,
                visual_prompt=enriched_visual_prompt,
                content_prompt=request.content_prompt,
                tone=request.tone,
                campaign_context=campaign_context,
                product_image_path=product_image_path,
            )

            visual_provider_used = ",".join(sorted(set(v.get("provider", "unknown") for v in scored_variants)))
            llm_provider_used = content.get("provider", "unknown")

            logger.info(
                f"Pipeline completed | asset_id={asset_id} | visual_provider={visual_provider_used} | llm={llm_provider_used}"
            )

            return GenerationResult(
                asset_id=asset_id,
                status=GENERATED,
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
                channel_outputs=content["channel_outputs"],
                quality_report=quality_report,
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
                channel_outputs={},
                quality_report={},
                error_message=str(exc),
            )

    def _campaign_context(self, request: GenerationRequest) -> dict:
        return {
            "campaign_name": request.campaign_name,
            "brand_name": request.brand_name,
            "target_audience": request.target_audience,
            "customer_persona": request.customer_persona,
            "platform": request.platform,
            "marketing_objective": request.marketing_objective,
            "funnel_stage": request.funnel_stage,
            "copy_framework": request.copy_framework,
            "selling_points": request.selling_points,
            "price": request.price,
            "offer": request.offer,
            "language": request.language,
            "compliance_notes": request.compliance_notes,
        }

    def _build_visual_prompt(self, request: GenerationRequest, campaign_context: dict) -> str:
        # Image editors need a controlled visual specification; sales metadata causes prompt drift.
        return request.visual_prompt
