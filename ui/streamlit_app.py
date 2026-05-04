import requests
import streamlit as st


API_URL = "http://127.0.0.1:8000"

DEFAULT_VISUAL_PROMPT = """Use the uploaded product image as the exact product identity.
Use the uploaded reference picture as the target composition and visual style.
Keep the same shirt design, color, logo, sponsor text, collar, sleeves, fabric texture and visible details.
Generate a realistic product marketing photo where the shirt is naturally lying flat on a football field grass under warm sunlight.
Match the reference image format, camera angle, perspective, lighting, shadows and realistic wrinkles.
Do not add a person. Do not hang the shirt. Do not change the shirt identity. Do not crop out the product."""

st.set_page_config(
    page_title="AI Product Studio Reference Editing",
    page_icon="🧥",
    layout="wide",
)

st.title("AI Product Studio — Reference-based Image Editing")
st.caption("Gemini Image / Nano Banana → Replicate FLUX Kontext → Mock fallback")

with st.sidebar:
    st.header("System Health")
    try:
        health = requests.get(f"{API_URL}/health", timeout=5).json()
        st.success(f"API online: {health['app']}")
        st.write("Visual chain:", health["visual_provider_chain"])
        st.write("LLM chain:", health["llm_provider_chain"])
        st.write("Gemini key loaded:", health["has_gemini_key"])
        st.write("Replicate key loaded:", health["has_replicate_key"])
        st.write("Gemini image model:", health["gemini_image_model"])
    except Exception:
        st.error("API offline. Run backend first.")

tab_generate, tab_review = st.tabs(["Generate", "Review Queue"])

with tab_generate:
    col_upload_1, col_upload_2 = st.columns(2)

    with col_upload_1:
        product_image = st.file_uploader(
            "Upload PRODUCT image",
            type=["jpg", "jpeg", "png"],
            key="product_image",
        )
        if product_image:
            st.image(product_image, caption="Product image", width=330)

    with col_upload_2:
        reference_image = st.file_uploader(
            "Upload REFERENCE picture optional",
            type=["jpg", "jpeg", "png"],
            key="reference_image",
        )
        if reference_image:
            st.image(reference_image, caption="Reference picture", width=330)

    col_a, col_b = st.columns(2)
    with col_a:
        product_name = st.text_input("Product name", value="Manchester United Jersey")
        num_variants = st.slider("Number of variants", min_value=1, max_value=4, value=2)
    with col_b:
        tone = st.text_input("Tone", value="premium, emotional, sporty, product-selling")

    visual_prompt = st.text_area("Visual editing prompt", value=DEFAULT_VISUAL_PROMPT, height=220)

    content_prompt = st.text_area(
        "Content prompt",
        value="Write a Vietnamese product description, Instagram caption and hashtags for selling this item.",
        height=100,
    )

    if st.button("Generate Reference-based Marketing Asset", type="primary"):
        if not product_image:
            st.error("Please upload a product image.")
        else:
            with st.spinner("Generating through Gemini Image / FLUX Kontext provider chain..."):
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

                data = {
                    "product_name": product_name,
                    "visual_prompt": visual_prompt,
                    "content_prompt": content_prompt,
                    "tone": tone,
                    "num_variants": num_variants,
                }

                res = requests.post(f"{API_URL}/generate", files=files, data=data)

            if res.status_code != 200:
                st.error(res.text)
            else:
                result = res.json()
                st.success(
                    f"Generated. Visual provider: {result['visual_provider_used']} | "
                    f"LLM provider: {result['llm_provider_used']}"
                )

                if result.get("error_message"):
                    st.error(result["error_message"])

                st.subheader("Best Image")
                if result.get("best_image_path"):
                    st.image(f"{API_URL}/files?path={result['best_image_path']}", width=640)

                st.subheader("Generated Description")
                st.write(result["description"])

                st.subheader("Caption")
                st.write(result["caption"])
                st.write(" ".join(result["hashtags"]))

                st.subheader("Variants + Metrics")
                cols = st.columns(2)
                for idx, v in enumerate(result["variants"]):
                    with cols[idx % 2]:
                        label = "BEST" if v["variant_id"] == result["best_variant_id"] else v["variant_id"]
                        st.markdown(f"### {label}")
                        st.caption(f"Provider: {v.get('provider')}")
                        st.image(f"{API_URL}/files?path={v['image_path']}")
                        st.json(v["scores"])

with tab_review:
    st.subheader("Human-in-the-loop Review")

    status_filter = st.selectbox(
        "Filter",
        ["", "pending_review", "approved", "rejected", "failed"],
        format_func=lambda x: "all" if x == "" else x,
    )

    url = f"{API_URL}/assets"
    if status_filter:
        url += f"?status={status_filter}"

    try:
        assets = requests.get(url).json()
    except Exception:
        assets = []
        st.error("Cannot load assets. Check backend.")

    for asset in assets:
        with st.container(border=True):
            col1, col2 = st.columns([1, 2])

            with col1:
                if asset.get("best_image_path"):
                    st.image(f"{API_URL}/files?path={asset['best_image_path']}", width=330)
                st.metric("Best Score", round(asset.get("best_score") or 0, 4))
                st.write("Visual provider:", asset.get("visual_provider_used"))
                st.write("LLM provider:", asset.get("llm_provider_used"))

            with col2:
                st.markdown(f"### {asset.get('product_name') or 'Unnamed Product'}")
                st.write(f"**Status:** {asset['status']}")
                st.write(asset.get("caption") or "")
                st.write(" ".join(asset.get("hashtags") or []))

                with st.expander("Variant metrics"):
                    for v in asset.get("variants", []):
                        st.write(v["variant_id"], v.get("provider"), v["scores"])

                note = st.text_area(
                    "Reviewer note",
                    key=f"note_{asset['id']}",
                    value=asset.get("reviewer_note") or "",
                )

                c1, c2, c3 = st.columns(3)

                if c1.button("Approve", key=f"approve_{asset['id']}"):
                    requests.patch(
                        f"{API_URL}/assets/{asset['id']}/review",
                        json={"status": "approved", "reviewer_note": note},
                    )
                    st.rerun()

                if c2.button("Reject", key=f"reject_{asset['id']}"):
                    requests.patch(
                        f"{API_URL}/assets/{asset['id']}/review",
                        json={"status": "rejected", "reviewer_note": note},
                    )
                    st.rerun()

                c3.link_button("Download ZIP", f"{API_URL}/assets/{asset['id']}/export")
