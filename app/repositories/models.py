from sqlalchemy import Column, String, Text, DateTime, Float
from datetime import datetime
from app.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id = Column(String, primary_key=True, index=True)
    product_name = Column(String, nullable=True)
    status = Column(String, index=True, default="pending_review")

    product_image_path = Column(Text, nullable=False)
    reference_image_path = Column(Text, nullable=True)
    best_image_path = Column(Text, nullable=True)
    variants_json = Column(Text, nullable=True)

    best_variant_id = Column(String, nullable=True)
    best_score = Column(Float, nullable=True)

    visual_provider_used = Column(String, nullable=True)
    llm_provider_used = Column(String, nullable=True)

    visual_prompt = Column(Text, nullable=True)
    content_prompt = Column(Text, nullable=True)
    tone = Column(Text, nullable=True)

    description = Column(Text, nullable=True)
    caption = Column(Text, nullable=True)
    hashtags = Column(Text, nullable=True)

    reviewer_note = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
