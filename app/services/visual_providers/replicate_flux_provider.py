import base64
import time
from pathlib import Path
from urllib.parse import quote

import requests
from loguru import logger

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

        product_image = self._to_data_uri(product_image_path)
        reference_image = self._to_data_uri(reference_image_path) if reference_image_path else None
        prompt = self._build_prompt(visual_prompt, variant_index, has_reference=bool(reference_image))
        errors = []

        for model_name, supports_reference in self._model_candidates(bool(reference_image)):
            model_input = {
                "prompt": prompt,
                "output_format": "jpg",
                "aspect_ratio": settings.REPLICATE_FLUX_ASPECT_RATIO,
                "prompt_upsampling": False,
                "safety_tolerance": 2,
            }
            if supports_reference and reference_image:
                model_input["input_image_1"] = product_image
                model_input["input_image_2"] = reference_image
            else:
                model_input["input_image"] = product_image
                if reference_image:
                    logger.info(
                        f"FLUX reference fallback uses product image only | model={model_name} | "
                        f"variant={variant_index + 1}"
                    )

            try:
                logger.info(f"Trying Replicate FLUX model | model={model_name} | variant={variant_index + 1}")
                output_url = self._run_prediction(model_name, model_input)
                self._download_output(output_url, output_path)
                return {
                    "variant_id": f"v{variant_index + 1}",
                    "image_path": output_path,
                    "provider": f"{self.name}:{model_name}",
                }
            except Exception as exc:
                error = self._safe_error(exc)
                errors.append(f"{model_name}: {error}")
                logger.warning(f"Replicate FLUX model failed | model={model_name} | error={error}")
                if self._is_unrecoverable_auth_error(error):
                    break

        raise RuntimeError("All Replicate FLUX models failed: " + " | ".join(errors))

    def _model_candidates(self, has_reference: bool) -> list[tuple[str, bool]]:
        candidates: list[tuple[str, bool]] = []
        if has_reference:
            candidates.extend(
                (model, True)
                for model in self._parse_model_chain(settings.REPLICATE_FLUX_REFERENCE_MODEL_CHAIN)
            )
        candidates.extend(
            (model, False)
            for model in self._parse_model_chain(
                settings.REPLICATE_FLUX_MODEL_CHAIN or settings.REPLICATE_FLUX_MODEL
            )
        )
        if not candidates:
            candidates.append((settings.REPLICATE_FLUX_MODEL, False))

        unique_candidates = []
        seen = set()
        for model, supports_reference in candidates:
            key = (model, supports_reference)
            if key not in seen:
                seen.add(key)
                unique_candidates.append(key)
        return unique_candidates

    def _parse_model_chain(self, configured_models: str) -> list[str]:
        return [model.strip() for model in configured_models.split(",") if model.strip()]

    def _build_prompt(self, visual_prompt: str, variant_index: int, has_reference: bool) -> str:
        reference_instruction = (
            "Use image 2 only as a scene and lighting reference. Never copy its product identity."
            if has_reference
            else "Use the requested setting and preserve the input product."
        )
        return f"""
Edit image 1 into a professional product marketing photograph.
Image 1 is the only source of truth for the product identity.
{reference_instruction}

Scene direction:
{visual_prompt}

Non-destructive product lock, highest priority:
- Treat the product as a locked photographic foreground layer. Preserve category, silhouette, proportions,
  orientation, camera angle, color, material, texture, logo, label, readable text, pattern, hardware,
  stitching, packaging, and visible condition exactly as shown in image 1.
- Modify only pixels outside the product silhouette: background, support surface, external shadow, and distant props.
- Do not re-render, retouch, relight, redesign, recolor, repair, rebrand, relabel, or cover the product.
- Do not add cracks, scratches, creases, dents, stains, discoloration, extra texture, new reflections, wear, or damage.
- Do not remove or hide existing condition details, and do not add a person or another product.

Create variant {variant_index + 1}.
"""

    def _to_data_uri(self, path: str) -> str:
        suffix = Path(path).suffix.lower().replace(".", "")
        mime = "jpeg" if suffix in ["jpg", "jpeg"] else "png"
        data = Path(path).read_bytes()
        return f"data:image/{mime};base64,{base64.b64encode(data).decode('utf-8')}"

    def _run_prediction(self, model_name: str, model_input: dict) -> str:
        owner, model = model_name.split("/", 1)
        url = f"https://api.replicate.com/v1/models/{owner}/{quote(model)}/predictions"
        headers = {
            "Authorization": f"Bearer {settings.REPLICATE_API_TOKEN}",
            "Content-Type": "application/json",
            "Prefer": "wait",
        }
        response = self._post_prediction_with_retry(url, headers, model_input)
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

    def _post_prediction_with_retry(self, url: str, headers: dict, model_input: dict):
        for attempt in range(2):
            response = requests.post(
                url,
                headers=headers,
                json={"input": model_input},
                timeout=settings.REQUEST_TIMEOUT_SECONDS,
            )
            if response.status_code != 429 or attempt == 1:
                return response

            retry_after = self._retry_after_seconds(response)
            logger.info(f"Replicate throttled request; retrying after {retry_after}s")
            time.sleep(retry_after)
        return response

    def _retry_after_seconds(self, response) -> int:
        try:
            retry_after = int(response.json().get("retry_after", 1))
        except (TypeError, ValueError, AttributeError):
            retry_after = 1
        return max(1, min(retry_after, 30))

    def _download_output(self, output_url: str, output_path: str):
        response = requests.get(output_url, timeout=settings.REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(response.content)

    def _safe_error(self, exc: Exception) -> str:
        message = str(exc).replace("\n", " ").strip()
        return message[:300] + "..." if len(message) > 300 else message

    def _is_unrecoverable_auth_error(self, error: str) -> bool:
        text = error.lower()
        return any(marker in text for marker in ["401", "unauthenticated", "invalid authentication token"])
