from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session
from app.repositories.models import Asset, AssetEvent
from app.core.status import EXPORTED


class AssetRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> Asset:
        asset = Asset(**data)
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)
        self.add_event(
            asset_id=asset.id,
            event_type="asset_created",
            status=asset.status,
            payload={"product_name": asset.product_name, "campaign_name": asset.campaign_name},
        )
        return asset

    def list(self, status: str | None = None) -> list[Asset]:
        query = self.db.query(Asset).order_by(Asset.created_at.desc())
        if status:
            query = query.filter(Asset.status == status)
        return query.all()

    def get(self, asset_id: str) -> Asset | None:
        return self.db.query(Asset).filter(Asset.id == asset_id).first()

    def update_review(
        self,
        asset_id: str,
        status: str,
        reviewer_note: str | None,
        description: str | None = None,
        caption: str | None = None,
        hashtags: list[str] | None = None,
        channel_outputs: dict | None = None,
        best_variant_id: str | None = None,
        identity_verified: bool = False,
    ):
        asset = self.get(asset_id)
        if not asset:
            return None

        asset.status = status
        asset.reviewer_note = reviewer_note

        if description is not None:
            asset.description = description
        if caption is not None:
            asset.caption = caption
        if hashtags is not None:
            asset.hashtags = json.dumps(hashtags, ensure_ascii=False)
        if channel_outputs is not None:
            asset.channel_outputs_json = json.dumps(channel_outputs, ensure_ascii=False)
        if best_variant_id:
            self._apply_best_variant(asset, best_variant_id)

        asset.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(asset)
        self.add_event(
            asset_id=asset.id,
            event_type="review_updated",
            status=asset.status,
            note=reviewer_note,
            payload={
                "best_variant_id": asset.best_variant_id,
                "edited_content": any(
                    value is not None
                    for value in [description, caption, hashtags, channel_outputs]
                ),
                "identity_verified": identity_verified,
            },
        )
        return asset

    def mark_exported(self, asset_id: str):
        asset = self.get(asset_id)
        if not asset:
            return None

        asset.status = EXPORTED
        asset.exported_at = datetime.utcnow()
        asset.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(asset)
        self.add_event(asset.id, "asset_exported", status=asset.status)
        return asset

    def add_event(
        self,
        asset_id: str,
        event_type: str,
        status: str | None = None,
        note: str | None = None,
        payload: dict | None = None,
    ) -> AssetEvent:
        event = AssetEvent(
            id=str(uuid4()),
            asset_id=asset_id,
            event_type=event_type,
            status=status,
            note=note,
            payload_json=json.dumps(payload or {}, ensure_ascii=False),
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_events(self, asset_id: str) -> list[AssetEvent]:
        return (
            self.db.query(AssetEvent)
            .filter(AssetEvent.asset_id == asset_id)
            .order_by(AssetEvent.created_at.asc())
            .all()
        )

    def list_events_by_type(self, event_type: str) -> list[AssetEvent]:
        return (
            self.db.query(AssetEvent)
            .filter(AssetEvent.event_type == event_type)
            .order_by(AssetEvent.created_at.asc())
            .all()
        )

    def _apply_best_variant(self, asset: Asset, best_variant_id: str):
        variants = json.loads(asset.variants_json or "[]")
        selected = next(
            (variant for variant in variants if variant.get("variant_id") == best_variant_id),
            None,
        )
        if not selected:
            return

        asset.best_variant_id = best_variant_id
        asset.best_image_path = selected.get("image_path")
        asset.best_score = selected.get("scores", {}).get("final_score")

    @staticmethod
    def to_dict(asset: Asset) -> dict:
        return {
            "id": asset.id,
            "product_name": asset.product_name,
            "campaign_name": asset.campaign_name,
            "brand_name": asset.brand_name,
            "target_audience": asset.target_audience,
            "customer_persona": asset.customer_persona,
            "platform": asset.platform,
            "marketing_objective": asset.marketing_objective,
            "funnel_stage": asset.funnel_stage,
            "copy_framework": asset.copy_framework,
            "selling_points": asset.selling_points,
            "price": asset.price,
            "offer": asset.offer,
            "language": asset.language,
            "compliance_notes": asset.compliance_notes,
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
            "channel_outputs": json.loads(asset.channel_outputs_json or "{}"),
            "quality_report": json.loads(asset.quality_report_json or "{}"),
            "visual_prompt": asset.visual_prompt,
            "content_prompt": asset.content_prompt,
            "tone": asset.tone,
            "reviewer_note": asset.reviewer_note,
            "error_message": asset.error_message,
            "exported_at": asset.exported_at.isoformat() if asset.exported_at else None,
            "created_at": asset.created_at.isoformat() if asset.created_at else None,
            "updated_at": asset.updated_at.isoformat() if asset.updated_at else None,
        }

    @staticmethod
    def event_to_dict(event: AssetEvent) -> dict:
        return {
            "id": event.id,
            "asset_id": event.asset_id,
            "event_type": event.event_type,
            "status": event.status,
            "note": event.note,
            "payload": json.loads(event.payload_json or "{}"),
            "created_at": event.created_at.isoformat() if event.created_at else None,
        }
