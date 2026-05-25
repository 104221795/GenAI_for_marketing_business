from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class GenerationRequest(BaseModel):
    product_name: Optional[str] = None
    campaign_name: Optional[str] = None
    brand_name: Optional[str] = None
    target_audience: Optional[str] = None
    customer_persona: Optional[str] = None
    platform: str = "Instagram"
    marketing_objective: str = "conversion"
    funnel_stage: str = "consideration"
    copy_framework: str = "AIDA"
    selling_points: Optional[str] = None
    price: Optional[str] = None
    offer: Optional[str] = None
    language: str = "Vietnamese"
    compliance_notes: Optional[str] = None
    visual_prompt: str
    content_prompt: str
    tone: str = "premium, emotional, product-selling"
    num_variants: int = Field(default=2, ge=1, le=6)


class VariantResult(BaseModel):
    variant_id: str
    image_path: str
    provider: str
    scores: Dict[str, float]
    technical_diagnostics: Dict[str, Any] = Field(default_factory=dict)


class GenerationResult(BaseModel):
    asset_id: str
    status: str
    product_image_path: str
    reference_image_path: Optional[str] = None
    best_image_path: str
    variants: List[VariantResult]
    best_variant_id: str
    visual_provider_used: str
    llm_provider_used: str
    description: str
    caption: str
    hashtags: List[str]
    channel_outputs: Dict[str, Any] = Field(default_factory=dict)
    quality_report: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class ReviewRequest(BaseModel):
    status: str
    identity_verified: bool = False
    reviewer_note: Optional[str] = None
    description: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None
    channel_outputs: Optional[Dict[str, Any]] = None
    best_variant_id: Optional[str] = None


class ImageEvaluationRequest(BaseModel):
    compared_with_original: bool = False
    product_fidelity: int = Field(ge=1, le=5)
    scene_quality: int = Field(ge=1, le=5)
    photorealism: int = Field(ge=1, le=5)
    prompt_adherence: int = Field(ge=1, le=5)
    publish_readiness: int = Field(ge=1, le=5)
    failure_modes: List[str] = Field(default_factory=list)
    reviewer_comment: Optional[str] = None
