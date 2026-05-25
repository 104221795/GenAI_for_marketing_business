import base64
import json
from io import BytesIO

from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.core.schemas import ImageEvaluationRequest
from app.database import Base
from app.repositories.models import Asset
from app.services.llm_gateway import LLMGateway
from app.services.llm_providers.gemini_text_provider import GeminiTextProvider
from app.services.scoring_service import ScoringService
from app.services.visual_providers.cloudflare_flux_provider import CloudflareFluxProvider
from app.services.visual_providers.replicate_flux_provider import ReplicateFluxProvider
from app.services.visual_service import VisualService
from app.main import (
    _build_image_evaluation,
    _can_export_asset,
    _requires_identity_verification,
    image_model_evaluation_summary,
    record_image_evaluation,
)


def save_test_image(path, color, size=(60, 60)):
    Image.new("RGB", size, color).save(path)
    # Ensure the file is fully written before proceeding, which can be an issue on some filesystems


def test_visual_service_returns_original_when_editor_is_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "VISUAL_PROVIDER_CHAIN", "replicate_flux,original")
    monkeypatch.setattr(settings, "REPLICATE_API_TOKEN", None)
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))
    product_path = tmp_path / "product.jpg"
    save_test_image(product_path, (32, 64, 96))

    result = VisualService().generate_variants(
        asset_id="safe-fallback",
        product_image_path=str(product_path),
        reference_image_path=None,
        visual_prompt="Place the item on a neutral surface.",
        num_variants=1,
    )[0]

    assert result["provider"] == "original_fallback"
    assert Image.open(result["image_path"]).size == (60, 60)


def test_cloudflare_flux_uses_product_and_scene_reference(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "CLOUDFLARE_ACCOUNT_ID", "account-id")
    monkeypatch.setattr(settings, "CLOUDFLARE_API_TOKEN", "test-token")
    monkeypatch.setattr(settings, "CLOUDFLARE_IMAGE_WIDTH", 1024)
    monkeypatch.setattr(settings, "CLOUDFLARE_IMAGE_HEIGHT", 1024)
    product_path = tmp_path / "product.jpg" # Create a test product image larger than 512px to verify resizing will provide with png, pdf, et

    reference_path = tmp_path / "reference.jpg"
    output_path = tmp_path / "output.jpg"
    save_test_image(product_path, (32, 64, 96), (900, 600))
    save_test_image(reference_path, (200, 180, 150), (700, 700))

    result_buffer = BytesIO()
    Image.new("RGB", (80, 80), (90, 90, 90)).save(result_buffer, format="PNG")
    encoded_result = base64.b64encode(result_buffer.getvalue()).decode("ascii")
    captured = {}

    class FakeResponse:
        status_code = 200
        text = ""

        def json(self):
            return {"success": True, "result": {"image": encoded_result}}

    def fake_post(url, headers, data, files, timeout):
        captured.update(url=url, headers=headers, data=data, files=files, timeout=timeout)
        return FakeResponse()

    monkeypatch.setattr(
        "app.services.visual_providers.cloudflare_flux_provider.requests.post",
        fake_post,
    )

    result = CloudflareFluxProvider().generate_variant(
        asset_id="cloudflare-reference",
        variant_index=0,
        product_image_path=str(product_path),
        reference_image_path=str(reference_path),
        visual_prompt="Place the item on pale travertine in soft daylight.",
        output_path=str(output_path),
    )

    assert captured["url"].endswith("/@cf/black-forest-labs/flux-2-klein-4b")
    assert captured["data"]["width"] == "1024"
    assert "input_image_0" in captured["files"]
    assert "input_image_1" in captured["files"]
    assert "Image 0 is the only source of truth" in captured["data"]["prompt"]
    assert "Do not add cracks, scratches" in captured["data"]["prompt"]
    with Image.open(BytesIO(captured["files"]["input_image_0"][1])) as prepared_product:
        assert max(prepared_product.size) < 512
    assert Image.open(result["image_path"]).format == "JPEG"
    assert result["provider"].startswith("cloudflare_flux:")


