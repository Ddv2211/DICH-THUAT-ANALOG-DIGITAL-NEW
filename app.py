import io
import json
import base64
import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
from deep_translator import GoogleTranslator

# Optional cropper import with graceful fallback
try:
    from streamlit_cropper import st_cropper
    HAS_CROPPER = True
except ImportError:
    HAS_CROPPER = False

# ==============================================================================
# CẤU HÌNH TRANG WEB (PAGE CONFIG)
# ==============================================================================
st.set_page_config(
    page_title="DualRead AI - Đọc & Dịch Sách PDF Song Song",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS cho giao diện Split-Screen chuẩn hiện đại
st.markdown("""
<style>
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 1rem;
        max-width: 98%;
    }
    .trans-card {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 20px;
        line-height: 1.75;
        font-size: 1.02rem;
        color: #F8FAFC;
        max-height: 78vh;
        overflow-y: auto;
        box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    }
    .source-card {
        background-color: #0F172A;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 12px;
        font-family: monospace;
        font-size: 0.88rem;
        color: #94A3B8;
        max-height: 25vh;
        overflow-y: auto;
    }
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        background: #2563EB;
        color: white;
        margin-right: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# KHỞI TẠO SESSION STATE
# ==============================================================================
if "current_page" not in st.session_state:
    st.session_state.current_page = 1
if "translations_cache" not in st.session_state:
    st.session_state.translations_cache = {}
if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None
if "pdf_name" not in st.session_state:
    st.session_state.pdf_name = None
if "total_pages" not in st.session_state:
    st.session_state.total_pages = 0

# ==============================================================================
# CÁC HÀM XỬ LÝ PDF & DỊCH THUẬT
# ==============================================================================
@st.cache_data(show_spinner=False)
def render_pdf_page(pdf_bytes: bytes, page_num: int, zoom: float = 2.0):
    """Render trang PDF thành ảnh PIL chất lượng cao và trích xuất văn bản gốc."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_index = max(0, min(page_num - 1, len(doc) - 1))
    page = doc.load_page(page_index)
    
    # Render ảnh
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    
    # Trích xuất text
    text = page.get_text("text").strip()
    doc.close()
    return img, text


def translate_with_google(text: str) -> str:
    """Dịch nhanh miễn phí bằng Google Translate (chia nhỏ đoạn nếu quá 4500 ký tự)."""
    if not text.strip():
        return "_Không tìm thấy văn bản dạng chữ trên trang này. Hãy chuyển sang chế độ **Gemini AI (Vision OCR)** hoặc **Khoanh vùng dịch** để đọc trang PDF dạng ảnh scan._"
    
    translator = GoogleTranslator(source="en", target="vi")
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    translated_chunks = []
    
    current_chunk = ""
    for p in paragraphs:
        if len(current_chunk) + len(p) < 4200:
            current_chunk += p + "\n\n"
        else:
            translated_chunks.append(translator.translate(current_chunk.strip()))
            current_chunk = p + "\n\n"
    if current_chunk.strip():
        translated_chunks.append(translator.translate(current_chunk.strip()))
        
    return "\n\n".join(translated_chunks)


def translate_with_gemini(
    api_key: str,
    model_name: str,
    text: str = "",
    pil_image: Image.Image = None,
    domain_prompt: str = "",
    use_vision: bool = False
) -> str:
    """Dịch thuật chuẩn chuyên ngành bằng SDK google-genai mới nhất (hỗ trợ cả Text và Multimodal Vision)."""
    if not api_key:
        return "⚠️ **Chưa có Gemini API Key!** Vui lòng nhập API Key ở thanh công cụ bên trái (Sidebar) hoặc cấu hình trong `st.secrets`."
    
    from google import genai
    from google.genai import types
    
    client = genai.Client(api_key=api_key)
    
    system_instruction = (
        "Bạn là chuyên gia dịch thuật sách giáo trình đại học và tài liệu khoa học kỹ thuật từ Tiếng Anh sang Tiếng Việt.\n"
        f"{domain_prompt}\n"
        "Quy tắc bắt buộc:\n"
        "1. Dịch sát nghĩa, mạch lạc, giữ nguyên cấu trúc tiêu đề, danh sách gạch đầu dòng.\n"
        "2. Giữ nguyên các thuật ngữ viết tắt chuyên ngành trong ngoặc đơn (ví dụ: Khuếch đại thuật toán (Op-Amp), Tỷ số nén tín hiệu đồng pha (CMRR)).\n"
        "3. Biểu diễn toàn bộ công thức toán học dưới dạng chuẩn LaTeX ($...$ hoặc $$...$$).\n"
        "4. Nếu đầu vào có hình ảnh sơ đồ mạch điện hoặc bảng thông số, hãy dịch toàn bộ chữ trong hình và giải thích ngắn gọn nguyên lý hoạt động."
    )
    
    contents = []
    if use_vision and pil_image is not None:
        contents.append(pil_image)
        prompt_text = (
            "Hãy nhận diện (OCR) và dịch toàn bộ nội dung tiếng Anh trong hình ảnh trang sách/vùng cắt này sang tiếng Việt. "
            "Nếu có công thức toán hoặc mạch điện, hãy trình bày lại rõ ràng bằng Markdown & LaTeX."
        )
        if text.strip():
            prompt_text += f"\n\nDưới đây là văn bản thô trích xuất kèm theo để đối chiếu:\n{text}"
        contents.append(prompt_text)
    else:
        if not text.strip():
            return "⚠️ Trang này không có lớp văn bản (text layer). Hãy bật tùy chọn **'Dùng Gemini Vision đọc trực tiếp ảnh trang'** ở Sidebar."
        contents.append(f"Hãy dịch toàn bộ nội dung trang sách tiếng Anh sau đây sang tiếng Việt chuẩn học thuật:\n\n{text}")
        
    response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2,
        )
    )
    return response.text


