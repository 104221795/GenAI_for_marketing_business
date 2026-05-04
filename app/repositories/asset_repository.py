import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.repositories.models import Asset


class AssetRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> Asset:
        asset = Asset(**data)
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def list(self, status: str | None = None) -> list[Asset]:
        query = self.db.query(Asset).order_by(Asset.created_at.desc())
        if status:
            query = query.filter(Asset.status == status)
        return query.all()

    def get(self, asset_id: str) -> Asset | None:
        return self.db.query(Asset).filter(Asset.id == asset_id).first()

    def update_review(self, asset_id: str, status: str, reviewer_note: str | None):
        asset = self.get(asset_id)
        if not asset:
            return None
        asset.status = status
        asset.reviewer_note = reviewer_note
        asset.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(asset)
        return asset

    @staticmethod
    def to_dict(asset: Asset) -> dict:
        return {
            "id": asset.id,
            "product_name": asset.product_name,
            "status": asset.status,
            "product_image_path": asset.product_image_path,
            "reference_image_path": asset.reference_image_path,
            "best_image_path": asset.best_image_path,
            "variants": json.loads(asset.variants_json or "[]"),
            "best_variant_id": asset.best_variant_id,
            "best_score": asset.best_score,
            "visual_provider_used": asset.visual_provider_used,
            "llm_provider_used": asset.llm_provider_used,
            "description": asset.description,
            "caption": asset.caption,
            "hashtags": json.loads(asset.hashtags or "[]"),
            "visual_prompt": asset.visual_prompt,
            "content_prompt": asset.content_prompt,
            "tone": asset.tone,
            "reviewer_note": asset.reviewer_note,
            "error_message": asset.error_message,
        }
