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
                "campaign_brief.json",
                json.dumps(self._campaign_brief(asset), ensure_ascii=False, indent=2),
            )
            z.writestr(
                "quality_report.json",
                json.dumps(asset.get("quality_report") or {}, ensure_ascii=False, indent=2),
            )
            z.writestr(
                "caption.txt",
                f"{asset.get('caption') or ''}\n\n{' '.join(asset.get('hashtags') or [])}",
            )
            self._write_channel_outputs(z, asset.get("channel_outputs") or {})
            if asset.get("reviewer_note"):
                z.writestr("reviewer_note.txt", asset["reviewer_note"])

        return str(zip_path)

    def _campaign_brief(self, asset: dict) -> dict:
        keys = [
            "campaign_name",
            "brand_name",
            "product_name",
            "target_audience",
            "customer_persona",
            "platform",
            "marketing_objective",
            "funnel_stage",
            "copy_framework",
            "selling_points",
            "price",
            "offer",
            "language",
            "tone",
            "compliance_notes",
        ]
        return {key: asset.get(key) for key in keys}

    def _write_channel_outputs(self, z: zipfile.ZipFile, channel_outputs: dict):
        output_names = {
            "seo_title": "content/seo_title.txt",
            "product_description": "content/product_description.txt",
            "instagram_caption": "content/instagram_caption.txt",
            "facebook_ad": "content/facebook_ad.txt",
            "tiktok_script": "content/tiktok_script.txt",
            "shopee_description": "content/shopee_description.txt",
            "email_subject": "content/email_subject.txt",
        }

        for key, arcname in output_names.items():
            value = channel_outputs.get(key)
            if value:
                z.writestr(arcname, str(value))

        if channel_outputs.get("cta_suggestions"):
            z.writestr("content/cta_suggestions.txt", "\n".join(channel_outputs["cta_suggestions"]))
        if channel_outputs.get("hashtags"):
            z.writestr("content/hashtags.txt", " ".join(channel_outputs["hashtags"]))
        if channel_outputs.get("product_analysis"):
            z.writestr(
                "content/product_analysis.json",
                json.dumps(channel_outputs["product_analysis"], ensure_ascii=False, indent=2),
            )