def translate_with_openai_compatible(
    api_key: str,
    base_url: str,
    model_name: str,
    text: str,
    domain_prompt: str = ""
) -> str:
    """Hỗ trợ OpenAI, DeepSeek, Groq hoặc Ollama Local."""
    from openai import OpenAI
    client = OpenAI(api_key=api_key or "ollama", base_url=base_url)
    
    sys_msg = (
        "Bạn là chuyên gia dịch thuật tài liệu học thuật và kỹ thuật từ Tiếng Anh sang Tiếng Việt. "
        "Hãy trình bày đẹp bằng Markdown và công thức LaTeX. " + domain_prompt
    )
    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": f"Dịch đoạn văn bản sau sang tiếng Việt:\n\n{text}"}
        ],
        temperature=0.2
    )
    return resp.choices[0].message.content


# ==============================================================================
# THANH BÊN (SIDEBAR): CÀI ĐẶT & UPLOAD FILE
# ==============================================================================
with st.sidebar:
    st.markdown("## 📚 DualRead AI")
    st.caption("Mã nguồn mở Đọc & Dịch Sách PDF Song Song")
    
    uploaded_file = st.file_uploader("📂 Tải lên sách PDF gốc (Tiếng Anh)", type=["pdf"])
    
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        if st.session_state.pdf_name != uploaded_file.name:
            st.session_state.pdf_bytes = file_bytes
            st.session_state.pdf_name = uploaded_file.name
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            st.session_state.total_pages = len(doc)
            doc.close()
            st.session_state.current_page = 1

    st.divider()
    st.markdown("### ⚙️ Công cụ Dịch thuật")
    
    engine = st.selectbox(
        "Chọn Engine Dịch:",
        [
            "✨ Gemini AI (Chuẩn học thuật + Vision OCR)",
            "⚡ Google Translate (Miễn phí - Tức thì)",
            "🔌 OpenAI / DeepSeek / Ollama (Custom API)"
        ]
    )
    
    # Cấu hình theo từng Engine
    default_gemini_key = ""
    try:
        default_gemini_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        pass

    gemini_key = default_gemini_key
    gemini_model = "gemini-2.5-flash"
    use_vision_ocr = False
    custom_api_key = ""
    custom_base_url = "https://api.deepseek.com/v1"
    custom_model = "deepseek-chat"

    if "Gemini" in engine:
        gemini_key = st.text_input(
            "🔑 Gemini API Key:",
            value=default_gemini_key,
            type="password",
            help="Lấy miễn phí tại https://aistudio.google.com/apikey"
        )
        gemini_model = st.selectbox(
            "Model Gemini:",
            ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"]
        )
        use_vision_ocr = st.toggle(
            "👁️ Dùng Gemini Vision đọc ảnh trực tiếp",
            value=False,
            help="Rất hữu ích khi đọc sách scan, công thức toán phức tạp hoặc sơ đồ mạch điện."
        )
    elif "OpenAI" in engine:
        custom_base_url = st.text_input("Base URL:", value="https://api.openai.com/v1")
        custom_api_key = st.text_input("API Key:", type="password")
        custom_model = st.text_input("Model Name:", value="gpt-4o-mini")

    domain_specialty = st.text_input(
        "🎓 Chuyên ngành dịch thuật:",
        value="Kỹ thuật Điện tử - Viễn thông, Vi mạch & Toán cao cấp",
        help="Giúp AI dịch chuẩn xác các thuật ngữ chuyên môn của bạn."
    )
    
    st.divider()
    st.markdown("### 🖥️ Tùy chỉnh Hiển thị")
    split_ratio = st.slider("Tỷ lệ khung Trái / Phải:", min_value=3, max_value=7, value=5, help="5 = Chia đôi 50/50")
    render_zoom = st.slider("Độ nét trang PDF (DPI):", min_value=1.0, max_value=3.0, value=1.8, step=0.2)
    auto_translate = st.toggle("🔄 Tự động dịch ngay khi lật trang", value=True)
    
    if st.session_state.translations_cache:
        st.divider()
        # Xuất toàn bộ các trang đã dịch ra file Markdown
        md_export = f"# Bản Dịch: {st.session_state.pdf_name or 'Tài liệu'}\n\n"
        for k, v in sorted(st.session_state.translations_cache.items()):
            md_export += f"## {k}\n\n{v}\n\n---\n\n"
        st.download_button(
            label="📥 Tải xuống các trang đã dịch (.md)",
            data=md_export.encode("utf-8"),
            file_name=f"Ban_dich_{st.session_state.pdf_name or 'sach'}.md",
            mime="text/markdown",
            use_container_width=True
        )


