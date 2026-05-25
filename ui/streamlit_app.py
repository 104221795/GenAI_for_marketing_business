from collections import Counter
from urllib.parse import quote

import requests
import streamlit as st


API_URL = "http://127.0.0.1:8000"

PRODUCT_IDENTITY_RULES = """Treat the uploaded product photo as a locked foreground asset and the only source of truth.
Keep the input product orientation, camera angle, outline, dimensions, crop, color, material, finish, grain, logo, label, text, hardware, stitching, pattern, packaging, and existing condition unchanged.
Generate only the environment behind and around the product: background, supporting surface, external shadow, and distant non-obscuring props.
Never re-render, repaint, retouch, repair, relight, age, distress, smooth, sharpen, or change any product surface.
Do not create cracks, scratches, creases, dents, stains, discoloration, texture changes, new reflections, or new wear on the product.
Do not hide defects already visible in the source, cover any part of the product, add a person, or crop it out."""

SCENE_PRODUCTION_RULES = """Professional production controls:
- Keep the original product pose, orientation, perspective, size relationship, and camera angle.
- Reserve a clean hero area around the entire product silhouette; props stay behind it or far outside its edges.
- Apply scene lighting to the environment and external grounding shadow only, never as new marks or highlights on product surfaces.
- Use realistic commercial photography with restrained styling, no text, badges, overlays, hands, people, clutter, or competing products."""

DEFAULT_CONTENT_PROMPT = (
    "Inspect the original product image and create a detailed, persuasive product description suitable for "
    "a listing and social post. Highlight attractive visible design details and buyer value. "
    "Use only details supplied by the seller or clearly visible in the original product image; do not invent "
    "authenticity, materials, condition, discounts, accessories, or brand claims."
)

