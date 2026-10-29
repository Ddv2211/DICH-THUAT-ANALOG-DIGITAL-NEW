# 📚 DualRead AI — Trình Đọc & Dịch Sách PDF Song Song (Streamlit Open-Source)

Ứng dụng web mã nguồn mở xây dựng bằng **Python & Streamlit**, cho phép đọc sách giáo trình, tài liệu kỹ thuật hoặc datasheet bằng tiếng Anh ở nửa màn hình bên trái và tự động nhận diện, biên dịch sang tiếng Việt ở nửa màn hình bên phải.

## ✨ Tính năng nổi bật
- **🖥️ Giao diện Chia đôi màn hình (Split-Screen):** Tùy chỉnh linh hoạt tỷ lệ khung nhìn Trái (Sách PDF gốc) và Phải (Bản dịch Tiếng Việt).
- **🔄 Dịch toàn trang tự động (Auto Page Sync):** Tự động trích xuất văn bản bằng `PyMuPDF` và dịch ngay khi bạn lật trang.
- **✂️ Khoanh vùng dịch (Snipping Tool):** Kéo chuột chọn bất kỳ vùng văn bản, công thức toán học hoặc sơ đồ mạch điện nào trên trang PDF để AI đọc hình ảnh (Vision OCR) và dịch/giải thích chi tiết.
- **🤖 Đa công cụ dịch thuật (Multi-Engine):**
  1. **Google Gemini AI (`google-genai`):** Dịch chuẩn thuật ngữ chuyên ngành, giữ nguyên định dạng Markdown & công thức LaTeX ($...$), hỗ trợ đọc trực tiếp trang PDF scan.
  2. **Google Translate (`deep-translator`):** Dịch miễn phí 100%, tốc độ phản hồi tức thì, không cần API Key.
  3. **OpenAI / DeepSeek / Ollama Local:** Dễ dàng kết nối với bất kỳ mô hình LLM mã nguồn mở nào.
- **📥 Xuất bản dịch:** Tải toàn bộ các trang đã dịch về máy dưới dạng file Markdown (`.md`).

---

## 🚀 Cách chạy trên máy tính cá nhân (Local)

```bash
# 1. Clone repository về máy
git clone https://github.com/<ten-cua-ban>/dualread-ai-streamlit.git
cd dualread-ai-streamlit

# 2. Cài đặt các thư viện cần thiết
pip install -r requirements.txt

# 3. Khởi chạy ứng dụng Streamlit
streamlit run app.py
```

---

## ☁️ Cách triển khai miễn phí lên Streamlit Community Cloud (Từ GitHub)

1. Tạo một Repository mới trên GitHub và đẩy toàn bộ các file trong thư mục này lên (`app.py`, `requirements.txt`, `.streamlit/config.toml`, `README.md`, `LICENSE`).
2. Truy cập [share.streamlit.io](https://share.streamlit.io/) và đăng nhập bằng tài khoản GitHub của bạn.
3. Nhấn **Create app** -> Chọn Repository vừa tạo -> Chọn nhánh `main` -> Điền `app.py` vào ô **Main file path**.
4. *(Tùy chọn)* Nhấn vào **Advanced settings...** -> Mục **Secrets**, dán Gemini API Key của bạn vào để không cần nhập lại mỗi lần mở web:
   ```toml
   GEMINI_API_KEY = "AIzaSy_KEY_CUA_BAN"
   ```
5. Nhấn **Deploy!** và chờ khoảng 1 phút để nhận đường link web công khai của riêng bạn.
