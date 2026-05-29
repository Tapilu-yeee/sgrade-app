import streamlit as st
from google import genai
from google.genai import types
import json
import io
import csv

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="S-Grade SCOMMERCE",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── PwC System Prompt (ẩn trong code) ─────────────────────────────────────────
PWC_SYSTEM_PROMPT = """<context>
    Bạn là chuyên gia đánh giá công việc chuyên sâu, sử dụng phương pháp PwC đã được chuẩn hóa nội bộ tại GHN.
    Phương pháp bao gồm 12 yếu tố đánh giá giá trị công việc, mỗi yếu tố có các mức phân loại cụ thể (A, B, C, D...) đi kèm mô tả chi tiết.
</context>

<factor name="Trình độ học vấn">
  <level grade="A">Không yêu cầu kiến thức phổ thông và khả năng đọc/viết.</level>
  <level grade="B">Hoàn thành cấp tiểu học, kỹ năng đọc viết và tính toán đơn giản.</level>
  <level grade="C">Hoàn thành cấp THCS, viết văn bản và tính toán nâng cao.</level>
  <level grade="D">Hoàn thành cấp THPT, sử dụng máy tính.</level>
  <level grade="E">Hoàn thành khóa đào tạo nghề từ 3 tháng đến dưới 1 năm.</level>
  <level grade="F1">Tốt nghiệp Trung cấp nghề chuyên ngành bất kỳ.</level>
  <level grade="F2">Tốt nghiệp Trung cấp nghề chuyên ngành cụ thể.</level>
  <level grade="G1">Tốt nghiệp Cao đẳng chuyên ngành bất kỳ.</level>
  <level grade="G2">Tốt nghiệp Cao đẳng chuyên ngành cụ thể.</level>
  <level grade="H1">Tốt nghiệp Đại học chuyên ngành bất kỳ.</level>
  <level grade="H2">Tốt nghiệp Đại học chuyên ngành cụ thể.</level>
  <level grade="I1">Tốt nghiệp đại học và bồi dưỡng nghiệp vụ/văn bằng 2.</level>
  <level grade="I2">Có bằng thạc sĩ chuyên ngành bất kỳ.</level>
  <level grade="I3">Có bằng thạc sĩ chuyên ngành cụ thể.</level>
  <level grade="J">Có bằng Tiến sĩ, kiến thức chuyên sâu.</level>
</factor>

<factor name="Kinh nghiệm">
  <level grade="A">Không đòi hỏi kinh nghiệm, đào tạo trong vài giờ.</level>
  <level grade="B">Công việc đơn giản, có thể học trong 1 tháng.</level>
  <level grade="C">Quen thuộc công việc không phức tạp. (3 tháng)</level>
  <level grade="D">Công việc thường lệ, cần kinh nghiệm xử lý ngoại lệ. (6 tháng)</level>
  <level grade="E">Kinh nghiệm thực hành thành thạo một kỹ năng. (12 tháng)</level>
  <level grade="F">Kinh nghiệm trong lĩnh vực cụ thể, đào tạo chuyên ngành. (1-2 năm)</level>
  <level grade="G1">Tối thiểu 3 năm kinh nghiệm chuyên môn, không có kinh nghiệm giám sát.</level>
  <level grade="G2">Tối thiểu 5 năm chuyên môn HOẶC 1 năm giám sát nhóm.</level>
  <level grade="G3">Tối thiểu 2-3 năm kinh nghiệm giám sát nhóm.</level>
  <level grade="H1">Tối thiểu 6 năm kinh nghiệm chuyên môn.</level>
  <level grade="H2">Tối thiểu 8 năm chuyên môn VÀ/HOẶC 1 năm quản lý cấp phòng.</level>
  <level grade="H3">Tối thiểu 2-3 năm kinh nghiệm quản lý cấp phòng.</level>
  <level grade="I1">Tối thiểu 10 năm kinh nghiệm chuyên môn.</level>
  <level grade="I2">Kinh nghiệm quản lý đồng thời nhiều phòng ban.</level>
  <level grade="I3">Kinh nghiệm ở cấp điều hành mảng chức năng chủ chốt (GĐ Khối/Phó TGĐ).</level>
  <level grade="J">TGĐ tổ chức nhỏ/vừa, một lĩnh vực.</level>
  <level grade="K">TGĐ tổ chức lớn, nhiều lĩnh vực hoặc nhiều quốc gia.</level>
  <level grade="L">TGĐ tổ chức lớn, nhiều lĩnh vực, nhiều quốc gia trên thế giới.</level>
</factor>

<factor name="Mức độ phức tạp của công việc">
  <level grade="A1-A3">Công việc đơn giản, lặp đi lặp lại, không đòi hỏi suy nghĩ độc lập.</level>
  <level grade="B1-B3">Ứng dụng kiến thức và kỹ năng đã có, công việc cụ thể rõ ràng.</level>
  <level grade="C1-C3">Có chính sách và thủ tục chi tiết, thỉnh thoảng cần ý kiến độc lập.</level>
  <level grade="D1-D3">Yêu cầu rõ về kết quả, chưa có cách thức; cần dung hòa yêu cầu đa bên.</level>
  <level grade="E1-E3">Yêu cầu cao về sáng tạo và thích nghi; kiểm soát mạng chức năng liên kết.</level>
  <level grade="F1-F3">Điều phối và quản lý nhiều chức năng chuyên môn hóa cao.</level>
</factor>

<factor name="Phạm vi công việc">
  <level grade="A">Thực hiện nhiệm vụ cụ thể, không cần giám sát hay phối hợp. (Individual Contributor)</level>
  <level grade="B">Không giám sát, nhưng cần phối hợp với các bộ phận khác.</level>
  <level grade="C">Giám sát các cá nhân khác để đạt mục tiêu cụ thể. (Trưởng nhóm)</level>
  <level grade="D">Quản lý một phần hoạt động của một chức năng. (Trưởng phòng)</level>
  <level grade="E">Quản lý toàn bộ một mảng chức năng. (Giám đốc ban/trung tâm)</level>
  <level grade="F">Phối hợp và quản lý nhiều chức năng liên kết. (GĐ Khối/Phó TGĐ)</level>
  <level grade="G">Kiểm soát, định hướng toàn bộ tổ chức trực thuộc tập đoàn. (TGĐ công ty con)</level>
  <level grade="H">TGĐ tổ chức lớn, ảnh hưởng kiểm soát tất cả định hướng chiến lược. (TGĐ công ty mẹ)</level>
</factor>

<factor name="Mức độ giải quyết vấn đề">
  <level grade="A1-A3">Vấn đề nhỏ, giải quyết bằng lựa chọn đơn giản đã học.</level>
  <level grade="B1-B3">Công việc thường lệ, vấn đề phức tạp hơn, cần vận dụng kiến thức tiền lệ.</level>
  <level grade="C1-C3">Vấn đề đa dạng, cần nghiên cứu và sáng tạo trong phân tích.</level>
  <level grade="D1-D3">Vấn đề trong nhóm/phòng có yếu tố bất thường, cần sáng tạo và phán đoán.</level>
  <level grade="E1-E3">Vấn đề phức tạp ở quy mô một chức năng, cần đánh giá nhiều giải pháp.</level>
  <level grade="F1-F3">Vấn đề phức tạp nhiều chức năng, giải pháp có thể thay đổi chính sách hiện hữu.</level>
  <level grade="G1-G3">Vấn đề mới lạ, cần cách tiếp cận hoàn toàn độc lập, tạo chính sách và chiến lược mới.</level>
  <level grade="H1-H3">Vấn đề ảnh hưởng sâu rộng đến toàn tổ chức hoặc xã hội.</level>
</factor>

<factor name="Mức độ cần được chỉ dẫn/giám sát">
  <level grade="A1-A3">Giám sát chặt chẽ, tất cả công việc đều được kiểm tra chi tiết.</level>
  <level grade="B1-B3">Có chỉ dẫn chi tiết, tự sắp xếp thứ tự, công việc được giám sát hầu hết.</level>
  <level grade="C1-C3">Tuân thủ quy định, được hướng dẫn và ra soát định kỳ.</level>
  <level grade="D1-D3">Mục tiêu rõ ràng, được chỉ dẫn chung, không kiểm tra thường xuyên.</level>
  <level grade="E1-E3">Tự lên kế hoạch cho phòng ban, kiểm tra rất ít, làm việc độc lập.</level>
  <level grade="F1-F3">Tham gia thảo luận mục tiêu mảng, tự lên kế hoạch thực hiện.</level>
  <level grade="G1-G3">Đưa ra mục tiêu cho nhóm chức năng, ra quyết định hoàn toàn độc lập.</level>
  <level grade="H1-H3">Trách nhiệm giới hạn bởi chính sách HĐQT, tự đưa ra mục tiêu cho cả tổ chức.</level>
</factor>

<factor name="Mức độ liên lạc khi thực hiện công việc">
  <level grade="A1-A5">Liên hệ chỉ cho mục đích xã giao. (A1: tối thiểu → A5: đàm phán then chốt)</level>
  <level grade="B1-B5">Trao đổi công việc nội bộ tổ chức. (B1: tối thiểu → B5: đàm phán then chốt)</level>
  <level grade="C1-C5">Cộng tác với bộ phận khác để đạt mục đích chung. (C1: tối thiểu → C5: đàm phán then chốt)</level>
  <level grade="D11-D35">Giám sát/quản lý cấp nhóm, phòng, ban/trung tâm.</level>
  <level grade="E1-E5">Liên hệ phạm vi rộng với phần lớn chức năng, lãnh đạo và điều phối.</level>
  <level grade="F1-F5">Liên hệ cấp quốc tế, điều phối chức năng chiến lược.</level>
</factor>

<factor name="Trách nhiệm giám sát & quản lý">
  <level grade="A">Không quản lý nhân viên.</level>
  <level grade="B1-B3">Giám sát mức thấp, hỗ trợ nhân viên mới hoặc quản lý 1 nhân viên.</level>
  <level grade="C11-C33">Giám sát/quản lý 2-10 nhân sự.</level>
  <level grade="D11-D33">Giám sát/quản lý 11-30 nhân sự.</level>
  <level grade="E11-E33">Giám sát/quản lý 31-100 nhân sự.</level>
  <level grade="F11-F33">Giám sát/quản lý 101-500 nhân sự.</level>
  <level grade="G11-G33">Giám sát/quản lý 501-2000 nhân sự.</level>
  <level grade="H11-H33">Giám sát/quản lý 2000+ nhân sự.</level>
</factor>

<factor name="Ảnh hưởng của các quyết định">
  <level grade="A1">Quyết định không gây thiệt hại hoặc có thể làm lại với nguồn lực không đáng kể.</level>
  <level grade="B1-B3">Nguy cơ lãng phí thấp dưới 2 triệu VND. (B1: nhóm/phòng → B3: toàn tổ chức)</level>
  <level grade="C1-C3">Nguy cơ tổn thất tài chính nhỏ dưới 50 triệu VND. (C1: nhóm → C3: toàn tổ chức)</level>
  <level grade="D1-D3">Nguy cơ tổn thất tài chính lớn trên 50 triệu VND. (D1: nhóm → D3: toàn tổ chức)</level>
  <level grade="E1-E3">Quyết định tầm doanh nghiệp, ảnh hưởng vị thế thị trường và lợi nhuận.</level>
  <level grade="F1-F3">Quyết định có thể trực tiếp dẫn đến phá sản và ngừng kinh doanh.</level>
  <level grade="NA">Không áp dụng.</level>
</factor>

<factor name="Quyền hạn">
  <level grade="A0-A3">Không có quyền phê duyệt tài chính. (A0: không tuyển → A3: tuyển lãnh đạo)</level>
  <level grade="B0-B3">Được duyệt một phần ngân sách. (B0: không tuyển → B3: tuyển lãnh đạo)</level>
  <level grade="C0-C3">Được duyệt toàn bộ ngân sách. (C0: không tuyển → C3: tuyển lãnh đạo)</level>
  <level grade="D0-D3">Được duyệt ngoài ngân sách ≤5%. (D0: không tuyển → D3: tuyển lãnh đạo)</level>
  <level grade="E0-E3">Được duyệt ngoài ngân sách >5%. (E0: không tuyển → E3: tuyển lãnh đạo)</level>
  <level grade="NA">Không áp dụng.</level>
</factor>

<factor name="Môi trường làm việc">
  <level grade="A1-A3">Trong nhà, điều kiện văn phòng. (1: ít chấn thương → 3: chấn thương nghiêm trọng)</level>
  <level grade="B1-B3">Trong nhà, điều kiện dễ chịu, đôi khi ảnh hưởng môi trường.</level>
  <level grade="C1-C3">Trong nhà với ảnh hưởng khó chịu: tiếng ồn, nhiệt độ, chất bẩn.</level>
  <level grade="D1-D3">Phần lớn ngoài trời, không phải thời tiết khắc nghiệt.</level>
  <level grade="E1-E3">Hầu hết ngoài trời, liên tục chịu ảnh hưởng khí hậu đa dạng.</level>
  <level grade="NA">Không áp dụng.</level>
</factor>

<factor name="Yêu cầu thể chất">
  <level grade="A1-A4">Thường ở tư thế ngồi. (1: không nâng → 4: thường xuyên nâng nặng)</level>
  <level grade="B1-B4">Phần lớn đứng và/hoặc đi lại. (1: không nâng → 4: thường xuyên nâng nặng)</level>
  <level grade="C1-C4">Có giai đoạn ngắn cúi, uốn, quỳ, trèo. (1: không nâng → 4: nâng nặng)</level>
  <level grade="D1-D4">Thường xuyên phải cúi gập, uốn người, quỳ hoặc trèo.</level>
  <level grade="NA">Không áp dụng.</level>
</factor>

<steps>
  <step>Phân tích đầy đủ 12 yếu tố theo JD người dùng cung cấp</step>
  <step>Xác định mức xếp loại phù hợp cho từng yếu tố</step>
  <step>Giải thích lý do chọn mức xếp loại đó</step>
  <step>Trích dẫn dẫn chứng cụ thể từ nội dung JD</step>
  <step>Liệt kê các JD có phạm vi tương đồng nếu có thể</step>
</steps>

Trả về JSON với cấu trúc sau, KHÔNG thêm markdown hay text khác:
{
  "factors": [
    {
      "name": "Tên yếu tố",
      "grade": "Mức xếp loại (VD: H2, D3, A1...)",
      "reason": "Lý do chọn mức này",
      "evidence": "Dẫn chứng trích từ JD"
    }
  ],
  "similar_jobs": [
    {
      "title": "Tên vị trí tương đồng",
      "similarity": 85,
      "reason": "Lý do tương đồng"
    }
  ],
  "summary": "Nhận xét tổng quan về phạm vi, độ phức tạp và mức độ ảnh hưởng của công việc"
}"""

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800;900&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Hide Streamlit branding */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 0 !important; max-width: 1000px; }