SCENE_TEMPLATES = {
    "soft_daylight": {
        "title": "Soft Daylight Studio",
        "group": "Minimal",
        "description": "Warm off-white surface, window light, soft shadow, generous negative space.",
        "direction": (
            "Build a warm off-white matte tabletop set in a minimal studio with a seamless tonal backdrop. "
            "Use a large diffused window source from camera left and a soft external grounding shadow. "
            "Leave generous clean negative space; include no props."
        ),
        "platform": "Instagram",
        "objective": "conversion",
        "tone": "minimal, refined, trustworthy",
        "audience": "Design-conscious online shoppers seeking a clear premium product presentation.",
    },
    "pure_white": {
        "title": "Pure White Catalogue",
        "group": "Ecommerce",
        "description": "Clean white listing image with accurate edges and subtle grounding shadow.",
        "direction": (
            "Use a seamless pure-white ecommerce sweep with even high-key studio illumination. Keep clean "
            "edge contrast and only a faint neutral grounding shadow on the surface. Include no props."
        ),
        "platform": "Website",
        "objective": "conversion",
        "tone": "clean, precise, commercial",
        "audience": "Online buyers comparing product detail and condition.",
    },
    "travertine": {
        "title": "Travertine Luxury",
        "group": "Luxury",
        "description": "Cream stone pedestal with restrained premium lighting.",
        "direction": (
            "Create a cream travertine pedestal set against a quiet warm-ivory backdrop. Use a broad diffused "
            "key light, gentle fill, and a refined external shadow. Keep stone veining subtle and distant "
            "from the hero silhouette."
        ),
        "platform": "Instagram",
        "objective": "conversion",
        "tone": "quiet luxury, elegant, curated",
        "audience": "Premium buyers attracted to elevated presentation and craftsmanship.",
    },
    "midnight": {
        "title": "Midnight Spotlight",
        "group": "Luxury",
        "description": "Dark charcoal set with controlled highlight and dramatic contrast.",
        "direction": (
            "Create a dark charcoal slate stage with a seamless near-black studio background. Use a controlled "
            "soft pool of light on the set and a readable grounding shadow. Avoid reflective streaks, haze, "
            "or bright accents crossing the hero area."
        ),
        "platform": "Instagram",
        "objective": "engagement",
        "tone": "dramatic, premium, collectible",
        "audience": "Luxury and collector audiences responding to editorial imagery.",
    },
    "botanical": {
        "title": "Botanical Fresh",
        "group": "Lifestyle",
        "description": "Pale stone, natural daylight, softly blurred greenery at the edges.",
        "direction": (
            "Build a pale limestone tabletop scene in fresh diffused daylight. Place only a few softly blurred "
            "green leaves at the far frame edges, outside the clear hero area, with no contact shadows from props."
        ),
        "platform": "TikTok",
        "objective": "awareness",
        "tone": "fresh, natural, modern",
        "audience": "Lifestyle shoppers drawn to clean, natural product stories.",
    },
    "vanity": {
        "title": "Vanity Shelf",
        "group": "Beauty",
        "description": "Neutral shelf, mirror glow, polished daily-routine atmosphere.",
        "direction": (
            "Create a clean warm-neutral vanity shelf with a softly glowing, defocused mirror in the background. "
            "Use diffused flattering ambient light; any blurred accessories remain distant at the far edges."
        ),
        "platform": "Instagram",
        "objective": "conversion",
        "tone": "polished, intimate, premium",
        "audience": "Beauty and self-care shoppers seeking a refined daily ritual.",
    },
    "coffee_table": {
        "title": "Coffee Table Editorial",
        "group": "Lifestyle",
        "description": "Textured linen and book corner for a lived-in editorial moment.",
        "direction": (
            "Create a restrained editorial coffee-table set with neutral linen texture and one closed art-book "
            "corner in the far background. Use soft morning window light; keep the central hero area clear."
        ),
        "platform": "Facebook",
        "objective": "engagement",
        "tone": "editorial, warm, aspirational",
        "audience": "Home and fashion shoppers who value tasteful lifestyle context.",
    },
    "gift": {
        "title": "Gift Ready",
        "group": "Seasonal",
        "description": "Subtle ribbon and premium box detail with bright celebratory light.",
        "direction": (
            "Create a refined gifting set on a light neutral surface. Add one unbranded presentation box or "
            "loose ribbon well behind the hero area only; do not imply included packaging. Use bright soft light."
        ),
        "platform": "Instagram",
        "objective": "conversion",
        "tone": "celebratory, refined, giftable",
        "audience": "Gift shoppers looking for a special, presentation-ready item.",
    },
    "travel": {
        "title": "Travel Essentials",
        "group": "Lifestyle",
        "description": "Light canvas backdrop with subtle journey cues and clean daylight.",
        "direction": (
            "Build a clean light-canvas tabletop with a softly blurred unbranded travel tag or folded map far in "
            "the background. Use open daylight and retain a fully uncluttered hero area."
        ),
        "platform": "TikTok",
        "objective": "awareness",
        "tone": "effortless, practical, premium",
        "audience": "Mobile shoppers imagining everyday travel and weekend use.",
    },
    "concrete": {
        "title": "Urban Concrete",
        "group": "Fashion",
        "description": "Architectural concrete plane with crisp directional lighting.",
        "direction": (
            "Create a clean architectural concrete plane and softly defocused concrete wall. Use directional "
            "daylight to form a modern external set shadow, with no graffiti, typography, or surface debris."
        ),
        "platform": "TikTok",
        "objective": "engagement",
        "tone": "modern, confident, design-led",
        "audience": "Fashion shoppers responding to clean urban styling.",
    },
    "summer": {
        "title": "Summer Resort",
        "group": "Seasonal",
        "description": "Sunlit cream surface with restrained coastal color accents.",
        "direction": (
            "Create a sunlit resort-inspired cream plaster surface with a faint aqua accent only in the distant "
            "background. Keep the foreground clean and dry with no sand, shells, foliage, or water reflections."
        ),
        "platform": "Instagram",
        "objective": "awareness",
        "tone": "bright, relaxed, premium",
        "audience": "Seasonal shoppers inspired by holiday styling.",
    },
    "festive": {
        "title": "Festive Gold Glow",
        "group": "Seasonal",
        "description": "Warm neutral set with restrained golden bokeh for launch moments.",
        "direction": (
            "Create a warm neutral studio surface with restrained, softly defocused golden bokeh far behind the "
            "hero area. Use a clean diffused key light; avoid glitter, confetti, ribbons, or metallic reflections."
        ),
        "platform": "Facebook",
        "objective": "conversion",
        "tone": "warm, festive, premium",
        "audience": "Celebration shoppers choosing a standout purchase or gift.",
    },
}

IMAGE_MODEL_RUBRIC = [
    {
        "key": "product_fidelity",
        "criterion": "Product fidelity",
        "weight": 40,
        "excellent": "Shape, logo or label, material, color, and visible condition match the original.",
    },
    {
        "key": "scene_quality",
        "criterion": "Scene quality",
        "weight": 20,
        "excellent": "Background, composition, and product placement feel professionally art-directed.",
    },
    {
        "key": "photorealism",
        "criterion": "Photorealism",
        "weight": 15,
        "excellent": "Edges, lighting, contact shadow, and scale look physically convincing.",
    },
    {
        "key": "prompt_adherence",
        "criterion": "Scene adherence",
        "weight": 10,
        "excellent": "The generated scene matches the selected template without unwanted objects.",
    },
    {
        "key": "publish_readiness",
        "criterion": "Publish readiness",
        "weight": 15,
        "excellent": "The image can be published with no corrective regeneration.",
    },
]

IMAGE_FAILURE_MODES = {
    "introduced_damage_or_wear": "Introduced cracks, scratches, wear, or damage",
    "changed_logo_or_text": "Changed logo, label, or visible text",
    "changed_color_or_material": "Changed product color, finish, or material",
    "altered_shape_or_hardware": "Altered silhouette, geometry, or hardware",
    "product_obscured_or_cropped": "Obscured or incorrectly cropped product",
    "unrealistic_scene_or_shadow": "Unrealistic edges, lighting, or shadow",
    "scene_does_not_match_request": "Scene does not match selected template",
}

STATUS_OPTIONS = [
    "generated",
    "pending_review",
    "needs_revision",
    "revised",
    "approved",
    "rejected",
    "exported",
    "failed",
]

