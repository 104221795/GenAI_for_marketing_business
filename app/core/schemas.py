from pydantic import BaseModel
from typing import Optional, List, Dict


class GenerationRequest(BaseModel):
    product_name: Optional[str] = None
    visual_prompt: str
    content_prompt: str
    tone: str = "premium, emotional, product-selling"
    num_variants: int = 2


class VariantResult(BaseModel):
    variant_id: str
    image_path: str
    provider: str
    scores: Dict[str, float]


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
    error_message: Optional[str] = None


class ReviewRequest(BaseModel):
    status: str
    reviewer_note: Optional[str] = None