# ==============================================================================
# GIAO DIỆN CHÍNH: CHIA ĐÔI MÀN HÌNH (SPLIT-SCREEN)
# ==============================================================================
if st.session_state.pdf_bytes is None:
    # Màn hình chào mừng khi chưa tải file
    st.markdown("## 👈 Hãy tải lên một file sách PDF ở thanh bên trái để bắt đầu!")
    st.info(
        "**DualRead AI** hỗ trợ đọc song ngữ bất kỳ giáo trình tiếng Anh nào (như *Analog Fundamentals - Floyd*, "
        "Datasheet linh kiện, bài báo IEEE) với 2 chế độ: **Dịch toàn trang tự động** và **Kéo chuột khoanh vùng (Snipping Tool)**."
    )
else:
    total_p = st.session_state.total_pages
    
    # Thanh điều hướng trang (Top Navigation Bar)
    nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns([1.2, 1.5, 2.5, 1.2, 3.6])
    
    with nav_col1:
        if st.button("⬅️ Trang trước", use_container_width=True, disabled=(st.session_state.current_page <= 1)):
            st.session_state.current_page -= 1
            st.rerun()
            
    with nav_col2:
        new_page = st.number_input(
            "Trang hiện tại:",
            min_value=1,
            max_value=total_p,
            value=st.session_state.current_page,
            step=1,
            label_visibility="collapsed"
        )
        if new_page != st.session_state.current_page:
            st.session_state.current_page = new_page
            st.rerun()
            
    with nav_col3:
        st.markdown(f"<div style='padding-top:8px; color:#94A3B8;'>/ Tổng <b>{total_p}</b> trang &nbsp;|&nbsp; 📄 <code>{st.session_state.pdf_name}</code></div>", unsafe_allow_html=True)
        
    with nav_col4:
        if st.button("Trang sau ➡️", use_container_width=True, disabled=(st.session_state.current_page >= total_p)):
            st.session_state.current_page += 1
            st.rerun()
            
    with nav_col5:
        mode = st.radio(
            "Chế độ đọc:",
            ["📄 Dịch toàn trang", "✂️ Khoanh vùng dịch (Snipping)"],
            horizontal=True,
            label_visibility="collapsed"
        )

    st.markdown("<hr style='margin: 0.4rem 0 1rem 0; border-color: #334155;'>", unsafe_allow_html=True)

    # Render trang PDF hiện tại
    page_img, page_text = render_pdf_page(
        st.session_state.pdf_bytes,
        st.session_state.current_page,
        zoom=render_zoom
    )

    # Chia cột Trái (Sách gốc) - Phải (Bản dịch Tiếng Việt)
    left_col, right_col = st.columns([split_ratio, 10 - split_ratio], gap="large")

    cropped_region_img = None

    # --------------------------------------------------------------------------
    # CỘT TRÁI: HIỂN THỊ SÁCH GỐC (HOẶC KHUNG KÉO CẮT VÙNG)
    # --------------------------------------------------------------------------
    with left_col:
        st.markdown(f"<span class='badge'>SÁCH GỐC (EN)</span> **Trang {st.session_state.current_page} / {total_p}**", unsafe_allow_html=True)
        
        if "Khoanh vùng" in mode:
            if HAS_CROPPER:
                st.caption("🖱️ Kéo khung viền màu xanh trên trang sách để chọn đoạn văn, công thức hoặc sơ đồ mạch điện cần dịch:")
                cropped_region_img = st_cropper(
                    page_img,
                    realtime_update=True,
                    box_color="#3B82F6",
                    aspect_ratio=None,
                    return_type="image"
                )
            else:
                st.warning("Chưa cài đặt `streamlit-cropper`. Đang hiển thị chế độ cắt theo tọa độ thanh trượt:")
                w, h = page_img.size
                y_range = st.slider("Chọn vùng dọc (% từ trên xuống):", 0, 100, (20, 60))
                x_range = st.slider("Chọn vùng ngang (% từ trái sang):", 0, 100, (5, 95))
                cropped_region_img = page_img.crop((
                    int(w * x_range[0] / 100),
                    int(h * y_range[0] / 100),
                    int(w * x_range[1] / 100),
                    int(h * y_range[1] / 100)
                ))
                st.image(page_img, use_container_width=True)
        else:
            st.image(page_img, use_container_width=True)
            
        with st.expander("🔍 Xem văn bản Tiếng Anh trích xuất thô (Raw Text)"):
            st.text_area(
                "Bạn có thể sửa hoặc copy đoạn văn bản này:",
                value=page_text if page_text else "[Trang này là ảnh scan không có lớp text]",
                height=180
            )

    # --------------------------------------------------------------------------
    # CỘT PHẢI: BẢN DỊCH TIẾNG VIỆT SONG SONG
    # --------------------------------------------------------------------------
    with right_col:
        head_c1, head_c2 = st.columns([6, 4])
        with head_c1:
            st.markdown(f"<span class='badge' style='background:#10B981;'>BẢN DỊCH (VI)</span> **Trang {st.session_state.current_page}**", unsafe_allow_html=True)
        with head_c2:
            manual_trigger = st.button("🚀 Dịch ngay / Dịch lại", type="primary", use_container_width=True)

        cache_key = f"Trang_{st.session_state.current_page}_{engine}_{use_vision_ocr}"

        # Xử lý chế độ KHOANH VÙNG DỊCH (SNIPPING)
        if "Khoanh vùng" in mode and cropped_region_img is not None:
            st.markdown("##### 🖼️ Vùng bạn vừa khoanh chọn:")
            st.image(cropped_region_img, width=360)
            
            if st.button("✨ Dịch & Giải thích vùng cắt này bằng AI", type="primary", use_container_width=True) or manual_trigger:
                with st.spinner("🤖 AI đang đọc hình ảnh vùng cắt và biên dịch sang Tiếng Việt..."):
                    res = translate_with_gemini(
                        api_key=gemini_key,
                        model_name=gemini_model,
                        text="",
                        pil_image=cropped_region_img,
                        domain_prompt=f"Chuyên ngành: {domain_specialty}",
                        use_vision=True
                    )
                    st.session_state.translations_cache[f"Snip_Trang_{st.session_state.current_page}"] = res
            
            snip_res = st.session_state.translations_cache.get(f"Snip_Trang_{st.session_state.current_page}", "")
            if snip_res:
                st.markdown(snip_res)

        # Xử lý chế độ DỊCH TOÀN TRANG
        else:
            should_translate = manual_trigger or (auto_translate and cache_key not in st.session_state.translations_cache)
            
            if should_translate:
                with st.spinner(f"Đang biên dịch Trang {st.session_state.current_page} sang Tiếng Việt..."):
                    try:
                        if "Google Translate" in engine:
                            result = translate_with_google(page_text)
                        elif "Gemini" in engine:
                            result = translate_with_gemini(
                                api_key=gemini_key,
                                model_name=gemini_model,
                                text=page_text,
                                pil_image=page_img,
                                domain_prompt=f"Chuyên ngành: {domain_specialty}",
                                use_vision=use_vision_ocr
                            )
                        else:
                            result = translate_with_openai_compatible(
                                api_key=custom_api_key,
                                base_url=custom_base_url,
                                model_name=custom_model,
                                text=page_text,
                                domain_prompt=f"Chuyên ngành: {domain_specialty}"
                            )
                        st.session_state.translations_cache[cache_key] = result
                    except Exception as e:
                        st.error(f"Lỗi khi dịch thuật: {e}")

            # Hiển thị kết quả dịch
            translated_content = st.session_state.translations_cache.get(cache_key, "")
            if translated_content:
                st.markdown(translated_content)
            else:
                st.info("Nhấn nút **'🚀 Dịch ngay / Dịch lại'** ở góc trên bên phải để biên dịch trang này.")
