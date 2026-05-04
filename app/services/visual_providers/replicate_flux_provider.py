import base64
import time
from pathlib import Path
from urllib.parse import quote

import requests
from app.config import settings
from app.services.visual_providers.base import VisualProvider


class ReplicateFluxProvider(VisualProvider):
    name = "replicate_flux"

    def generate_variant(
        self,
        asset_id: str,
        variant_index: int,
        product_image_path: str,
        reference_image_path: str | None,
        visual_prompt: str,
        output_path: str,
    ) -> dict:
        if not settings.REPLICATE_API_TOKEN:
            raise RuntimeError("Missing REPLICATE_API_TOKEN")

        image_data_uri = self._to_data_uri(product_image_path)

        prompt = f'''
Use the uploaded product as the exact reference identity.
{visual_prompt}
Keep product logo, color, sponsor text, collar, sleeves, fabric details.
Make it look like a realistic product marketing photo, not a pasted sticker.
Variant {variant_index + 1}.
'''

        output_url = self._run_prediction(image_data_uri, prompt)
        self._download_output(output_url, output_path)

        return {
            "variant_id": f"v{variant_index + 1}",
            "image_path": output_path,
            "provider": self.name,
        }

    def _to_data_uri(self, path: str) -> str:
        suffix = Path(path).suffix.lower().replace(".", "")
        mime = "jpeg" if suffix in ["jpg", "jpeg"] else "png"
        data = Path(path).read_bytes()
        return f"data:image/{mime};base64,{base64.b64encode(data).decode('utf-8')}"

    def _run_prediction(self, image_data_uri: str, prompt: str) -> str:
        owner, model_name = settings.REPLICATE_FLUX_MODEL.split("/", 1)
        url = f"https://api.replicate.com/v1/models/{owner}/{quote(model_name)}/predictions"

        headers = {
            "Authorization": f"Bearer {settings.REPLICATE_API_TOKEN}",
            "Content-Type": "application/json",
            "Prefer": "wait",
        }

        payload = {
            "input": {
                "prompt": prompt,
                "input_image": image_data_uri,
                "output_format": "jpg",
                "aspect_ratio": "1:1",
            }
        }

        response = requests.post(url, headers=headers, json=payload, timeout=settings.REQUEST_TIMEOUT_SECONDS)

        if response.status_code >= 400:
            raise RuntimeError(f"Replicate prediction failed: {response.status_code} {response.text[:300]}")

        data = response.json()

        if data.get("status") in ["starting", "processing"]:
            get_url = data["urls"]["get"]
            for _ in range(60):
                time.sleep(2)
                poll = requests.get(get_url, headers=headers, timeout=30)
                poll.raise_for_status()
                data = poll.json()
                if data.get("status") == "succeeded":
                    break
                if data.get("status") == "failed":
                    raise RuntimeError(f"Replicate failed: {data.get('error')}")

        output = data.get("output")
        if isinstance(output, list) and output:
            return output[0]
        if isinstance(output, str):
            return output

        raise RuntimeError("Replicate returned no output URL")

    def _download_output(self, output_url: str, output_path: str):
        response = requests.get(output_url, timeout=settings.REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(response.content)