def test_cloudflare_transparent_product_restores_source_layer(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "CLOUDFLARE_ACCOUNT_ID", "account-id")
    monkeypatch.setattr(settings, "CLOUDFLARE_API_TOKEN", "test-token")
    product_path = tmp_path / "transparent_product.png"
    output_path = tmp_path / "overlay_output.jpg"
    product = Image.new("RGBA", (80, 80), (0, 0, 0, 0))
    for x in range(20, 60):
        for y in range(18, 62):
            product.putpixel((x, y), (238, 22, 12, 255))
    product.save(product_path)

    scene_buffer = BytesIO()
    Image.new("RGB", (80, 80), (18, 52, 180)).save(scene_buffer, format="PNG")
    encoded_scene = base64.b64encode(scene_buffer.getvalue()).decode("ascii")
    captured = {}

    class FakeResponse:
        status_code = 200
        text = ""

        def json(self):
            return {"result": {"image": encoded_scene}}

    def fake_post(url, headers, data, files, timeout):
        captured["prompt"] = data["prompt"]
        return FakeResponse()

    monkeypatch.setattr(
        "app.services.visual_providers.cloudflare_flux_provider.requests.post",
        fake_post,
    )

    result = CloudflareFluxProvider().generate_variant(
        asset_id="pixel-source",
        variant_index=0,
        product_image_path=str(product_path),
        reference_image_path=None,
        visual_prompt="Clean studio background.",
        output_path=str(output_path),
    )

    output = Image.open(output_path).convert("RGB")
    center = output.getpixel((40, 40))
    corner = output.getpixel((5, 5))
    assert result["provider"].endswith(":source_product_overlay")
    assert "transparent source-product layer" in captured["prompt"]
    assert center[0] > 210 and center[2] < 40
    assert corner[2] > 150 and corner[0] < 50


def test_cloudflare_missing_credentials_falls_back_to_original(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "VISUAL_PROVIDER_CHAIN", "cloudflare_flux,original")
    monkeypatch.setattr(settings, "CLOUDFLARE_ACCOUNT_ID", None)
    monkeypatch.setattr(settings, "CLOUDFLARE_API_TOKEN", None)
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))
    product_path = tmp_path / "product.jpg"
    save_test_image(product_path, (32, 64, 96))

    result = VisualService().generate_variants(
        asset_id="cloudflare-fallback",
        product_image_path=str(product_path),
        reference_image_path=None,
        visual_prompt="Place the item on a neutral surface.",
        num_variants=1,
    )[0]

    assert result["provider"] == "original_fallback"


def test_flux_uses_multi_image_model_for_style_reference(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "REPLICATE_API_TOKEN", "test-token")
    monkeypatch.setattr(
        settings,
        "REPLICATE_FLUX_REFERENCE_MODEL_CHAIN",
        "flux-kontext-apps/multi-image-kontext-max",
    )
    monkeypatch.setattr(
        settings,
        "REPLICATE_FLUX_MODEL_CHAIN",
        "black-forest-labs/flux-kontext-pro",
    )
    product_path = tmp_path / "product.jpg"
    reference_path = tmp_path / "reference.jpg"
    output_path = tmp_path / "output.jpg"
    save_test_image(product_path, (32, 64, 96))
    save_test_image(reference_path, (200, 180, 150))

    captured = {}
    provider = ReplicateFluxProvider()

    def fake_prediction(model_name, model_input):
        captured["model_name"] = model_name
        captured["input"] = model_input
        return "https://example.test/output.jpg"

    def fake_download(output_url, path):
        save_test_image(path, (80, 80, 80))

    monkeypatch.setattr(provider, "_run_prediction", fake_prediction)
    monkeypatch.setattr(provider, "_download_output", fake_download)

    result = provider.generate_variant(
        asset_id="reference",
        variant_index=0,
        product_image_path=str(product_path),
        reference_image_path=str(reference_path),
        visual_prompt="Use a soft luxury scene.",
        output_path=str(output_path),
    )

    assert captured["model_name"] == "flux-kontext-apps/multi-image-kontext-max"
    assert "input_image_1" in captured["input"]
    assert "input_image_2" in captured["input"]
    assert "input_image" not in captured["input"]
    assert result["provider"].endswith("flux-kontext-apps/multi-image-kontext-max")