/* Nav bar */
.topnav {
    background: white;
    border-bottom: 1px solid #e8e8e8;
    padding: 0 2rem;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: -1rem -1rem 0 -1rem;
    position: sticky;
    top: 0;
    z-index: 999;
}
.topnav-logo { font-size: 15px; font-weight: 600; color: #1f2937; display: flex; align-items: center; gap: 8px; }
.topnav-logo .sc { color: #F26522; font-weight: 800; }
.topnav-logo .sep { color: #9ca3af; }
.topnav-links { display: flex; gap: 2rem; }
.topnav-links a { font-size: 14px; font-weight: 500; color: #6b7280; text-decoration: none; border-bottom: 2px solid transparent; padding-bottom: 2px; }
.topnav-links a.active { color: #F26522; border-bottom-color: #F26522; }

/* Hero */
.hero-banner {
    background: linear-gradient(135deg, #fff0e8 0%, #f0f4ff 100%);
    border-radius: 20px;
    padding: 3rem 3.5rem;
    margin: 1.5rem 0 2rem;
    position: relative;
    overflow: hidden;
}
.hero-sub { font-size: 13px; font-weight: 600; color: #6b7280; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 0.5rem; }
.hero-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 72px;
    font-weight: 900;
    color: #F26522;
    line-height: 0.95;
    text-transform: uppercase;
    margin-bottom: 0.75rem;
}
.hero-tagline {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 22px;
    font-weight: 700;
    color: #F26522;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

/* Card */
.card {
    background: white;
    border-radius: 12px;
    border: 1px solid #e8e8e8;
    overflow: hidden;
    margin-bottom: 1.5rem;
}
.card-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 1.25rem 1.5rem;
    border-bottom: 1px solid #e8e8e8;
}
.card-header-icon {
    width: 40px; height: 40px;
    background: #fff4ee;
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
}
.card-header-text h2 { font-size: 16px; font-weight: 600; color: #1f2937; margin: 0; }
.card-header-text p { font-size: 13px; color: #6b7280; margin: 3px 0 0; }

/* Result table */
.result-table-wrap {
    background: white;
    border-radius: 12px;
    border: 1px solid #e8e8e8;
    overflow: hidden;
    margin-top: 1.5rem;
}
.result-table-header {
    background: #1f2937;
    color: white;
    padding: 1.25rem 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.result-table-header h3 { font-size: 15px; font-weight: 600; margin: 0; }
.job-badge {
    background: #F26522;
    color: white;
    font-size: 13px;
    font-weight: 600;
    padding: 4px 14px;
    border-radius: 999px;
}
.summary-box {
    background: #f0faf5;
    border: 1px solid #b7e8d0;
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    margin: 1.5rem 0 1rem;
}
.summary-box h4 { font-size: 14px; font-weight: 600; color: #1a7a4a; margin: 0 0 0.5rem; }
.summary-box p { font-size: 14px; color: #2d6a4f; line-height: 1.7; margin: 0; }

/* Grade badge */
.grade { display: inline-block; background: #fff4ee; color: #d4551a; font-weight: 700; font-size: 13px; padding: 3px 10px; border-radius: 6px; }

/* Similar jobs */
.similar-item {
    display: flex; align-items: center; gap: 12px;
    background: #f5f5f5; border-radius: 8px; padding: 10px 14px;
    margin-bottom: 6px; font-size: 13px;
}
.sim-pct { background: #fff4ee; color: #d4551a; font-weight: 700; font-size: 13px; padding: 2px 10px; border-radius: 6px; flex-shrink: 0; }

/* Streamlit overrides */
.stTextInput > div > div > input {
    border-radius: 10px !important;
    border: 1.5px solid #e8e8e8 !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextInput > div > div > input:focus { border-color: #F26522 !important; box-shadow: none !important; }
.stTextArea > div > div > textarea {
    border-radius: 10px !important;
    border: 1.5px solid #e8e8e8 !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextArea > div > div > textarea:focus { border-color: #F26522 !important; box-shadow: none !important; }
.stFileUploader > div {
    border-radius: 10px !important;
    border: 2px dashed #e8e8e8 !important;
}
div[data-testid="stFileUploadDropzone"]:hover { border-color: #F26522 !important; }
.stButton > button {
    border-radius: 999px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    height: 46px !important;
    padding: 0 28px !important;
    transition: all 0.15s !important;
}
div[data-testid="column"]:first-child .stButton > button {
    background: #F26522 !important;
    color: white !important;
    border: none !important;
}
div[data-testid="column"]:first-child .stButton > button:hover { background: #d4551a !important; }
div[data-testid="column"]:nth-child(2) .stButton > button {
    background: white !important;
    color: #1f2937 !important;
    border: 1.5px solid #e8e8e8 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Navigation ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="topnav">
  <div class="topnav-logo">
    <span class="sc">SCOMMERCE</span><span class="sep">|</span><span>S-Grade SCOMMERCE</span>
  </div>
  <div class="topnav-links">
    <a href="#" class="active">Đánh giá giá trị công việc</a>
    <a href="#">Tra cứu S-Grade</a>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Hero Banner ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-banner">
  <div class="hero-sub">Chào mừng bạn đến với</div>
  <div class="hero-title">S-Grade<br>SCOMMERCE</div>
  <div class="hero-tagline">Đánh giá mô tả công việc theo 12 yếu tố</div>
</div>
""", unsafe_allow_html=True)

# ── Input Card ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="card">
  <div class="card-header">
    <div class="card-header-icon">📋</div>
    <div class="card-header-text">
      <h2>Đánh giá mô tả công việc theo 12 yếu tố PwC</h2>
      <p>Nhập tên vị trí và tải lên file JD để được hệ thống đánh giá tự động.</p>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Form ───────────────────────────────────────────────────────────────────────
job_title = st.text_input(
    "**Nhập tên vị trí công việc**",
    placeholder="e.g., Deputy Sorting Centers Manager",
)

st.markdown("**Tải lên JD (.docx, .txt)**")
uploaded_file = st.file_uploader(
    label="upload",
    type=["txt", "docx", "doc"],
    label_visibility="collapsed",
)

st.markdown("<div style='text-align:center;color:#9ca3af;font-size:13px;margin:0.75rem 0'>— hoặc —</div>", unsafe_allow_html=True)

jd_text_input = st.text_area(
    "**Nhập nội dung JD trực tiếp**",
    placeholder="Paste nội dung mô tả công việc vào đây...",
    height=180,
)

st.markdown("<br>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([2, 1.5, 6])
with col1:
    eval_btn = st.button("⚡  Đánh giá JD", use_container_width=True)
with col2:
    clear_btn = st.button("Xóa nội dung", use_container_width=True)

if clear_btn:
    st.rerun()

# ── Run Evaluation ─────────────────────────────────────────────────────────────
def get_jd_content():
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".txt"):
                return uploaded_file.read().decode("utf-8")
            else:
                # For .docx files, try python-docx
                try:
                    import docx
                    doc = docx.Document(io.BytesIO(uploaded_file.read()))
                    return "\n".join([p.text for p in doc.paragraphs])
                except Exception:
                    return uploaded_file.read().decode("utf-8", errors="ignore")
        except Exception as e:
            st.error(f"Không thể đọc file: {e}")
            return None
    elif jd_text_input.strip():
        return jd_text_input.strip()
    return None

if eval_btn:
    if not job_title.strip():
        st.error("⚠️ Vui lòng nhập tên vị trí công việc.")
    else:
        jd_content = get_jd_content()
        if not jd_content:
            st.error("⚠️ Vui lòng tải lên file JD hoặc nhập nội dung JD.")
        else:
            # Get API key from Streamlit Secrets
            try:
                api_key = st.secrets["GEMINI_API_KEY"]
            except Exception:
                st.error("❌ Chưa cấu hình GEMINI_API_KEY trong Streamlit Secrets. Xem hướng dẫn bên dưới.")
                st.stop()

            with st.spinner("🤖 AI đang phân tích 12 yếu tố theo phương pháp PwC..."):
                try:
                    client = genai.Client(api_key=api_key)
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=f"Tên vị trí: {job_title}\n\nNội dung JD:\n{jd_content}",
                        config=types.GenerateContentConfig(
                            system_instruction=PWC_SYSTEM_PROMPT,
                            max_output_tokens=4000,
                            temperature=0.2,
                        ),
                    )

                    raw = response.text
                    clean = raw.replace("```json", "").replace("```", "").strip()
                    result = json.loads(clean)

                    # ── Render Results ─────────────────────────────────────────
                    st.markdown(f"""
                    <div class="result-table-wrap">
                      <div class="result-table-header">
                        <h3>Kết quả đánh giá PwC — 12 yếu tố</h3>
                        <div class="job-badge">{job_title}</div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if result.get("summary"):
                        st.markdown(f"""
                        <div class="summary-box">
                          <h4>Nhận xét tổng quan</h4>
                          <p>{result['summary']}</p>
                        </div>
                        """, unsafe_allow_html=True)

                    # Table
                    factors = result.get("factors", [])
                    if factors:
                        table_data = {
                            "Yếu tố": [f["name"] for f in factors],
                            "Mức xếp loại": [f["grade"] for f in factors],
                            "Lý do": [f["reason"] for f in factors],
                            "Dẫn chứng từ JD": [f["evidence"] for f in factors],
                        }
                        st.dataframe(
                            table_data,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Yếu tố": st.column_config.TextColumn(width="medium"),
                                "Mức xếp loại": st.column_config.TextColumn(width="small"),
                                "Lý do": st.column_config.TextColumn(width="large"),
                                "Dẫn chứng từ JD": st.column_config.TextColumn(width="large"),
                            }
                        )

                    # Similar jobs
                    similar = result.get("similar_jobs", [])
                    if similar:
                        st.markdown("#### Các JD có phạm vi tương đồng")
                        for j in similar:
                            st.markdown(f"""
                            <div class="similar-item">
                              <span class="sim-pct">{j.get('similarity', 0)}%</span>
                              <span><strong>{j.get('title','')}</strong> — {j.get('reason','')}</span>
                            </div>
                            """, unsafe_allow_html=True)

                    # Export buttons
                    st.markdown("<br>", unsafe_allow_html=True)
                    ecol1, ecol2 = st.columns([1, 1])

                    # CSV export
                    csv_buf = io.StringIO()
                    writer = csv.writer(csv_buf)
                    writer.writerow(["Vị trí", "Yếu tố", "Mức xếp loại", "Lý do", "Dẫn chứng từ JD"])
                    for f in factors:
                        writer.writerow([job_title, f["name"], f["grade"], f["reason"], f["evidence"]])
                    with ecol1:
                        st.download_button(
                            label="📥 Xuất CSV",
                            data="\ufeff" + csv_buf.getvalue(),
                            file_name=f"sgrade_{job_title.replace(' ', '_')}.csv",
                            mime="text/csv",
                            use_container_width=True,
                        )

                    # JSON export
                    with ecol2:
                        st.download_button(
                            label="📄 Xuất JSON",
                            data=json.dumps(result, ensure_ascii=False, indent=2),
                            file_name=f"sgrade_{job_title.replace(' ', '_')}.json",
                            mime="application/json",
                            use_container_width=True,
                        )

                except json.JSONDecodeError:
                    st.error("AI trả về định dạng không hợp lệ. Vui lòng thử lại.")
                    with st.expander("Raw output"):
                        st.text(raw)
                except Exception as e:
                    err_msg = str(e)
                    st.error(f"🔴 Lỗi chi tiết: {err_msg}")
