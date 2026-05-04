import json
import shutil
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.logging_config import setup_logging
from app.database import get_db, init_db
from app.core.schemas import GenerationRequest, ReviewRequest
from app.core.pipeline import ProductPromotionPipeline
from app.repositories.asset_repository import AssetRepository
from app.services.export_service import ExportService


logger = setup_logging()
app = FastAPI(title=settings.APP_NAME)


@app.on_event("startup")
def startup():
    init_db()
    logger.info("Application started")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "visual_provider_chain": settings.VISUAL_PROVIDER_CHAIN,
        "llm_provider_chain": settings.LLM_PROVIDER_CHAIN,
        "has_gemini_key": bool(settings.GEMINI_API_KEY),
        "has_replicate_key": bool(settings.REPLICATE_API_TOKEN),
        "gemini_image_model": settings.GEMINI_IMAGE_MODEL,
        "gemini_text_model": settings.GEMINI_TEXT_MODEL,
    }


@app.post("/generate")
async def generate_asset(
    product_image: UploadFile = File(...),
    reference_image: UploadFile | None = File(None),
    product_name: str = Form(None),
    visual_prompt: str = Form(...),
    content_prompt: str = Form(...),
    tone: str = Form("premium, emotional, product-selling"),
    num_variants: int = Form(2),
    db: Session = Depends(get_db),
):
    product_dir = Path(settings.STORAGE_DIR) / "input" / "product"
    reference_dir = Path(settings.STORAGE_DIR) / "input" / "reference"
    product_dir.mkdir(parents=True, exist_ok=True)
    reference_dir.mkdir(parents=True, exist_ok=True)

    safe_product_name = product_image.filename.replace(" ", "_")
    product_path = product_dir / safe_product_name

    with open(product_path, "wb") as f:
        shutil.copyfileobj(product_image.file, f)

    reference_path = None
    if reference_image and reference_image.filename:
        safe_reference_name = reference_image.filename.replace(" ", "_")
        reference_path_obj = reference_dir / safe_reference_name
        with open(reference_path_obj, "wb") as f:
            shutil.copyfileobj(reference_image.file, f)
        reference_path = str(reference_path_obj)

    request = GenerationRequest(
        product_name=product_name,
        visual_prompt=visual_prompt,
        content_prompt=content_prompt,
        tone=tone,
        num_variants=num_variants,
    )

    result = ProductPromotionPipeline().run(
        product_image_path=str(product_path),
        reference_image_path=reference_path,
        request=request,
    )

    best_score = 0.0
    for v in result.variants:
        if v.variant_id == result.best_variant_id:
            best_score = v.scores.get("final_score", 0.0)

    repo = AssetRepository(db)
    repo.create({
        "id": result.asset_id,
        "product_name": product_name,
        "status": result.status,
        "product_image_path": result.product_image_path,
        "reference_image_path": result.reference_image_path,
        "best_image_path": result.best_image_path,
        "variants_json": json.dumps([v.model_dump() for v in result.variants], ensure_ascii=False),
        "best_variant_id": result.best_variant_id,
        "best_score": best_score,
        "visual_provider_used": result.visual_provider_used,
        "llm_provider_used": result.llm_provider_used,
        "visual_prompt": visual_prompt,
        "content_prompt": content_prompt,
        "tone": tone,
        "description": result.description,
        "caption": result.caption,
        "hashtags": json.dumps(result.hashtags, ensure_ascii=False),
        "error_message": result.error_message,
    })

    return result.model_dump()


@app.get("/assets")
def list_assets(status: str | None = None, db: Session = Depends(get_db)):
    repo = AssetRepository(db)
    return [repo.to_dict(asset) for asset in repo.list(status=status)]


@app.get("/assets/{asset_id}")
def get_asset(asset_id: str, db: Session = Depends(get_db)):
    repo = AssetRepository(db)
    asset = repo.get(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return repo.to_dict(asset)


@app.patch("/assets/{asset_id}/review")
def review_asset(asset_id: str, request: ReviewRequest, db: Session = Depends(get_db)):
    if request.status not in ["pending_review", "approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    repo = AssetRepository(db)
    asset = repo.update_review(asset_id, request.status, request.reviewer_note)

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    return repo.to_dict(asset)


@app.get("/files")
def get_file(path: str):
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(file_path))


@app.get("/assets/{asset_id}/export")
def export_asset(asset_id: str, db: Session = Depends(get_db)):
    repo = AssetRepository(db)
    asset = repo.get(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset_dict = repo.to_dict(asset)
    zip_path = ExportService().export_asset(asset_dict)
    return FileResponse(zip_path, filename=Path(zip_path).name)
