import json
import zipfile
from pathlib import Path
from app.config import settings


class ExportService:
    def export_asset(self, asset: dict) -> str:
        export_dir = Path(settings.STORAGE_DIR) / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        zip_path = export_dir / f"{asset['id']}_reference_editing_asset.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            best_path = Path(asset["best_image_path"])
            if best_path.exists():
                z.write(best_path, arcname="best_image.jpg")

            for v in asset.get("variants", []):
                p = Path(v["image_path"])
                if p.exists():
                    z.write(p, arcname=f"variants/{v['variant_id']}_{v.get('provider','unknown')}.jpg")

            if asset.get("product_image_path") and Path(asset["product_image_path"]).exists():
                z.write(asset["product_image_path"], arcname="input/product_image.jpg")

            if asset.get("reference_image_path") and Path(asset["reference_image_path"]).exists():
                z.write(asset["reference_image_path"], arcname="input/reference_image.jpg")

            z.writestr("asset_metadata.json", json.dumps(asset, ensure_ascii=False, indent=2))
            z.writestr(
                "caption.txt",
                f"{asset.get('caption') or ''}\n\n{' '.join(asset.get('hashtags') or [])}",
            )

        return str(zip_path)
