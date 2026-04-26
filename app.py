import streamlit as st
import requests
import os
from dotenv import load_dotenv
import base64
import tempfile
import io
from streamlit_image_comparison import image_comparison
import replicate
from PIL import Image

# ---------------- PAGE CONFIG ---------------- #

st.set_page_config(
    page_title="PixelPioneers Studio",
    page_icon="assets/favicon/favicon.ico",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------- LOAD ENV ---------------- #

load_dotenv()

STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

# ---------------- SESSION STATE ---------------- #

if "history" not in st.session_state:
    st.session_state.history = []

if "generated_count" not in st.session_state:
    st.session_state.generated_count = 0

if "enhanced_count" not in st.session_state:
    st.session_state.enhanced_count = 0

if "selected_menu" not in st.session_state:
    st.session_state.selected_menu = "🎨 AI Image Generation"

if "last_generated" not in st.session_state:
    st.session_state.last_generated = None

if "last_generated_original" not in st.session_state:
    st.session_state.last_generated_original = None

if "enhance_original" not in st.session_state:
    st.session_state.enhance_original = None

if "enhance_result" not in st.session_state:
    st.session_state.enhance_result = None

if "enhance_scale" not in st.session_state:
    st.session_state.enhance_scale = 4

# ---------------- CLEAN CSS ---------------- #

st.markdown("""
<style>
/* Full-width main container */
.block-container {
    padding-top: 1rem;
    padding-left: 2rem;
    padding-right: 2rem;
    max-width: 100%;
}

/* Sticky header row */
.header-sticky {
    position: sticky;
    top: 0;
    z-index: 40;
    background: transparent;
    padding: 15px 0 8px 0;
    margin-bottom: 10px;
}

/* Hamburger button styling */
.hamburger-btn div.stButton > button {
    background: rgba(255,255,255,0.15) !important;
    color: white !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    border-radius: 10px !important;
    padding: 8px 16px !important;
    font-size: 22px !important;
    min-width: auto !important;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2) !important;
    transition: all 0.3s ease !important;
}
.hamburger-btn div.stButton > button:hover {
    background: rgba(255,255,255,0.3) !important;
    transform: scale(1.05);
}

/* Section headers - dark mode compatible */
h2, h3 {
    color: #fafafa;
    margin-bottom: 1rem;
}

/* History grid items - dark mode compatible */
.history-item {
    padding: 10px;
    border-radius: 12px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    margin-bottom: 10px;
    text-align: center;
}

/* Crew card - dark mode compatible */
.crew-col > div {
    display: flex;
    justify-content: center;
}
.crew-col .stContainer {
    text-align: center;
}
.crew-col img {
    width: 150px !important;
    height: 150px !important;
    object-fit: cover !important;
    border-radius: 50% !important;
    display: block !important;
    margin: 0 auto 10px auto !important;
}

/* Responsive breakpoints */
@media (max-width: 768px) {
    .header-sticky { padding: 22px 0 8px 0; }
    .hamburger-btn div.stButton > button { margin-top: 4px !important; }
}
</style>
""", unsafe_allow_html=True)

# ---------------- PRESETS ---------------- #

PRESETS = {
    "None": "",
    "Cinematic": "cinematic lighting, ultra realistic, 4k, dramatic",
    "Anime": "anime style, vibrant colors",
    "Fantasy": "fantasy art, magical",
    "Cyberpunk": "cyberpunk style, neon lights",
    "Custom": "CUSTOM"
}

# ---------------- FUNCTIONS ---------------- #

def generate_image(prompt):
    url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"

    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    body = {
        "text_prompts": [{"text": prompt}],
        "cfg_scale": 7,
        "height": 1024,
        "width": 1024,
        "samples": 1,
        "steps": 30
    }

    res = requests.post(url, headers=headers, json=body)

    if res.status_code != 200:
        return None, res.text

    data = res.json()
    img_bytes = base64.b64decode(data["artifacts"][0]["base64"])
    return img_bytes, None


def enhance_image(image_path, scale=4):
    try:
        with open(image_path, "rb") as f:
            output = replicate.run(
                "nightmareai/real-esrgan",
                input={"image": f, "scale": scale}
            )
        if isinstance(output, str):
            res = requests.get(output)
            return res.content, None
        elif isinstance(output, list) and len(output) > 0:
            res = requests.get(output[0])
            return res.content, None
        else:
            return None, "Unexpected output format from Replicate"
    except Exception as e:
        return None, str(e)


def img_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# ---------------- TOP NAVBAR ---------------- #

pages = ["Dashboard", "AI Image Generation", "AI Image Enhance", "History", "Crew"]
icons = ["📊", "🎨", "✨", "🖼️", "👥"]

@st.dialog("Menu")
def nav_dialog():
    for i, (page, icon) in enumerate(zip(pages, icons)):
        full_label = f"{icon} {page}"
        if st.button(full_label, key=f"nav_popup_{i}", use_container_width=True):
            st.session_state.selected_menu = full_label
            st.session_state.last_generated = None
            st.session_state.last_generated_original = None
            st.rerun()

# Load banner image as base64
with open("assets/banner/banner.png", "rb") as f:
    banner_b64 = base64.b64encode(f.read()).decode()

# Sticky header with hamburger + banner
st.markdown('<div class="header-sticky">', unsafe_allow_html=True)

header_left, header_right = st.columns([1, 20])
with header_left:
    if st.button("☰", key="hamburger"):
        nav_dialog()
with header_right:
    st.markdown(f'<img src="data:image/png;base64,{banner_b64}" style="max-height:50px;width:auto;">', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

menu = st.session_state.selected_menu

# ---------------- DASHBOARD ---------------- #

if menu == "📊 Dashboard":
    st.subheader("📊 Dashboard")

    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.metric("Images Generated", st.session_state.generated_count)
    with col2:
        with st.container(border=True):
            st.metric("Images Upscaled", st.session_state.enhanced_count)
    with col3:
        with st.container(border=True):
            st.metric("Models Used", "Diffusion + GAN")

    st.divider()

    left, right = st.columns([1, 2])
    with left:
        st.markdown("### ⚡ Quick Start")
        st.markdown("""
        - 🎨 **Generate** images using AI  
        - ✨ **Enhance** with GAN  
        - 🖼️ **View** results in History  
        """)

    with right:
        st.markdown("### 📄 About")
        st.markdown("""
        **PixelPioneers Studio** is an AI-powered platform for generating and enhancing images through a user-friendly Streamlit interface.

        **🧠 Models & APIs Used**
        - **Image Generation:** [Stability AI](https://stability.ai/) — `stable-diffusion-xl-1024-v1-0` (Diffusion Model)
        - **Image Enhancement:** [Replicate AI](https://replicate.com/) — `nightmareai/real-esrgan` (Generative Adversarial Network)

        **🎨 Why Diffusion for Generation?**
        Stable Diffusion XL (SDXL) is a latent diffusion model that generates high-fidelity, diverse images by iteratively denoising random noise conditioned on text prompts. Diffusion models outperform traditional GANs for generation because they:
        - Avoid **mode collapse**, producing highly diverse outputs
        - Deliver superior **prompt adherence** and photorealistic detail
        - Scale effectively to high resolutions (1024×1024)

        **✨ Why GAN for Enhancement?**
        Real-ESRGAN is a true **Generative Adversarial Network** optimized for super-resolution. Its architecture consists of:
        - **Generator:** A deep CNN that upscales low-resolution images while restoring realistic textures and sharp details
        - **Discriminator:** A perceptual network that adversarially trains the generator to produce outputs indistinguishable from authentic high-resolution images
        This adversarial approach yields significantly sharper, more natural results than bicubic interpolation or pure regression-based upscalers.

        **📋 Topic Justification**
        The project title *"AI Image Generation and Enhancement Studio using GANs"* is justified as follows:
        1. **Generation** leverages state-of-the-art **diffusion technology** (Stability AI SDXL) to synthesize novel images from text descriptions — representing the cutting edge of generative AI
        2. **Enhancement** explicitly employs a **GAN architecture** (Real-ESRGAN with Generator + Discriminator) for intelligent upscaling, fulfilling the core GAN requirement
        3. **Streamlit** provides the **user-friendly interface**, democratizing access to these powerful models through an intuitive, no-code web application
        4. Together, the studio unifies both **generative** (diffusion-based creation) and **adversarial** (GAN-based enhancement) paradigms in a single cohesive platform
        """)

# ---------------- GENERATE ---------------- #

elif menu == "🎨 AI Image Generation":
    st.subheader("🎨 AI Image Generation")

    left_col, right_col = st.columns([1, 1.2])

    with left_col:
        with st.container(border=True):
            st.markdown("#### 📝 Prompt Settings")
            prompt = st.text_area("Enter your prompt", height=120, key="gen_prompt")

            preset = st.selectbox("Style Preset", list(PRESETS.keys()), key="gen_preset")

            custom_style = ""
            if preset == "Custom":
                custom_style = st.text_input("Describe your custom style", key="gen_custom")

            auto_enhance = st.radio("Auto-enhance generated image?", ["Yes", "No"], horizontal=True, key="gen_auto_enhance")

            enhance_scale = 4
            if auto_enhance == "Yes":
                enhance_scale = int(st.selectbox("Enhancement Scale", ["2x", "4x", "8x"], index=1, key="gen_enhance_scale").replace("x", ""))

            st.divider()
            generate_clicked = st.button("🚀 Generate Image", type="primary", use_container_width=True)

    with right_col:
        with st.container(border=True):
            st.markdown("#### 🖼️ Result")
            if st.session_state.last_generated is not None:
                st.image(st.session_state.last_generated, use_container_width=True)
                st.download_button(
                    "⬇️ Download Image",
                    st.session_state.last_generated,
                    "generated.png",
                    use_container_width=True
                )
            else:
                st.info("Your generated image will appear here. Enter a prompt and click Generate!")

    if generate_clicked:
        if not prompt:
            st.warning("Please enter a prompt first.")
        else:
            parts = [prompt]

            if preset not in ["None", "Custom"]:
                parts.append(PRESETS[preset])

            if preset == "Custom" and custom_style:
                parts.append(custom_style)

            final_prompt = ", ".join(parts)

            with st.spinner("Generating your masterpiece..."):
                img, err = generate_image(final_prompt)

                if err:
                    st.error(f"Generation failed: {err}")
                else:
                    if auto_enhance == "Yes":
                        with st.spinner("Auto-enhancing via GAN Model..."):
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                                tmp.write(img)
                                tmp_path = tmp.name

                            enhanced_bytes, enhance_err = enhance_image(tmp_path, scale=enhance_scale)
                            os.remove(tmp_path)

                            if enhance_err:
                                st.warning(f"Generated successfully but auto-enhancement failed: {enhance_err}")
                                st.session_state.last_generated = img
                                st.session_state.last_generated_original = None
                                st.session_state.history.append(img)
                                st.session_state.generated_count += 1
                                st.toast("✨ Image generated successfully!", icon="🎉")
                            else:
                                st.session_state.last_generated = enhanced_bytes
                                st.session_state.last_generated_original = img
                                st.session_state.history.append(enhanced_bytes)
                                st.session_state.generated_count += 1
                                st.session_state.enhanced_count += 1
                                st.toast("✨ Image generated & enhanced successfully!", icon="🎉")
                    else:
                        st.session_state.last_generated = img
                        st.session_state.last_generated_original = None
                        st.session_state.history.append(img)
                        st.session_state.generated_count += 1
                        st.toast("✨ Image generated successfully!", icon="🎉")
                    st.rerun()

    if st.session_state.last_generated_original is not None and st.session_state.last_generated is not None:
        st.divider()
        st.markdown("#### 🔍 Side-by-Side Comparison")
        image_comparison(
            img1=Image.open(io.BytesIO(st.session_state.last_generated_original)),
            img2=Image.open(io.BytesIO(st.session_state.last_generated)),
            label1="Original",
            label2="Enhanced"
        )

# ---------------- ENHANCE ---------------- #

elif menu == "✨ AI Image Enhance":
    st.subheader("✨ AI Enhance / Upscale")

    left_col, right_col = st.columns([1, 1.5])

    with left_col:
        with st.container(border=True):
            st.markdown("#### 📤 Upload & Settings")
            file = st.file_uploader("Upload image", type=["png", "jpg", "jpeg"], key="enhance_uploader")

            if file is not None:
                original = file.read()
                input_img = Image.open(io.BytesIO(original)).convert("RGB")
                st.session_state.enhance_original = input_img

                scale = st.selectbox("Upscale Factor", [2, 4, 8], index=1, key="enhance_scale")

                st.divider()
                enhance_clicked = st.button("✨ Enhance", type="primary", use_container_width=True)
            else:
                st.info("Upload an image to start")
                enhance_clicked = False

    with right_col:
        with st.container(border=True):
            st.markdown("#### 🖼️ Preview & Result")
            if st.session_state.enhance_original is not None:
                if st.session_state.enhance_result is not None:
                    st.image(st.session_state.enhance_result, caption="Enhanced", use_container_width=True)
                    st.download_button(
                        "⬇️ Download Enhanced",
                        st.session_state.enhance_result_bytes,
                        "enhanced.png",
                        type="secondary",
                        use_container_width=True
                    )
                else:
                    st.image(st.session_state.enhance_original, caption="Original", use_container_width=True)
            else:
                st.info("Original and enhanced previews will appear here after you upload an image.")

    if file is not None and enhance_clicked:
        input_img = st.session_state.enhance_original
        scale = st.session_state.enhance_scale

        with st.spinner("Enhancing via GAN Model..."):
            MAX_SIDE = {2: 1536, 4: 1024, 8: 512}
            w, h = input_img.size
            api_img = input_img
            max_side = MAX_SIDE.get(scale, 1024)
            if max(w, h) > max_side:
                ratio = max_side / max(w, h)
                new_w = int(w * ratio)
                new_h = int(h * ratio)
                api_img = input_img.resize((new_w, new_h), Image.LANCZOS)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                api_img.save(tmp.name)
                tmp_path = tmp.name

            enhanced_bytes, err = enhance_image(tmp_path, scale=scale)
            os.remove(tmp_path)

            if err:
                st.error(f"Enhancement failed: {err}")
            else:
                enhanced_img = Image.open(io.BytesIO(enhanced_bytes))
                st.session_state.enhance_result = enhanced_img
                st.session_state.enhance_result_bytes = enhanced_bytes
                st.session_state.history.append(enhanced_bytes)
                st.session_state.enhanced_count += 1
                st.toast("✨ Image enhanced successfully!", icon="🎉")
                st.rerun()

    if st.session_state.enhance_original is not None and st.session_state.enhance_result is not None:
        st.divider()
        st.markdown("#### 🔍 Side-by-Side Comparison")
        image_comparison(
            img1=st.session_state.enhance_original,
            img2=st.session_state.enhance_result,
            label1="Original",
            label2="Enhanced"
        )

# ---------------- HISTORY ---------------- #

elif menu == "🖼️ History":
    st.subheader("🖼️ History")

    col_btn, col_empty = st.columns([1, 3])
    with col_btn:
        if st.button("🗑️ Clear History", type="secondary"):
            st.session_state.history = []
            st.session_state.last_generated = None
            st.session_state.last_generated_original = None
            st.session_state.enhance_result = None
            st.session_state.enhance_original = None
            st.toast("History cleared.", icon="🗑️")
            st.rerun()

    st.divider()

    if not st.session_state.history:
        st.info("No images in history yet. Generate or enhance an image to see it here!")
    else:
        st.markdown(f"**Total images:** {len(st.session_state.history)}")
        items = st.session_state.history
        for row_start in range(0, len(items), 3):
            cols = st.columns(3)
            for j in range(3):
                idx = row_start + j
                with cols[j]:
                    if idx < len(items):
                        with st.container(border=True):
                            st.image(items[idx], use_container_width=True)
                            st.download_button(
                                "⬇️ Download",
                                items[idx],
                                f"img_{idx}.png",
                                key=f"dl_hist_{idx}",
                                use_container_width=True
                            )

# ---------------- CREW ---------------- #

elif menu == "👥 Crew":
    st.subheader("👥 The Crew")

    crew_members = [
        {"name": "Arijeet Das", "role": "Project Lead", "img": "assets/profile/arijeet.jpg"},
        {"name": "Arijit Bera", "role": "AI Integration Engineer", "img": "assets/profile/arijit.jpg"},
        {"name": "Arigna Roy", "role": "Frontend Integration Engineer", "img": "assets/profile/arigna.jpeg"},
        {"name": "Ardhendu Pal", "role": "Deployment & Backend Engineer", "img": "assets/profile/ardhendu.jpeg"},
        {"name": "Aisha Das", "role": "Frontend UI Engineer", "img": "assets/profile/aisha.jpeg"},
    ]

    cols = st.columns(len(crew_members))
    for i, member in enumerate(crew_members):
        with cols[i]:
            b64 = img_to_base64(member["img"])
            st.markdown(f"""
            <div style="text-align:center; padding:18px 12px; border-radius:16px; border:1px solid rgba(255,255,255,0.12); background:rgba(255,255,255,0.06); margin-bottom:12px;">
                <img src="data:image/jpeg;base64,{b64}" style="width:150px; height:150px; object-fit:cover; border-radius:50%; margin-bottom:12px; display:inline-block;">
                <div style="font-weight:bold; color:#fafafa; margin:6px 0; font-size:1.05em;">{member['name']}</div>
                <div style="font-size:0.85em; color:#aaaaaa; margin:0;">{member['role']}</div>
            </div>
            """, unsafe_allow_html=True)