def test_flux_retries_pro_when_max_cannot_run(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "REPLICATE_API_TOKEN", "test-token")
    monkeypatch.setattr(
        settings,
        "REPLICATE_FLUX_MODEL_CHAIN",
        "black-forest-labs/flux-kontext-max,black-forest-labs/flux-kontext-pro",
    )
    product_path = tmp_path / "product.jpg"
    output_path = tmp_path / "output.jpg"
    save_test_image(product_path, (32, 64, 96))
    attempted_models = []
    provider = ReplicateFluxProvider()

    def fake_prediction(model_name, model_input):
        attempted_models.append(model_name)
        if model_name.endswith("-max"):
            raise RuntimeError("Replicate prediction failed: 402 insufficient credit for max model")
        return "https://example.test/output.jpg"

    monkeypatch.setattr(provider, "_run_prediction", fake_prediction)
    monkeypatch.setattr(provider, "_download_output", lambda _, path: save_test_image(path, (80, 80, 80)))

    result = provider.generate_variant(
        asset_id="retry",
        variant_index=0,
        product_image_path=str(product_path),
        reference_image_path=None,
        visual_prompt="Use a neutral scene.",
        output_path=str(output_path),
    )

    assert attempted_models == [
        "black-forest-labs/flux-kontext-max",
        "black-forest-labs/flux-kontext-pro",
    ]
    assert result["provider"].endswith("black-forest-labs/flux-kontext-pro")


def test_flux_waits_and_retries_replicate_throttle(monkeypatch):
    monkeypatch.setattr(settings, "REPLICATE_API_TOKEN", "test-token")
    provider = ReplicateFluxProvider()
    sleeps = []

    class FakeResponse:
        def __init__(self, status_code, data):
            self.status_code = status_code
            self._data = data
            self.text = str(data)

        def json(self):
            return self._data

    responses = iter(
        [
            FakeResponse(429, {"retry_after": 10}),
            FakeResponse(200, {"status": "succeeded", "output": "https://example.test/out.jpg"}),
        ]
    )
    monkeypatch.setattr(
        "app.services.visual_providers.replicate_flux_provider.requests.post",
        lambda *args, **kwargs: next(responses),
    )
    monkeypatch.setattr(
        "app.services.visual_providers.replicate_flux_provider.time.sleep",
        lambda seconds: sleeps.append(seconds),
    )

    output_url = provider._run_prediction(
        "black-forest-labs/flux-kontext-pro",
        {"prompt": "test", "input_image": "data:image/jpeg;base64,test"},
    )

    assert output_url == "https://example.test/out.jpg"
    assert sleeps == [10]