CHANNEL_FIELDS = [
    ("seo_title", "SEO Title", 80),
    ("product_description", "Product Description", 160),
    ("instagram_caption", "Instagram Caption", 140),
    ("facebook_ad", "Facebook Ad", 130),
    ("tiktok_script", "TikTok Script", 180),
    ("shopee_description", "Shopee Description", 160),
    ("email_subject", "Email Subject", 70),
]


st.set_page_config(
    page_title="AI Product Studio",
    page_icon=":material/photo_camera:",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {background: #fcfbf8; color: #161817;}
    .block-container {max-width: 1220px; padding-top: 1.6rem; padding-bottom: 2.5rem;}
    [data-testid="stSidebar"] {background: #f6f3ed; border-right: 1px solid #e8e1d7;}
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #ede7de;
        padding: 0.75rem 0.9rem;
        border-radius: 14px;
    }
    div[data-testid="stTabs"] button {font-weight: 600; letter-spacing: .01em;}
    div[data-testid="stForm"] {
        background: #ffffff;
        border: 1px solid #ede7de;
        border-radius: 20px;
        padding: 1.1rem;
    }
    .stButton > button[kind="primary"], div[data-testid="stFormSubmitButton"] button[kind="primary"] {
        border-radius: 999px;
        min-height: 3rem;
        font-weight: 650;
    }
    .brand {
        font-size: .83rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .16em;
        color: #716554;
        margin-bottom: .8rem;
    }
    .hero-title {
        font-size: 2.65rem;
        line-height: 1.1;
        font-weight: 720;
        letter-spacing: -.04em;
        color: #171817;
        max-width: 710px;
        margin-bottom: .55rem;
    }
    .hero-subtitle {
        color: #635e57;
        font-size: 1.02rem;
        max-width: 670px;
        margin-bottom: 1.35rem;
    }
    .scene-card {
        border: 1px solid #ebe3d7;
        border-radius: 16px;
        padding: .9rem 1rem;
        background: #fbf8f3;
        margin: .4rem 0 .8rem;
    }
    .scene-tag {
        color: #8b7048;
        letter-spacing: .12em;
        font-size: .7rem;
        text-transform: uppercase;
        font-weight: 700;
    }
    .scene-title {font-size: 1.15rem; font-weight: 650; margin: .2rem 0;}
    .scene-copy {color: #665f56; font-size: .9rem;}
    .lock {
        display: inline-block;
        border-radius: 999px;
        background: #eff5ef;
        color: #31543a;
        font-size: .8rem;
        font-weight: 600;
        padding: .28rem .65rem;
        margin: .15rem .25rem .65rem 0;
    }
    .mini-card {
        min-height: 106px;
        border-radius: 13px;
        border: 1px solid #ede7de;
        background: #fff;
        padding: .65rem .7rem;
        margin-bottom: .55rem;
    }
    .mini-title {font-weight: 620; margin-bottom: .18rem;}
    .mini-copy {font-size: .8rem; color: #6b665f;}
    .result-title {font-size: 1.5rem; font-weight: 680; margin: 1.35rem 0 .1rem;}
    .muted {color: #6b665f;}
    </style>
    """,
    unsafe_allow_html=True,
)


def api_get(path: str, **params):
    response = requests.get(f"{API_URL}{path}", params=params or None, timeout=20)
    response.raise_for_status()
    return response.json()


def file_url(path: str | None) -> str | None:
    if not path:
        return None
    return f"{API_URL}/files?path={quote(path, safe='')}"


def fetch_assets(status: str | None = None):
    try:
        params = {"status": status} if status else {}
        return api_get("/assets", **params)
    except Exception:
        return []


def post_generation(files, data):
    return requests.post(f"{API_URL}/generate", files=files, data=data, timeout=420)


def patch_review(asset_id: str, payload: dict):
    response = requests.patch(f"{API_URL}/assets/{asset_id}/review", json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def post_image_evaluation(asset_id: str, payload: dict):
    response = requests.post(f"{API_URL}/assets/{asset_id}/evaluation", json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def build_visual_prompt(scene: dict, custom_direction: str, has_reference: bool) -> str:
    reference_rule = (
        "Use the optional reference image only for composition, lighting, and atmosphere; never take product "
        "shape, branding, labels, or condition from the reference image."
        if has_reference
        else "No style reference is supplied; follow this scene specification closely."
    )
    prompt = (
        f"{PRODUCT_IDENTITY_RULES}\n\n"
        f"Selected scene: {scene['title']}.\n{scene['direction']}\n\n"
        f"{SCENE_PRODUCTION_RULES}\n\n"
        f"{reference_rule}"
    )
    if custom_direction.strip():
        prompt += (
            "\n\nOptional seller art direction (apply only if it does not conflict with product identity rules):\n"
            + custom_direction.strip()
        )
    return prompt


def render_header():
    st.markdown('<div class="brand">AI Product Studio</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">One product photo. A polished scene in one click.</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">Choose a ready-made background and generate a publish-ready product image. '
        "Every scene is directed to protect the product's visible identity and detail.</div>",
        unsafe_allow_html=True,
    )


def render_sidebar():
    with st.sidebar:
        st.markdown('<div class="brand">Studio</div>', unsafe_allow_html=True)
        st.write("Create premium product imagery from one original photo.")
        st.markdown('<span class="lock">Identity lock active</span>', unsafe_allow_html=True)

        assets = fetch_assets()
        counts = Counter(asset["status"] for asset in assets)
        stat_cols = st.columns(2)
        stat_cols[0].metric("Created", len(assets))
        stat_cols[1].metric("Approved", counts.get("approved", 0))

        with st.expander("System status", expanded=False):
            try:
                health = api_get("/health")
                st.success("Ready to generate")
                st.caption(f"Visual pipeline: {health['visual_provider_chain']}")
                st.caption(f"Copy pipeline: {health['llm_provider_chain']}")
                if health.get("google_imagen_model"):
                    st.caption(f"Imagen fallback: {health['google_imagen_model']}")
                for warning in health.get("configuration_warnings", []):
                    st.warning(warning)
            except Exception:
                st.error("API offline. Start the backend to generate.")

        st.caption("Always review logos, labels, color, and condition details before publishing.")


def render_quality_report(report: dict):
    if not report:
        st.info("No quality report available.")
        return

    st.write(report.get("summary", "Quality report generated."))
    identity_assurance = report.get("identity_assurance") or {}
    best_provider = report.get("best_provider") or ""
    requires_identity_review = identity_assurance.get(
        "requires_identity_review",
        bool(best_provider) and "source_product_overlay" not in best_provider and best_provider != "original_fallback",
    )
    if requires_identity_review:
        st.warning("Product identity is unverified. Compare against the original image before approval.")
    elif identity_assurance.get("status") == "source_product_layer_retained":
        st.success("Source product layer retained. Human review is still required before publishing.")
    st.markdown("##### Automated technical screen")
    st.caption("These signals screen output image quality only; they do not prove product fidelity or scene realism.")
    scorecard = report.get("scorecard") or {}
    metric_cols = st.columns(3)
    for index, (key, value) in enumerate(scorecard.items()):
        with metric_cols[index % 3]:
            st.metric(key.replace("_", " ").title(), round(value, 4) if isinstance(value, float) else value)

    technical_diagnostics = report.get("technical_diagnostics") or {}
    if technical_diagnostics:
        st.markdown("##### Output diagnostics")
        diagnostic_rows = [
            {"Signal": key.replace("_", " ").title(), "Value": str(value)}
            for key, value in technical_diagnostics.items()
            if key != "interpretation"
        ]
        st.dataframe(diagnostic_rows, use_container_width=True, hide_index=True)
        st.caption(technical_diagnostics.get("interpretation", ""))

    recommendations = report.get("recommendations") or []
    if recommendations:
        for item in recommendations:
            st.write(f"- {item}")
    if report.get("disclaimer"):
        st.caption(report["disclaimer"])


def render_channel_outputs(channel_outputs: dict, llm_provider: str | None = None):
    if not channel_outputs:
        st.info("No copy available.")
        return

    tabs = st.tabs(["Listing", "Social", "Video", "CTA"])
    with tabs[0]:
        product_analysis = channel_outputs.get("product_analysis") or {}
        if product_analysis:
            st.markdown("##### Product observation from original photo")
            st.caption("Gemini-generated visual observation. Verify factual details before publication.")
            if product_analysis.get("detected_product_type"):
                st.write(f"**Detected product:** {product_analysis['detected_product_type']}")
            if product_analysis.get("observed_description"):
                st.write(product_analysis["observed_description"])
            visible_details = product_analysis.get("visible_details") or []
            if visible_details:
                st.write("**Visible details:** " + " | ".join(visible_details))
            condition_observations = product_analysis.get("condition_observations") or []
            if condition_observations:
                st.write("**Visible condition:** " + " | ".join(condition_observations))
            appeal_points = product_analysis.get("buyer_appeal_points") or []
            if appeal_points:
                st.write("**Buyer appeal:** " + " | ".join(appeal_points))
            unknown_details = product_analysis.get("unknown_or_unverified") or []
            if unknown_details:
                st.caption("Not verified from image: " + " | ".join(unknown_details))
            st.divider()
        elif llm_provider == "mock":
            st.info("Image-based product observation is unavailable because local copy fallback was used.")
        st.text_area("SEO Title", value=channel_outputs.get("seo_title", ""), height=70, disabled=True)
        st.text_area("Product Description", value=channel_outputs.get("product_description", ""), height=160, disabled=True)
        st.text_area("Marketplace Description", value=channel_outputs.get("shopee_description", ""), height=150, disabled=True)
    with tabs[1]:
        st.text_area("Instagram Caption", value=channel_outputs.get("instagram_caption", ""), height=150, disabled=True)
        st.text_area("Facebook Ad", value=channel_outputs.get("facebook_ad", ""), height=130, disabled=True)
        st.write(" ".join(channel_outputs.get("hashtags", [])))
    with tabs[2]:
        st.text_area("Short Video Script", value=channel_outputs.get("tiktok_script", ""), height=200, disabled=True)
    with tabs[3]:
        st.text_area("Email Subject", value=channel_outputs.get("email_subject", ""), height=70, disabled=True)
        st.write(" | ".join(channel_outputs.get("cta_suggestions", [])))


def render_generation_result(result: dict):
    st.markdown('<div class="result-title">Generated picture</div>', unsafe_allow_html=True)
    if result.get("error_message"):
        st.error(result["error_message"])
        return

    image_col, detail_col = st.columns([1.12, 0.88], gap="large")
    with image_col:
        if result.get("best_image_path"):
            st.image(file_url(result["best_image_path"]), use_container_width=True)
        st.caption("Check the generated image against the original product before approval.")
    with detail_col:
        provider_used = result.get("visual_provider_used") or "unknown"
        if "source_product_overlay" in provider_used:
            st.markdown('<span class="lock">Original transparent product layer retained</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="lock">AI identity lock active - inspect product surface</span>', unsafe_allow_html=True)
        st.write("Your scene is ready for review and export.")
        quality = result.get("quality_report") or {}
        score = (quality.get("scorecard") or {}).get("final_score")
        if score is not None:
            st.metric("Technical screen score", round(score, 4))
        requires_identity_review = (quality.get("identity_assurance") or {}).get(
            "requires_identity_review",
            "source_product_overlay" not in provider_used and provider_used != "original_fallback",
        )
        if requires_identity_review:
            st.warning("Not approved: compare product identity with the original image first.")
        st.caption(f"Image provider: {provider_used}")
        st.caption(f"Copy provider: {result.get('llm_provider_used') or 'unknown'}")
        st.caption(f"Best image: {result.get('best_variant_id') or 'single output'}")
        st.caption("Approve this picture in Review before export.")

    variants = result.get("variants") or []
    if len(variants) > 1:
        with st.expander("Compare generated variations"):
            cols = st.columns(min(3, len(variants)))
            for index, variant in enumerate(variants):
                with cols[index % len(cols)]:
                    label = variant["variant_id"]
                    if label == result.get("best_variant_id"):
                        label += " - selected"
                    st.markdown(f"**{label}**")
                    st.image(file_url(variant["image_path"]), use_container_width=True)

    with st.expander("Quality details"):
        render_quality_report(result.get("quality_report") or {})
    with st.expander("Gemini product description and generated copy"):
        render_channel_outputs(
            result.get("channel_outputs") or {},
            result.get("llm_provider_used") or "",
        )


def render_scene_gallery():
    with st.expander(f"Browse all {len(SCENE_TEMPLATES)} ready-made scenes", expanded=False):
        columns = st.columns(3)
        for index, scene in enumerate(SCENE_TEMPLATES.values()):
            with columns[index % 3]:
                st.markdown(
                    f'<div class="mini-card"><div class="scene-tag">{scene["group"]}</div>'
                    f'<div class="mini-title">{scene["title"]}</div>'
                    f'<div class="mini-copy">{scene["description"]}</div></div>',
                    unsafe_allow_html=True,
                )


def render_studio_tab():
    upload_col, scene_col = st.columns([0.92, 1.08], gap="large")
    with upload_col:
        st.markdown("#### 1. Upload product")
        product_image = st.file_uploader(
            "Original product photo",
            type=["jpg", "jpeg", "png", "webp"],
            key="studio_product_image",
            help="For the most faithful surface detail, use a high-resolution transparent-background PNG cutout. Clear JPG or WEBP photos use identity-preserving AI editing.",
            label_visibility="collapsed",
        )
        if product_image:
            st.image(product_image, caption="Original product", use_container_width=True)
            if product_image.type == "image/png":
                st.caption("Transparent PNG products use source-product overlay when transparency is present.")
            else:
                st.caption("Exact fidelity mode is available with a transparent-background PNG product cutout.")
        else:
            st.info("Drop a JPG, PNG, or WEBP product photo here.")

    with scene_col:
        with st.form("one_click_generation_form"):
            st.markdown("#### 2. Select scene")
            scene_id = st.selectbox(
                "Scene template",
                list(SCENE_TEMPLATES),
                format_func=lambda value: f"{SCENE_TEMPLATES[value]['group']} | {SCENE_TEMPLATES[value]['title']}",
                label_visibility="collapsed",
            )
            scene = SCENE_TEMPLATES[scene_id]
            st.markdown(
                f'<div class="scene-card"><div class="scene-tag">{scene["group"]}</div>'
                f'<div class="scene-title">{scene["title"]}</div>'
                f'<div class="scene-copy">{scene["description"]}</div></div>',
                unsafe_allow_html=True,
            )
            st.markdown('<span class="lock">Product identity lock included</span>', unsafe_allow_html=True)
            st.caption("The template changes the scene, not the product design or visible condition.")

            with st.expander("Optional details and advanced controls", expanded=False):
                product_name = st.text_input("Product name", placeholder="Optional")
                brand_name = st.text_input("Brand / shop", placeholder="Optional")
                price = st.text_input("Price", placeholder="Optional")
                offer = st.text_input("Offer", placeholder="Optional")
                reference_image = st.file_uploader(
                    "Style reference photo",
                    type=["jpg", "jpeg", "png", "webp"],
                    key="studio_reference_image",
                    help="Used for mood and layout only; the original photo remains the product source.",
                )
                language = st.selectbox("Copy language", ["Vietnamese", "English", "Vietnamese + English"])
                num_variants = st.slider("Number of variations", min_value=1, max_value=4, value=1)
                custom_direction = st.text_area(
                    "Extra art direction",
                    placeholder="Optional: e.g. leave more empty space at the top.",
                    height=76,
                )
                st.caption("Gemini copy uses the original product photo to describe visible details truthfully.")

            submitted = st.form_submit_button(
                "Generate picture",
                type="primary",
                use_container_width=True,
                disabled=product_image is None,
            )

    render_scene_gallery()

    if not submitted:
        if st.session_state.get("latest_generation_result"):
            render_generation_result(st.session_state["latest_generation_result"])
        return

    files = {
        "product_image": (
            product_image.name,
            product_image.getvalue(),
            product_image.type,
        )
    }
    if reference_image:
        files["reference_image"] = (
            reference_image.name,
            reference_image.getvalue(),
            reference_image.type,
        )

    seller_product_name = product_name.strip() or "Featured product"
    seller_brand_name = brand_name.strip()
    data = {
        "campaign_name": f"{seller_brand_name or 'Product Studio'} | {scene['title']}",
        "product_name": seller_product_name,
        "brand_name": seller_brand_name,
        "target_audience": scene["audience"],
        "customer_persona": "",
        "platform": scene["platform"],
        "marketing_objective": scene["objective"],
        "funnel_stage": "consideration",
        "copy_framework": "AIDA",
        "selling_points": "Accurate product presentation in a premium ready-to-publish scene.",
        "price": price.strip(),
        "offer": offer.strip(),
        "language": language,
        "compliance_notes": (
            "Do not assert authenticity, new condition, official partnership, or materials unless supplied. "
            "Preserve visible condition and labeling."
        ),
        "visual_prompt": build_visual_prompt(scene, custom_direction, reference_image is not None),
        "content_prompt": DEFAULT_CONTENT_PROMPT,
        "tone": scene["tone"],
        "num_variants": num_variants,
    }

    try:
        with st.spinner("Creating your product picture..."):
            response = post_generation(files=files, data=data)
        if response.status_code != 200:
            st.error(response.text)
            return
        result = response.json()
        st.session_state["latest_generation_result"] = result
        render_generation_result(result)
    except requests.RequestException as exc:
        st.error(f"Generation request failed: {exc}")


def render_asset_review(asset: dict):
    with st.container(border=True):
        top_cols = st.columns([0.8, 1.2])
        with top_cols[0]:
            if asset.get("best_image_path"):
                st.image(file_url(asset["best_image_path"]), use_container_width=True)
        with top_cols[1]:
            st.markdown(f"### {asset.get('campaign_name') or asset.get('product_name') or 'Untitled image'}")
            st.caption(
                f"{asset.get('status')} | {asset.get('platform') or 'no channel'} | "
                f"technical screen {round(asset.get('best_score') or 0, 4)}"
            )
            st.write(asset.get("caption") or "")
            st.caption(" ".join(asset.get("hashtags") or []))
            with st.expander("Quality report"):
                render_quality_report(asset.get("quality_report") or {})

    variants = asset.get("variants") or []
    best_options = [variant["variant_id"] for variant in variants]
    current_best = asset.get("best_variant_id")
    if current_best not in best_options and best_options:
        current_best = best_options[0]

    with st.expander("Edit, approve, or export"):
        if len(variants) > 1:
            variant_cols = st.columns(min(3, len(variants)))
            for index, variant in enumerate(variants):
                with variant_cols[index % len(variant_cols)]:
                    st.caption(variant["variant_id"])
                    st.image(file_url(variant["image_path"]), use_container_width=True)

        channel_outputs = dict(asset.get("channel_outputs") or {})
        quality = asset.get("quality_report") or {}
        identity_assurance = quality.get("identity_assurance") or {}
        provider_used = asset.get("visual_provider_used") or ""
        requires_identity_review = identity_assurance.get(
            "requires_identity_review",
            "source_product_overlay" not in provider_used and provider_used != "original_fallback",
        )
        with st.form(f"review_form_{asset['id']}"):
            review_status_options = [item for item in STATUS_OPTIONS if item != "exported"]
            if asset.get("status") == "exported":
                review_status_options.append("exported")
            status_index = (
                review_status_options.index(asset["status"])
                if asset["status"] in review_status_options
                else 0
            )
            status = st.selectbox("Status", review_status_options, index=status_index)
            best_variant_id = st.selectbox(
                "Selected image",
                best_options or [asset.get("best_variant_id") or ""],
                index=(best_options.index(current_best) if current_best in best_options else 0),
            )
            caption = st.text_area("Caption", value=asset.get("caption") or "", height=110)
            hashtags_text = st.text_input("Hashtags", value=" ".join(asset.get("hashtags") or []))
            identity_verified = st.checkbox(
                "I compared the selected image against the original and verified product details and condition.",
                value=False,
                help="Required to approve an AI-edited image unless its source product layer was retained.",
            )
            if requires_identity_review:
                st.warning("Approval is blocked until this identity check is confirmed.")

            st.markdown("##### Generated copy")
            description = st.text_area("Product Description", value=asset.get("description") or "", height=120)
            for field_key, label, height in CHANNEL_FIELDS:
                channel_outputs[field_key] = st.text_area(
                    label,
                    value=str(channel_outputs.get(field_key, "")),
                    height=height,
                    key=f"{asset['id']}_{field_key}",
                )
            ctas = st.text_input(
                "CTA Suggestions",
                value=" | ".join(channel_outputs.get("cta_suggestions", [])),
                key=f"{asset['id']}_ctas",
            )
            channel_outputs["cta_suggestions"] = [item.strip() for item in ctas.split("|") if item.strip()]

            reviewer_note = st.text_area("Reviewer note", value=asset.get("reviewer_note") or "", height=80)
            action_cols = st.columns(3)
            save_clicked = action_cols[0].form_submit_button("Save")
            revision_clicked = action_cols[1].form_submit_button("Revise")
            approve_clicked = action_cols[2].form_submit_button("Approve", type="primary")

        if save_clicked or revision_clicked or approve_clicked:
            next_status = "needs_revision" if revision_clicked else "approved" if approve_clicked else status
            payload = {
                "status": next_status,
                "identity_verified": identity_verified,
                "reviewer_note": reviewer_note,
                "description": description,
                "caption": caption,
                "hashtags": [item.strip() for item in hashtags_text.split() if item.strip()],
                "channel_outputs": channel_outputs,
                "best_variant_id": best_variant_id,
            }
            try:
                patch_review(asset["id"], payload)
                st.success("Review saved.")
                st.rerun()
            except Exception as exc:
                st.error(f"Review update failed: {exc}")

        if asset.get("id") and asset.get("status") in {"approved", "exported"}:
            st.link_button(
                "Export package",
                f"{API_URL}/assets/{asset['id']}/export",
                use_container_width=True,
            )
        elif asset.get("id"):
            st.caption("Export unlocks after review approval.")


def render_review_tab():
    st.subheader("Review")
    st.caption("Verify visible product details before approving images for publication.")
    status_filter = st.selectbox(
        "Filter",
        ["all"] + STATUS_OPTIONS,
        index=0,
        key="review_status_filter",
        label_visibility="collapsed",
    )
    assets = fetch_assets(None if status_filter == "all" else status_filter)
    if not assets:
        st.info("No images found for this filter.")
        return
    for asset in assets:
        render_asset_review(asset)


def render_library_tab():
    st.subheader("Library")
    assets = fetch_assets()
    if not assets:
        st.info("Your generated product pictures will appear here.")
        return

    counts = Counter(asset["status"] for asset in assets)
    metric_cols = st.columns(4)
    metric_cols[0].metric("All images", len(assets))
    metric_cols[1].metric("Generated", counts.get("generated", 0))
    metric_cols[2].metric("Approved", counts.get("approved", 0))
    metric_cols[3].metric("Exported", counts.get("exported", 0))

    rows = []
    for asset in assets:
        rows.append(
            {
                "picture": asset.get("campaign_name"),
                "status": asset.get("status"),
                "channel": asset.get("platform"),
                "technical_screen": asset.get("best_score"),
                "created": asset.get("created_at"),
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_evaluation_tab():
    st.subheader("Evaluation")
    st.caption(
        "Benchmark image-generation models here without adding steps to the one-click Studio flow."
    )

    assets = fetch_assets()
    if assets:
        counts = Counter(asset["status"] for asset in assets)
        scored_assets = [
            asset for asset in assets if isinstance(asset.get("best_score"), (int, float))
        ]
        average_score = (
            sum(asset["best_score"] for asset in scored_assets) / len(scored_assets)
            if scored_assets
            else 0
        )
        metric_cols = st.columns(4)
        metric_cols[0].metric("Generated samples", len(assets))
        metric_cols[1].metric("Average technical screen", f"{average_score:.2f}")
        metric_cols[2].metric("Approved", counts.get("approved", 0) + counts.get("exported", 0))
        metric_cols[3].metric("Needs revision", counts.get("needs_revision", 0))
        st.caption("Technical screening is automatic; image-model quality comes from saved side-by-side evaluations.")

    st.markdown("#### Image model benchmark")
    try:
        model_summary = api_get("/evaluation/image-models")
    except Exception:
        model_summary = {"models": [], "total_evaluations": 0}
    if model_summary.get("models"):
        summary_rows = [
            {
                "Model / provider": row["provider"],
                "Samples": row["samples"],
                "Avg score / 100": row["average_weighted_score"],
                "Avg fidelity / 5": row["average_product_fidelity"],
                "Identity pass": f"{row['identity_pass_rate']}%",
                "Publishable": f"{row['publishable_rate']}%",
                "Top failures": ", ".join(
                    IMAGE_FAILURE_MODES.get(mode, mode) for mode in row["top_failure_modes"]
                ) or "None recorded",
            }
            for row in model_summary["models"]
        ]
        st.dataframe(summary_rows, use_container_width=True, hide_index=True)
        st.caption(model_summary.get("method", ""))
    else:
        st.info("No saved model evaluations yet. Score an output below to establish a Cloudflare baseline.")

    st.markdown("#### Fidelity-weighted rubric")
    rubric_rows = [
        {
            "Criterion": item["criterion"],
            "Weight": f"{item['weight']}%",
            "Excellent standard": item["excellent"],
        }
        for item in IMAGE_MODEL_RUBRIC
    ]
    st.dataframe(rubric_rows, use_container_width=True, hide_index=True)

    if not assets:
        st.info("Generate a picture to start an image-model evaluation.")
        return

    st.markdown("#### Evaluate generated image")
    selected_id = st.selectbox(
        "Picture to evaluate",
        [asset["id"] for asset in assets],
        format_func=lambda asset_id: next(
            (
                asset.get("campaign_name") or asset.get("product_name") or asset_id
                for asset in assets
                if asset["id"] == asset_id
            ),
            asset_id,
        ),
    )
    selected_asset = next(asset for asset in assets if asset["id"] == selected_id)
    selected_report = selected_asset.get("quality_report") or {}
    identity_assurance = selected_report.get("identity_assurance") or {}
    provider_used = selected_asset.get("visual_provider_used") or ""
    requires_identity_review = identity_assurance.get(
        "requires_identity_review",
        "source_product_overlay" not in provider_used and provider_used != "original_fallback",
    )
    best_variant = next(
        (
            variant for variant in selected_asset.get("variants", [])
            if variant.get("variant_id") == selected_asset.get("best_variant_id")
        ),
        {},
    )
    evaluated_provider = best_variant.get("provider") or provider_used or "unknown"

    image_cols = st.columns(2, gap="large")
    with image_cols[0]:
        st.markdown("**Original product**")
        if selected_asset.get("product_image_path"):
            st.image(file_url(selected_asset["product_image_path"]), use_container_width=True)
    with image_cols[1]:
        st.markdown("**Generated result**")
        if selected_asset.get("best_image_path"):
            st.image(file_url(selected_asset["best_image_path"]), use_container_width=True)
    st.caption(f"Image provider under evaluation: {evaluated_provider}")

    with st.expander("Automated technical signals", expanded=False):
        render_quality_report(selected_report)

    with st.form(f"model_evaluation_{selected_id}"):
        st.markdown("##### Record model quality")
        compared_with_original = st.checkbox(
            "I compared the generated product against the original image.",
            value=False,
            help="Required before saving a valid model evaluation.",
        )
        selected_failure_labels = st.multiselect(
            "Observed failures",
            options=list(IMAGE_FAILURE_MODES),
            format_func=lambda mode: IMAGE_FAILURE_MODES[mode],
            help="Select every visible failure. Product-identity failures make this output unusable.",
        )
        rating_cols = st.columns(2)
        ratings = {}
        total = 0.0
        for index, item in enumerate(IMAGE_MODEL_RUBRIC):
            with rating_cols[index % 2]:
                ratings[item["key"]] = st.slider(
                    f"{item['criterion']} ({item['weight']}%)",
                    min_value=1,
                    max_value=5,
                    value=3,
                    key=f"image_eval_{selected_id}_{item['key']}",
                )
            total += ratings[item["key"]] / 5 * item["weight"]
        reviewer_comment = st.text_area(
            "Evidence note",
            placeholder="Example: new crack visible on leather at lower-right edge; unsuitable for listing.",
            height=85,
        )
        st.metric("Fidelity-weighted model score", f"{total:.1f} / 100")
        save_evaluation = st.form_submit_button("Save model evaluation", type="primary")

    if save_evaluation:
        payload = {
            "compared_with_original": compared_with_original,
            **ratings,
            "failure_modes": selected_failure_labels,
            "reviewer_comment": reviewer_comment,
        }
        try:
            saved = post_image_evaluation(selected_id, payload)
            decision = (saved.get("payload") or {}).get("decision", "recorded")
            st.success(f"Model evaluation saved: {decision.replace('_', ' ')}.")
            st.rerun()
        except requests.HTTPError as exc:
            message = exc.response.json().get("detail", str(exc)) if exc.response is not None else str(exc)
            st.error(message)
        except Exception as exc:
            st.error(f"Evaluation could not be saved: {exc}")

    if requires_identity_review:
        st.warning("This AI-edited output still requires formal identity verification in Review before approval.")


render_header()
render_sidebar()

tab_studio, tab_review, tab_library, tab_evaluation = st.tabs(["Studio", "Review", "Library", "Evaluation"])

with tab_studio:
    render_studio_tab()

with tab_review:
    render_review_tab()

with tab_library:
    render_library_tab()

with tab_evaluation:
    render_evaluation_tab()
