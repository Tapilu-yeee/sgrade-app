# S-Grade SCOMMERCE — Job Evaluation Tool

Đánh giá giá trị công việc theo 12 yếu tố PwC, tích hợp AI (Claude).

---

## 🚀 Deploy lên Streamlit Cloud (miễn phí)

### Bước 1 — Đưa code lên GitHub
```bash
git init
git add app.py requirements.txt .gitignore
# ⚠️ KHÔNG git add .streamlit/secrets.toml
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/sgrade-app.git
git push -u origin main
```

### Bước 2 — Tạo app trên Streamlit Cloud
1. Truy cập https://share.streamlit.io
2. Đăng nhập bằng GitHub
3. Click **"New app"**
4. Chọn repo vừa tạo → Branch: `main` → File: `app.py`
5. Click **"Advanced settings"**

### Bước 3 — Nhập API Key (quan trọng)
Trong **Advanced settings > Secrets**, dán vào:
```toml
GEMINI_API_KEY = "AIzaSy-..."
```
6. Click **Deploy**

✅ App sẽ sẵn sàng tại `https://YOUR_APP.streamlit.app`

---

## 💻 Chạy Local

```bash
pip install -r requirements.txt

# Tạo file secret (đã có sẵn template)
# Sửa .streamlit/secrets.toml, điền API key thật vào

streamlit run app.py
```

---

## 🔑 Về API Key & Quota

| Vấn đề | Giải pháp |
|--------|-----------|
| Key lộ ra ngoài | Key nằm trong Streamlit Secrets, **không bao giờ** xuất hiện trong code |
| Hết quota | Kiểm tra Usage tại console.anthropic.com → nâng tier |
| Muốn tiết kiệm token | Đổi model thành `claude-haiku-4-5-20251001` trong `app.py` (~20x rẻ hơn) |

---

## 📁 Cấu trúc project

```
sgrade_app/
├── app.py                  # App chính
├── requirements.txt        # Dependencies
├── .gitignore              # Bảo vệ secrets.toml
├── .streamlit/
│   └── secrets.toml        # API key (KHÔNG commit)
└── README.md
```