def test_gateway_and_scoring_accept_qualified_provider_names(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER_CHAIN", "mock")
    content = LLMGateway().generate_product_content(
        product_name="Test Product",
        visual_prompt="Neutral background",
        content_prompt="Write concise copy",
        tone="minimal",
    )
    assert content["provider"] == "mock"
    assert content["channel_outputs"]["product_description"]

    image_path = tmp_path / "generated.jpg"
    save_test_image(image_path, (120, 120, 120))
    scored = ScoringService().score_variants(
        variants=[
            {
                "variant_id": "v1",
                "image_path": str(image_path),
                "provider": "replicate_flux:black-forest-labs/flux-kontext-max",
            }
        ],
        visual_prompt="A professional product image.",
        reference_image_path=None,
    )
    assert scored[0]["scores"]["source_layer_retained_indicator"] == 0.0

    cloudflare_scored = ScoringService().score_variants(
        variants=[
            {
                "variant_id": "v1",
                "image_path": str(image_path),
                "provider": "cloudflare_flux:@cf/black-forest-labs/flux-2-klein-4b",
            }
        ],
        visual_prompt="A professional product image.",
        reference_image_path=None,
    )
    assert cloudflare_scored[0]["scores"]["source_layer_retained_indicator"] == 0.0

    retained_scored = ScoringService().score_variants(
        variants=[
            {
                "variant_id": "v1",
                "image_path": str(image_path),
                "provider": "cloudflare_flux:@cf/black-forest-labs/flux-2-klein-4b:source_product_overlay",
            }
        ],
        visual_prompt="A professional product image.",
        reference_image_path=None,
    )
    assert retained_scored[0]["scores"]["source_layer_retained_indicator"] == 1.0


def test_gemini_text_analyzes_original_product_image_before_copy(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "GEMINI_TEXT_MODEL", "gemini-2.5-flash-lite")
    monkeypatch.setattr(settings, "GEMINI_TEXT_MODEL_CHAIN", "gemini-2.5-flash-lite")
    product_path = tmp_path / "product.png"
    product = Image.new("RGBA", (80, 80), (0, 0, 0, 0))
    for x in range(20, 60):
        for y in range(20, 60):
            product.putpixel((x, y), (120, 45, 25, 255))
    product.save(product_path)
    captured = {}

    class FakeResponse:
        text = json.dumps(
            {
                "product_analysis": {
                    "detected_product_type": "handbag",
                    "observed_description": "A structured brown handbag with a clean silhouette.",
                    "visible_details": ["warm brown tone", "structured body"],
                    "condition_observations": ["no visible major damage in this view"],
                    "buyer_appeal_points": ["easy-to-style silhouette"],
                    "unknown_or_unverified": ["material composition", "authenticity"],
                },
                "description": "A structured brown handbag designed for refined daily styling.",
                "caption": "A polished everyday silhouette.",
                "hashtags": ["#handbag"],
                "channel_outputs": {
                    "product_description": "A structured brown handbag designed for refined daily styling.",
                    "instagram_caption": "A polished everyday silhouette.",
                    "hashtags": ["#handbag"],
                },
            }
        )

    class FakeModels:
        def generate_content(self, model, contents, config):
            captured["model"] = model
            captured["contents"] = contents
            captured["config"] = config
            return FakeResponse()

    class FakeClient:
        def __init__(self, api_key):
            captured["api_key"] = api_key
            self.models = FakeModels()

    monkeypatch.setattr("google.genai.Client", FakeClient)

    content = GeminiTextProvider().generate(
        product_name="Featured bag",
        visual_prompt="Soft daylight background.",
        content_prompt="Write convincing Vietnamese product copy.",
        tone="premium",
        campaign_context={"language": "Vietnamese"},
        product_image_path=str(product_path),
    )

    assert captured["model"] == "gemini-2.5-flash-lite"
    assert len(captured["contents"]) == 2
    assert "original uploaded product image is attached" in captured["contents"][0]
    assert isinstance(captured["contents"][1], Image.Image)
    assert captured["contents"][1].mode == "RGB"
    assert content["product_analysis"]["detected_product_type"] == "handbag"
    assert content["channel_outputs"]["product_description"]
    normalized = LLMGateway()._normalize_content(content)
    assert normalized["channel_outputs"]["product_analysis"]["visible_details"]


def test_quality_report_blocks_unverified_ai_product_identity(tmp_path):
    image_path = tmp_path / "generated.jpg"
    save_test_image(image_path, (120, 120, 120))
    service = ScoringService()
    scored = service.score_variants(
        variants=[
            {
                "variant_id": "v1",
                "image_path": str(image_path),
                "provider": "cloudflare_flux:@cf/black-forest-labs/flux-2-klein-4b",
            }
        ],
        visual_prompt="A professional product image.",
        reference_image_path=None,
    )

    report = service.build_quality_report(scored, "v1", {})

    assert report["identity_assurance"]["status"] == "unverified_ai_edit"
    assert report["identity_assurance"]["requires_identity_review"] is True
    assert report["approval_gate"] == "blocked_pending_identity_review"


def test_technical_screen_is_not_affected_by_prompt_length(tmp_path):
    source_path = tmp_path / "source.jpg"
    generated_path = tmp_path / "generated.jpg"
    save_test_image(source_path, (85, 110, 130), (320, 320))
    save_test_image(generated_path, (140, 140, 140), (1024, 1024))
    service = ScoringService()
    variant = {
        "variant_id": "v1",
        "image_path": str(generated_path),
        "provider": "cloudflare_flux:@cf/black-forest-labs/flux-2-klein-4b",
    }

    concise = service.score_variants([variant], "studio", None, str(source_path))[0]
    verbose = service.score_variants([variant], "scene detail " * 500, None, str(source_path))[0]

    assert concise["scores"] == verbose["scores"]
    assert "prompt_alignment_proxy" not in concise["scores"]
    assert concise["technical_diagnostics"]["output_dimensions"] == "1024x1024"
    assert concise["technical_diagnostics"]["scene_change_signal"] is not None


def test_image_model_evaluation_fails_identity_when_damage_is_introduced():
    request = ImageEvaluationRequest(
        compared_with_original=True,
        product_fidelity=5,
        scene_quality=5,
        photorealism=5,
        prompt_adherence=5,
        publish_readiness=5,
        failure_modes=["introduced_damage_or_wear"],
        reviewer_comment="A new crack appears on the product surface.",
    )
    evaluation = _build_image_evaluation(
        {
            "best_variant_id": "v1",
            "variants": [
                {
                    "variant_id": "v1",
                    "provider": "cloudflare_flux:@cf/black-forest-labs/flux-2-klein-4b",
                }
            ],
        },
        request,
    )

    assert evaluation["weighted_score"] == 100.0
    assert evaluation["identity_pass"] is False
    assert evaluation["publishable"] is False
    assert evaluation["decision"] == "failed_product_identity"


def test_saved_image_evaluations_aggregate_provider_quality(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'evaluations.db'}")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    db.add(
        Asset(
            id="evaluated-asset",
            status="generated",
            product_image_path="source.jpg",
            best_variant_id="v1",
            visual_provider_used="cloudflare_flux:@cf/black-forest-labs/flux-2-klein-4b",
            variants_json=json.dumps(
                [
                    {
                        "variant_id": "v1",
                        "provider": "cloudflare_flux:@cf/black-forest-labs/flux-2-klein-4b",
                    }
                ]
            ),
        )
    )
    db.commit()

    event = record_image_evaluation(
        "evaluated-asset",
        ImageEvaluationRequest(
            compared_with_original=True,
            product_fidelity=2,
            scene_quality=4,
            photorealism=3,
            prompt_adherence=4,
            publish_readiness=2,
            failure_modes=["introduced_damage_or_wear"],
        ),
        db,
    )
    summary = image_model_evaluation_summary(db)
    db.close()

    assert event["event_type"] == "image_evaluation_recorded"
    assert summary["total_evaluations"] == 1
    assert summary["models"][0]["identity_pass_rate"] == 0.0
    assert summary["models"][0]["top_failure_modes"] == ["introduced_damage_or_wear"]


def test_approval_identity_gate_recognizes_overlay_and_legacy_edits():
    assert _requires_identity_verification(
        {"quality_report": {"identity_assurance": {"requires_identity_review": True}}}
    )
    assert not _requires_identity_verification(
        {"quality_report": {"identity_assurance": {"requires_identity_review": False}}}
    )
    assert _requires_identity_verification(
        {"quality_report": {}, "visual_provider_used": "cloudflare_flux:@cf/black-forest-labs/flux-2-klein-4b"}
    )
    assert not _requires_identity_verification(
        {
            "quality_report": {},
            "visual_provider_used": "cloudflare_flux:@cf/black-forest-labs/flux-2-klein-4b:source_product_overlay",
        }
    )


def test_export_requires_approved_asset():
    assert not _can_export_asset({"status": "generated"})
    assert not _can_export_asset({"status": "needs_revision"})
    assert _can_export_asset({"status": "approved"})
    assert _can_export_asset({"status": "exported"})
