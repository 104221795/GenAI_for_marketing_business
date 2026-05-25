from PIL import Image, ImageStat
import numpy as np
from loguru import logger


class ScoringService:
    def score_variants(
        self,
        variants: list[dict],
        visual_prompt: str,
        reference_image_path: str | None,
        product_image_path: str | None = None,
    ) -> list[dict]:
        logger.info("Scoring variants")
        scored = []

        for variant in variants:
            technical_diagnostics = self._technical_diagnostics(
                image_path=variant["image_path"],
                product_image_path=product_image_path,
                provider=variant.get("provider"),
            )
            scores = self._score_one(
                image_path=variant["image_path"],
                reference_image_path=reference_image_path,
                provider=variant.get("provider"),
                technical_diagnostics=technical_diagnostics,
            )
            scored.append(
                {
                    **variant,
                    "scores": scores,
                    "technical_diagnostics": technical_diagnostics,
                }
            )

        return scored

    def pick_best(self, scored_variants: list[dict]) -> dict:
        return max(scored_variants, key=lambda x: x["scores"]["final_score"])

    def build_quality_report(self, scored_variants: list[dict], best_variant_id: str, campaign_context: dict) -> dict:
        if not scored_variants:
            return {
                "summary": "No variants were available for quality evaluation.",
                "scorecard": {},
                "recommendations": ["Regenerate with at least one visual provider available."],
            }

        best = next(
            (variant for variant in scored_variants if variant["variant_id"] == best_variant_id),
            scored_variants[0],
        )
        best_scores = best.get("scores", {})
        technical_diagnostics = best.get("technical_diagnostics", {})
        identity_assurance = self._identity_assurance(best.get("provider"))
        average_score = sum(
            variant.get("scores", {}).get("final_score", 0.0)
            for variant in scored_variants
        ) / len(scored_variants)

        recommendations = []
        if identity_assurance["requires_identity_review"]:
            recommendations.append(
                "Required before approval: compare product surfaces, logos, labels, and condition with the original image."
            )
        if technical_diagnostics.get("clipped_pixel_rate", 0) > 0.12:
            recommendations.append("Check for blown highlights or crushed shadows before publishing.")
        if technical_diagnostics.get("detail_signal", 1) < 0.2:
            recommendations.append("Inspect sharpness and product-detail clarity; the output may be too soft.")
        if best_scores.get("reference_palette_similarity_proxy", 1) < 0.7:
            recommendations.append("The generated palette differs from the supplied scene reference.")
        if not recommendations:
            recommendations.append("Ready for human review before export.")

        return {
            "summary": (
                f"Best variant {best_variant_id} has an automated technical-readiness score of {best_scores.get('final_score', 0):.4f} "
                f"with an average variant score of {average_score:.4f}. "
                f"{identity_assurance['message']}"
            ),
            "best_variant_id": best_variant_id,
            "best_provider": best.get("provider"),
            "scorecard": best_scores,
            "technical_diagnostics": technical_diagnostics,
            "average_final_score": round(average_score, 4),
            "identity_assurance": identity_assurance,
            "approval_gate": (
                "blocked_pending_identity_review"
                if identity_assurance["requires_identity_review"]
                else "human_review_required"
            ),
            "evaluation_dimensions": [
                "contrast_readability_proxy",
                "exposure_balance_proxy",
                "clipping_quality_proxy",
                "detail_signal",
                "resolution_sufficiency_proxy",
                "reference_palette_similarity_proxy",
            ],
            "campaign_fit": {
                "platform": campaign_context.get("platform"),
                "objective": campaign_context.get("marketing_objective"),
                "funnel_stage": campaign_context.get("funnel_stage"),
                "copy_framework": campaign_context.get("copy_framework"),
            },
            "recommendations": recommendations,
            "disclaimer": (
                "Automated screening measures technical image signals only. It cannot judge prompt accuracy, "
                "scene realism, or product identity; those are measured in the saved human image-model evaluation."
            ),
        }

    def _score_one(
        self,
        image_path: str,
        reference_image_path: str | None,
        provider: str | None,
        technical_diagnostics: dict,
    ) -> dict:
        img = Image.open(image_path).convert("RGB")
        stat = ImageStat.Stat(img)

        contrast = sum(stat.stddev) / 3
        contrast_readability_proxy = min(1.0, max(0.0, contrast / 70))
        source_layer_retained = bool(provider and "source_product_overlay" in provider)
        reference_palette_similarity_proxy = self._reference_similarity(img, reference_image_path)

        final_score = (
            contrast_readability_proxy * 0.20
            + technical_diagnostics["exposure_balance_proxy"] * 0.20
            + technical_diagnostics["clipping_quality_proxy"] * 0.20
            + technical_diagnostics["detail_signal"] * 0.15
            + technical_diagnostics["resolution_sufficiency_proxy"] * 0.15
            + reference_palette_similarity_proxy * 0.10
        )

        return {
            "contrast_readability_proxy": round(contrast_readability_proxy, 4),
            "exposure_balance_proxy": technical_diagnostics["exposure_balance_proxy"],
            "clipping_quality_proxy": technical_diagnostics["clipping_quality_proxy"],
            "detail_signal": technical_diagnostics["detail_signal"],
            "resolution_sufficiency_proxy": technical_diagnostics["resolution_sufficiency_proxy"],
            "reference_palette_similarity_proxy": round(min(reference_palette_similarity_proxy, 1.0), 4),
            "source_layer_retained_indicator": 1.0 if source_layer_retained else 0.0,
            "final_score": round(min(final_score, 1.0), 4),
        }

    def _technical_diagnostics(
        self,
        image_path: str,
        product_image_path: str | None,
        provider: str | None,
    ) -> dict:
        image = Image.open(image_path).convert("RGB")
        grayscale = np.asarray(image.convert("L"), dtype="float32") / 255.0
        brightness = float(grayscale.mean())
        clipped_pixel_rate = float(
            np.logical_or(grayscale < (8 / 255), grayscale > (247 / 255)).mean()
        )
        horizontal_edges = np.abs(np.diff(grayscale, axis=1)).mean() if image.width > 1 else 0.0
        vertical_edges = np.abs(np.diff(grayscale, axis=0)).mean() if image.height > 1 else 0.0
        detail_signal = min(1.0, float((horizontal_edges + vertical_edges) / 0.16))
        exposure_balance_proxy = max(0.0, 1.0 - abs(brightness - 0.5) / 0.5)
        clipping_quality_proxy = max(0.0, 1.0 - min(1.0, clipped_pixel_rate * 4))
        megapixels = image.width * image.height / 1_000_000
        resolution_sufficiency_proxy = min(1.0, megapixels / 1.0)

        scene_change_signal = None
        if product_image_path:
            try:
                source = Image.open(product_image_path).convert("RGB").resize((128, 128))
                output = image.resize((128, 128))
                source_arr = np.asarray(source, dtype="float32") / 255.0
                output_arr = np.asarray(output, dtype="float32") / 255.0
                scene_change_signal = round(float(np.abs(source_arr - output_arr).mean()), 4)
            except Exception:
                scene_change_signal = None

        return {
            "output_dimensions": f"{image.width}x{image.height}",
            "megapixels": round(megapixels, 4),
            "exposure_balance_proxy": round(exposure_balance_proxy, 4),
            "clipped_pixel_rate": round(clipped_pixel_rate, 4),
            "clipping_quality_proxy": round(clipping_quality_proxy, 4),
            "detail_signal": round(detail_signal, 4),
            "resolution_sufficiency_proxy": round(resolution_sufficiency_proxy, 4),
            "scene_change_signal": scene_change_signal,
            "source_layer_retained": bool(provider and "source_product_overlay" in provider),
            "interpretation": (
                "Scene-change and technical signals do not isolate the product silhouette; "
                "use human side-by-side evaluation for fidelity."
            ),
        }

    def _reference_similarity(self, img: Image.Image, reference_image_path: str | None) -> float:
        if not reference_image_path:
            return 0.75

        try:
            ref = Image.open(reference_image_path).convert("RGB").resize((128, 128))
            out = img.convert("RGB").resize((128, 128))

            ref_arr = np.asarray(ref).astype("float32") / 255.0
            out_arr = np.asarray(out).astype("float32") / 255.0

            ref_mean = ref_arr.mean(axis=(0, 1))
            out_mean = out_arr.mean(axis=(0, 1))

            distance = float(np.linalg.norm(ref_mean - out_mean))
            return max(0.0, 1.0 - distance)
        except Exception:
            return 0.75

    def _identity_assurance(self, provider: str | None) -> dict:
        if provider and "source_product_overlay" in provider:
            return {
                "status": "source_product_layer_retained",
                "requires_identity_review": False,
                "message": "The original transparent product layer was retained in the composed image.",
            }
        if provider == "original_fallback":
            return {
                "status": "original_image_returned",
                "requires_identity_review": False,
                "message": "No generated scene was applied; the returned image is the original product photo.",
            }
        if provider == "mock":
            return {
                "status": "demo_output_only",
                "requires_identity_review": True,
                "message": "This is a demonstration output and is not approved for product accuracy.",
            }
        return {
            "status": "unverified_ai_edit",
            "requires_identity_review": True,
            "message": "Product identity is not automatically verified for this AI-edited image.",
        }
