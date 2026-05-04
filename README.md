# AI Product Studio — Reference Image Editing Version

This is the final demo-ready version for your thesis/product demo.

It uses **reference-based image editing** instead of pasting a shirt onto a background.

## Core architecture

```text
Product Image + Optional Reference Picture + Prompt
→ Visual Provider Chain
    1. Gemini Image / Nano Banana
    2. Replicate FLUX Kontext
    3. Mock fallback
→ Multi-generation
→ Quality scoring
→ Best image selection
→ Gemini/MOCK product description
→ Human review
→ Export ZIP
```

## Why this is the correct direction

Old bad approach:

```text
Generate background → paste shirt image on top
```

This makes the product look like a sticker.

New approach:

```text
Product image + reference picture → image editing model → natural product marketing image
```

This is closer to Luma-style or Nano Banana-style output.

---

## Folder structure

```text
ai-product-studio-reference-editing/
│
├── app/
│   ├── main.py
│   │   FastAPI backend routes.
│   │
│   ├── config.py
│   │   Loads .env.
│   │
│   ├── database.py
│   │   SQLite database.
│   │
│   ├── logging_config.py
│   │   Console + JSON log file.
│   │
│   ├── core/
│   │   ├── pipeline.py
│   │   │   Main orchestration.
│   │   ├── schemas.py
│   │   │   Request/response models.
│   │   └── status.py
│   │       Status constants.
│   │
│   ├── services/
│   │   ├── visual_service.py
│   │   │   Visual provider chain manager.
│   │   ├── scoring_service.py
│   │   │   Demo metrics and best image selection.
│   │   ├── llm_service.py
│   │   │   LLM provider chain manager.
│   │   ├── export_service.py
│   │   │   ZIP export.
│   │   │
│   │   ├── visual_providers/
│   │   │   ├── gemini_image_provider.py
│   │   │   │   Gemini Image / Nano Banana reference-based editing.
│   │   │   ├── replicate_flux_provider.py
│   │   │   │   Replicate FLUX Kontext fallback.
│   │   │   └── mock_provider.py
│   │   │       Local fallback.
│   │   │
│   │   └── llm_providers/
│   │       ├── gemini_text_provider.py
│   │       └── mock_provider.py
│   │
│   └── repositories/
│       ├── models.py
│       └── asset_repository.py
│
├── ui/
│   └── streamlit_app.py
│       Streamlit admin UI.
│
├── storage/
│   ├── input/product/
│   ├── input/reference/
│   ├── output/
│   └── exports/
│
├── logs/
├── requirements.txt
├── .env.example
├── scripts_init_db.py
├── run_backend.bat
└── run_ui.bat
```

---

## Setup

```bash
cd ai-product-studio-reference-editing
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python scripts_init_db.py
```

## Run backend

```bash
uvicorn app.main:app --reload
```

## Run UI

```bash
streamlit run ui/streamlit_app.py
```

Open:

```text
http://localhost:8501
```

---

## .env setup

### Demo fallback only

Leave keys empty:

```env
GEMINI_API_KEY=
REPLICATE_API_TOKEN=
```

### Real Gemini Image + Gemini Text

```env
VISUAL_PROVIDER_CHAIN=gemini_image,replicate_flux,mock
GEMINI_API_KEY=your_gemini_key
GEMINI_IMAGE_MODEL=gemini-2.5-flash-image-preview

LLM_PROVIDER_CHAIN=gemini_text,mock
GEMINI_TEXT_MODEL=gemini-2.0-flash
```

### Add Replicate FLUX fallback

```env
REPLICATE_API_TOKEN=your_replicate_key
REPLICATE_FLUX_MODEL=black-forest-labs/flux-kontext-pro
```

---

## Recommended visual prompt

```text
Use the uploaded product image as the exact product identity.
Use the uploaded reference picture as the target composition and visual style.
Keep the same shirt design, color, logo, sponsor text, collar, sleeves, fabric texture and visible details.
Generate a realistic product marketing photo where the shirt is naturally lying flat on a football field grass under warm sunlight.
Match the reference image format, camera angle, perspective, lighting, shadows and realistic wrinkles.
Do not add a person. Do not hang the shirt. Do not change the shirt identity. Do not crop out the product.
```

## Metrics

The current metrics are demo-safe proxy metrics:

- `aesthetic_score`
- `prompt_alignment_proxy`
- `product_visibility_proxy`
- `reference_format_similarity_proxy`
- `provider_bonus`
- `final_score`

For thesis writing, call them **heuristic/demo metrics**, not full FID/LPIPS/CLIP yet.

## Demo explanation

Say:

```text
The system uses an API-first provider architecture. It first tries Gemini Image / Nano Banana for reference-based image editing, then falls back to FLUX Kontext through Replicate, and finally falls back to local mock generation so the demo remains stable.
```
