import streamlit as st
from google import genai
from google.genai import types
import json, io, csv, re, time, base64
import urllib.request
from datetime import datetime

# ── GitHub History Storage ───────────────────────────────────────────────────────
HISTORY_FILE = "history.json"

def load_history_from_github():
    try:
        repo = st.secrets.get("GITHUB_REPO", "")
        token = st.secrets.get("GITHUB_TOKEN", "")
        url = f"https://api.github.com/repos/{repo}/contents/{HISTORY_FILE}"
        req = urllib.request.Request(url, headers={"Authorization": f"token {token}", "User-Agent": "sgrade"})
        with urllib.request.urlopen(req, timeout=6) as r:
            data = json.loads(r.read())
        decoded = base64.b64decode(data["content"].replace("\n","")).decode()
        return json.loads(decoded), data.get("sha","")
    except Exception:
        return [], ""

def save_history_to_github(history, sha=""):
    try:
        repo = st.secrets.get("GITHUB_REPO", "")
        token = st.secrets.get("GITHUB_TOKEN", "")
        url = f"https://api.github.com/repos/{repo}/contents/{HISTORY_FILE}"
        payload = {
            "message": "Update history",
            "content": base64.b64encode(json.dumps(history, ensure_ascii=False, indent=2).encode()).decode(),
        }
        if sha:
            payload["sha"] = sha
        req = urllib.request.Request(url,
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"token {token}", "Content-Type": "application/json", "User-Agent": "sgrade"},
            method="PUT")
        with urllib.request.urlopen(req, timeout=10) as r:
            resp = json.loads(r.read())
            return resp.get("content", {}).get("sha", "")
    except Exception:
        return ""

st.set_page_config(page_title="S-Grade SCOMMERCE", page_icon="📋", layout="wide", initial_sidebar_state="collapsed")

# ── Load databases ──────────────────────────────────────────────────────────────
@st.cache_data
def load_je_database():
    import os
    db_path = os.path.join(os.path.dirname(__file__), "je_data.json")
    if os.path.exists(db_path):
        with open(db_path, encoding="utf-8") as f:
            return json.load(f)
    return []

@st.cache_data
def load_positions():
    import os
    db_path = os.path.join(os.path.dirname(__file__), "sgrade_positions.json")
    if os.path.exists(db_path):
        with open(db_path, encoding="utf-8") as f:
            return json.load(f)
    return []

JE_DATABASE = load_je_database()
POSITIONS = load_positions()

# ── Session state init ──────────────────────────────────────────────────────────
if "history" not in st.session_state:
    _hist, _sha = load_history_from_github()
    st.session_state.history = _hist
    st.session_state.history_sha = _sha
if "selected_history" not in st.session_state:
    st.session_state.selected_history = None

# ── PwC System Prompt ───────────────────────────────────────────────────────────
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
  <level grade="A1-A5">Liên hệ chỉ cho mục đích xã giao.</level>
  <level grade="B1-B5">Trao đổi công việc nội bộ tổ chức.</level>
  <level grade="C1-C5">Cộng tác với bộ phận khác để đạt mục đích chung.</level>
  <level grade="D11-D35">Giám sát/quản lý cấp nhóm, phòng, ban/trung tâm.</level>
  <level grade="E1-E5">Liên hệ phạm vi rộng với phần lớn chức năng, lãnh đạo và điều phối.</level>
  <level grade="F1-F5">Liên hệ cấp quốc tế, điều phối chức năng chiến lược.</level>
</factor>
<factor name="Trách nhiệm giám sát và quản lý">
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
  <level grade="B1-B3">Nguy cơ lãng phí thấp dưới 2 triệu VND.</level>
  <level grade="C1-C3">Nguy cơ tổn thất tài chính nhỏ dưới 50 triệu VND.</level>
  <level grade="D1-D3">Nguy cơ tổn thất tài chính lớn trên 50 triệu VND.</level>
  <level grade="E1-E3">Quyết định tầm doanh nghiệp, ảnh hưởng vị thế thị trường và lợi nhuận.</level>
  <level grade="F1-F3">Quyết định có thể trực tiếp dẫn đến phá sản và ngừng kinh doanh.</level>
  <level grade="NA">Không áp dụng.</level>
</factor>
<factor name="Quyền hạn">
  <level grade="A0-A3">Không có quyền phê duyệt tài chính.</level>
  <level grade="B0-B3">Được duyệt một phần ngân sách.</level>
  <level grade="C0-C3">Được duyệt toàn bộ ngân sách.</level>
  <level grade="D0-D3">Được duyệt ngoài ngân sách tối đa 5%.</level>
  <level grade="E0-E3">Được duyệt ngoài ngân sách trên 5%.</level>
  <level grade="NA">Không áp dụng.</level>
</factor>
<factor name="Môi trường làm việc">
  <level grade="A1-A3">Trong nhà, điều kiện văn phòng.</level>
  <level grade="B1-B3">Trong nhà, điều kiện dễ chịu, đôi khi ảnh hưởng môi trường.</level>
  <level grade="C1-C3">Trong nhà với ảnh hưởng khó chịu: tiếng ồn, nhiệt độ, chất bẩn.</level>
  <level grade="D1-D3">Phần lớn ngoài trời, không phải thời tiết khắc nghiệt.</level>
  <level grade="E1-E3">Hầu hết ngoài trời, liên tục chịu ảnh hưởng khí hậu đa dạng.</level>
  <level grade="NA">Không áp dụng.</level>
</factor>
<factor name="Yêu cầu thể chất">
  <level grade="A1-A4">Thường ở tư thế ngồi.</level>
  <level grade="B1-B4">Phần lớn đứng và/hoặc đi lại.</level>
  <level grade="C1-C4">Có giai đoạn ngắn cúi, uốn, quỳ, trèo.</level>
  <level grade="D1-D4">Thường xuyên phải cúi gập, uốn người, quỳ hoặc trèo.</level>
  <level grade="NA">Không áp dụng.</level>
</factor>

QUAN TRỌNG:
- Chỉ trả về JSON thuần túy, KHÔNG dùng markdown
- Bắt đầu ngay bằng { và kết thúc bằng }
- Mỗi trường "reason" và "evidence" tối đa 80 từ
- Phải trả về đủ 12 yếu tố

{
  "factors": [
    {"name": "Tên yếu tố", "grade": "Mức xếp loại", "reason": "Lý do ngắn gọn", "evidence": "Dẫn chứng từ JD"}
  ],
  "similar_jobs": [
    {"title": "Tên vị trí tương đồng", "similarity": 85, "reason": "Lý do tương đồng"}
  ],
  "summary": "Nhận xét tổng quan về phạm vi, độ phức tạp và mức độ ảnh hưởng"
}"""

COMPARE_PROMPT = """Bạn là chuyên gia đánh giá công việc PwC. Nhiệm vụ: so sánh vị trí mới với danh sách vị trí đã được đánh giá trong lịch sử.

Trả về JSON thuần túy (không markdown):
{
  "comparisons": [
    {
      "title": "Tên vị trí trong lịch sử",
      "similarity_score": 85,
      "matching_factors": ["Yếu tố 1", "Yếu tố 2"],
      "differing_factors": ["Yếu tố 3"],
      "explanation": "Giải thích chi tiết sự tương đồng và khác biệt, tối đa 100 từ"
    }
  ],
  "overall_insight": "Nhận xét tổng quan về vị trí mới so với toàn bộ danh sách đã có, tối đa 80 từ"
}"""

# ── CSS ─────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800;900&family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 0 !important; max-width: 1100px; }
.topnav { background:white; border-bottom:1px solid #e8e8e8; padding:0 2rem; height:56px; display:flex; align-items:center; justify-content:space-between; margin:-1rem -1rem 0 -1rem; position:sticky; top:0; z-index:999; }
.topnav-logo { font-size:15px; font-weight:600; color:#1f2937; display:flex; align-items:center; gap:8px; }
.topnav-logo .sc { color:#F26522; font-weight:800; }
.topnav-logo .sep { color:#9ca3af; }
.hero-banner { background:linear-gradient(135deg,#fff0e8 0%,#f0f4ff 100%); border-radius:20px; padding:2.5rem 3rem; margin:1.5rem 0 1.5rem; }
.hero-sub { font-size:13px; font-weight:600; color:#6b7280; letter-spacing:0.08em; text-transform:uppercase; margin-bottom:0.5rem; }
.hero-title { font-family:'Barlow Condensed',sans-serif; font-size:64px; font-weight:900; color:#F26522; line-height:0.95; text-transform:uppercase; margin-bottom:0.5rem; }
.hero-tagline { font-family:'Barlow Condensed',sans-serif; font-size:20px; font-weight:700; color:#F26522; text-transform:uppercase; letter-spacing:0.04em; }
.summary-box { background:#f0faf5; border:1px solid #b7e8d0; border-radius:10px; padding:1.25rem 1.5rem; margin:1rem 0; }
.summary-box h4 { font-size:14px; font-weight:600; color:#1a7a4a; margin:0 0 0.5rem; }
.summary-box p { font-size:14px; color:#2d6a4f; line-height:1.7; margin:0; }
.similar-item { display:flex; align-items:center; gap:12px; background:#f5f5f5; border-radius:8px; padding:10px 14px; margin-bottom:6px; font-size:13px; }
.sim-pct { background:#fff4ee; color:#d4551a; font-weight:700; font-size:13px; padding:2px 10px; border-radius:6px; flex-shrink:0; }
.history-card { background:white; border:1px solid #e8e8e8; border-radius:10px; padding:1rem 1.25rem; margin-bottom:0.75rem; cursor:pointer; transition:border-color 0.15s; }
.history-card:hover { border-color:#F26522; }
.history-card-title { font-weight:600; font-size:15px; color:#1f2937; margin-bottom:4px; }
.history-card-meta { font-size:12px; color:#9ca3af; }
.grade-chips { display:flex; flex-wrap:wrap; gap:4px; margin-top:8px; }
.chip { font-size:11px; font-weight:600; padding:2px 8px; border-radius:999px; }
.compare-card { background:white; border:1px solid #e8e8e8; border-radius:10px; padding:1.25rem; margin-bottom:0.75rem; }
.compare-pct-bar { height:8px; border-radius:4px; background:#F26522; margin-top:6px; }
.stButton>button { border-radius:999px !important; font-family:'Inter',sans-serif !important; font-weight:600 !important; font-size:14px !important; }
div[data-testid="column"]:first-child .stButton>button { background:#F26522 !important; color:white !important; border:none !important; }
.topnav { position:sticky !important; top:0 !important; z-index:999 !important; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ──────────────────────────────────────────────────────────────────────
def grade_color(g):
    g = str(g).upper()
    if g.startswith("A"): return "#1a7a4a", "#f0faf5"
    if g.startswith("B"): return "#185fa5", "#e6f1fb"
    if g.startswith("C"): return "#854f0b", "#faeeda"
    if g.startswith("D"): return "#993556", "#fbeaf0"
    if g.startswith("E"): return "#993c1d", "#faece7"
    if g.startswith("F"): return "#5b21b6", "#ede9fe"
    if g.startswith("G"): return "#065f46", "#d1fae5"
    return "#444441", "#f1efe8"

def fix_json(raw):
    s = raw.strip().lstrip('\ufeff')
    start = s.find('{')
    if start == -1:
        raise ValueError("No JSON found")
    s = s[start:]
    depth = 0
    in_str = False
    escape = False
    last_valid = 0
    for i, ch in enumerate(s):
        if escape: escape = False; continue
        if ch == '\\': escape = True; continue
        if ch == '"': in_str = not in_str
        if not in_str:
            if ch in '{[': depth += 1
            elif ch in '}]':
                depth -= 1
                if depth == 0: last_valid = i
    if depth == 0:
        return json.loads(s[:last_valid+1])
    fixed = re.sub(r',\s*\{[^}]*$', '', s)
    fixed = re.sub(r',\s*"[^"]*":\s*"[^"]*$', '', fixed)
    if fixed.rstrip().endswith(','):
        fixed = fixed.rstrip().rstrip(',')
    o = fixed.count('{') - fixed.count('}')
    a = fixed.count('[') - fixed.count(']')
    fixed += ']' * max(0,a) + '}' * max(0,o)
    return json.loads(fixed)

def render_result_table(factors, job_title):
    rows = ""
    for i, f in enumerate(factors):
        tc, bg = grade_color(f.get("grade",""))
        rows += f"""<tr style="border-bottom:1px solid #e8e8e8;background:white">
          <td style="padding:11px 14px;font-weight:600;font-size:13px;vertical-align:top;width:16%;color:#1f2937">{i+1}. {f.get("name","")}</td>
          <td style="padding:11px 14px;font-size:13px;vertical-align:top;width:29%;color:#1f2937;line-height:1.6">{f.get("reason","")}</td>
          <td style="padding:11px 14px;font-size:13px;font-style:italic;color:#4b5563;vertical-align:top;width:42%;line-height:1.6">{f.get("evidence","")}</td>
          <td style="padding:11px 14px;text-align:center;vertical-align:top;width:13%">
            <span style="display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:50%;background:{bg};color:{tc};font-weight:700;font-size:13px">{f.get("grade","")}</span>
          </td></tr>"""
    html = f"""<div style="background:white;border-radius:12px;overflow:hidden;border:1px solid #e8e8e8;margin-top:1rem">
      <div style="background:#1f2937;padding:1rem 1.5rem;display:flex;justify-content:space-between;align-items:center">
        <span style="color:white;font-weight:600;font-size:15px">Kết quả đánh giá: {job_title}</span>
      </div>
      <table style="width:100%;border-collapse:collapse;font-family:Arial,sans-serif;background:white">
        <thead><tr style="background:#f3f4f6;border-bottom:2px solid #e5e7eb">
          <th style="padding:10px 14px;text-align:left;font-size:13px;font-weight:600;color:#374151">Yếu tố</th>
          <th style="padding:10px 14px;text-align:left;font-size:13px;font-weight:600;color:#374151">Lý do</th>
          <th style="padding:10px 14px;text-align:left;font-size:13px;font-weight:600;color:#374151">Dẫn chứng</th>
          <th style="padding:10px 14px;text-align:center;font-size:13px;font-weight:600;color:#374151">Mức</th>
        </tr></thead>
        <tbody>{rows}</tbody>
      </table></div>"""
    st.markdown(html, unsafe_allow_html=True)

def call_gemini(api_key, system_prompt, user_content, max_tokens=8192):
    client = genai.Client(api_key=api_key)
    last_err = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=max_tokens,
                    temperature=0.2,
                    response_mime_type="application/json",
                ),
            )
            return response.text
        except Exception as e:
            last_err = e
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                wait = (attempt+1) * 5
                st.toast(f"Server bận, thử lại sau {wait}s... ({attempt+1}/3)")
                time.sleep(wait)
            else:
                raise e
    raise last_err

def get_jd_content(uploaded_file, jd_text_input):
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".txt"):
                return uploaded_file.read().decode("utf-8")
            else:
                try:
                    import docx as _docx
                    doc = _docx.Document(io.BytesIO(uploaded_file.read()))
                    return "\n".join([p.text for p in doc.paragraphs])
                except Exception:
                    return uploaded_file.read().decode("utf-8", errors="ignore")
        except Exception as e:
            st.error(f"Không thể đọc file: {e}")
            return None
    elif jd_text_input.strip():
        return jd_text_input.strip()
    return None

# ── Nav ──────────────────────────────────────────────────────────────────────────
if "main_page" not in st.session_state:
    st.session_state.main_page = "evaluate"

# Nav bar HTML (visual only)
p = st.session_state.main_page
def active(key): return "background:#F26522;color:white;border:none;" if p==key else "background:white;color:#6b7280;border:1px solid #e8e8e8;"

st.markdown(f"""
<div class="topnav">
  <div class="topnav-logo">
    <span class="sc">SCOMMERCE</span><span class="sep">|</span><span>S-Grade SCOMMERCE</span>
  </div>
</div>
""", unsafe_allow_html=True)

# Nav buttons using Streamlit columns (functional)
_, nc1, nc2, nc3, _r = st.columns([3, 1.8, 1.8, 2.2, 0.1])
with nc1:
    if st.button("Đánh giá S-Grade", use_container_width=True, type="primary" if p=="evaluate" else "secondary"):
        st.session_state.main_page = "evaluate"
        st.rerun()
with nc2:
    if st.button("Tra cứu S-Grade", use_container_width=True, type="primary" if p=="lookup" else "secondary"):
        st.session_state.main_page = "lookup"
        st.rerun()
with nc3:
    if st.button("Phúc lợi theo S-Grade", use_container_width=True, type="primary" if p=="benefits" else "secondary"):
        st.session_state.main_page = "benefits"
        st.rerun()

main_page = st.session_state.main_page

# ════════════ PAGE ROUTER ══════════════════════════════════════════════════════

# ── PAGE: ĐÁNH GIÁ S-GRADE ──────────────────────────────────────────────────────
if main_page == "evaluate":

    # ── Hero ─────────────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="hero-banner">
      <div class="hero-sub">Chào mừng bạn đến với</div>
      <div class="hero-title">S-Grade<br>SCOMMERCE</div>
      <div class="hero-tagline">Đánh giá mô tả công việc theo 12 yếu tố PwC</div>
    </div>
    """, unsafe_allow_html=True)
    
    # ── Main Tabs ────────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["⚡  Đánh giá JD", "📂  Lịch sử & So sánh", "🗂  Tra cứu S-Grade"])
    
    # ════════════════════════════════════════════════════════════════════════════════
    # TAB 1: ĐÁNH GIÁ
    # ════════════════════════════════════════════════════════════════════════════════
    with tab1:
        job_title = st.text_input("**Nhập tên vị trí công việc**", placeholder="e.g., Deputy Sorting Centers Manager")
        st.markdown("**Tải lên JD (.docx, .txt)**")
        uploaded_file = st.file_uploader("upload", type=["txt","docx","doc"], label_visibility="collapsed")
        st.markdown("<div style='text-align:center;color:#9ca3af;font-size:13px;margin:0.75rem 0'>— hoặc —</div>", unsafe_allow_html=True)
        jd_text_input = st.text_area("**Nhập nội dung JD trực tiếp**", placeholder="Paste nội dung mô tả công việc vào đây...", height=160)
    
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([2, 1.5, 6])
        with c1:
            eval_btn = st.button("⚡  Đánh giá JD", use_container_width=True)
        with c2:
            clear_btn = st.button("Xóa nội dung", use_container_width=True)
        if clear_btn:
            st.rerun()
    
        if eval_btn:
            if not job_title.strip():
                st.error("⚠️ Vui lòng nhập tên vị trí công việc.")
            else:
                jd_content = get_jd_content(uploaded_file, jd_text_input)
                if not jd_content:
                    st.error("⚠️ Vui lòng tải lên file JD hoặc nhập nội dung JD.")
                else:
                    try:
                        api_key = st.secrets["GEMINI_API_KEY"]
                    except Exception:
                        st.error("❌ Chưa cấu hình GEMINI_API_KEY trong Streamlit Secrets.")
                        st.stop()
    
                    with st.spinner("🤖 AI đang phân tích 12 yếu tố theo phương pháp PwC..."):
                        try:
                            raw = call_gemini(api_key, PWC_SYSTEM_PROMPT, f"Tên vị trí: {job_title}\n\nNội dung JD:\n{jd_content}")
                            result = fix_json(raw)
                            factors = result.get("factors", [])
                            similar = result.get("similar_jobs", [])
                            summary = result.get("summary", "")
    
                            # ── Lưu vào lịch sử ───────────────────────────────────
                            st.session_state.history.append({
                                "title": job_title,
                                "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                                "jd": jd_content[:2000],
                                "result": result,
                            })
                            # Lưu lên GitHub
                            _new_sha = save_history_to_github(
                                st.session_state.history,
                                st.session_state.get("history_sha", "")
                            )
                            if _new_sha:
                                st.session_state.history_sha = _new_sha
    
                            # ── Render bảng kết quả ────────────────────────────────
                            render_result_table(factors, job_title)
    
                            if summary:
                                st.markdown(f"""<div class="summary-box" style="margin-top:1rem">
                                  <h4>Nhận xét tổng quan</h4><p>{summary}</p></div>""", unsafe_allow_html=True)
    
                            if similar:
                                st.markdown("#### Các JD có phạm vi tương đồng")
                                for j in similar:
                                    st.markdown(f"""<div class="similar-item">
                                      <span class="sim-pct">{j.get("similarity",0)}%</span>
                                      <span><strong>{j.get("title","")}</strong> — {j.get("reason","")}</span>
                                    </div>""", unsafe_allow_html=True)
    
                            # ── Export ─────────────────────────────────────────────
                            st.markdown("<br>", unsafe_allow_html=True)
                            e1, e2 = st.columns(2)
                            csv_buf = io.StringIO()
                            writer = csv.writer(csv_buf)
                            writer.writerow(["Vị trí","Yếu tố","Mức","Lý do","Dẫn chứng"])
                            for f in factors:
                                writer.writerow([job_title, f["name"], f["grade"], f["reason"], f["evidence"]])
                            with e1:
                                st.download_button("📥 Xuất CSV", "\ufeff"+csv_buf.getvalue(),
                                    f"sgrade_{job_title.replace(' ','_')}.csv", "text/csv", use_container_width=True)
                            with e2:
                                st.download_button("📄 Xuất JSON", json.dumps(result, ensure_ascii=False, indent=2),
                                    f"sgrade_{job_title.replace(' ','_')}.json", "application/json", use_container_width=True)
    
                            st.success(f"✅ Đã lưu vào lịch sử! Xem tại tab **Lịch sử & So sánh**.")
    
                        except json.JSONDecodeError:
                            st.error("AI trả về định dạng không hợp lệ. Vui lòng thử lại.")
                            with st.expander("Raw output"):
                                st.text(raw)
                        except Exception as e:
                            st.error(f"🔴 Lỗi: {str(e)}")
    
    # ════════════════════════════════════════════════════════════════════════════════
    # TAB 2: LỊCH SỬ & SO SÁNH
    # ════════════════════════════════════════════════════════════════════════════════
    with tab2:
        history = st.session_state.history
    
        if not history:
            st.info("📭 Chưa có vị trí nào được đánh giá. Hãy đánh giá một JD ở tab trước để bắt đầu!")
        else:
            # ── Layout: cột trái = danh sách, cột phải = chi tiết + so sánh ──────
            left_col, right_col = st.columns([1, 2.2], gap="medium")
    
            with left_col:
                st.markdown(f"**{len(history)} vị trí đã đánh giá**")
                st.markdown("<br>", unsafe_allow_html=True)
    
                for i, item in enumerate(reversed(history)):
                    idx = len(history) - 1 - i
                    factors = item["result"].get("factors", [])
                    chips_html = ""
                    for f in factors[:6]:
                        tc, bg = grade_color(f.get("grade",""))
                        chips_html += f'<span class="chip" style="background:{bg};color:{tc}">{f.get("name","")[:8]}: {f.get("grade","")}</span>'
    
                    if st.button(f"📄 {item['title']}", key=f"hist_{idx}", use_container_width=True):
                        st.session_state.selected_history = idx
    
                    st.markdown(f"""<div style="font-size:11px;color:#9ca3af;margin:-8px 0 8px 0">{item['date']}</div>
                    <div class="grade-chips">{chips_html}</div>
                    <div style="margin-bottom:12px"></div>""", unsafe_allow_html=True)
    
            with right_col:
                sel = st.session_state.selected_history
    
                if sel is None:
                    st.markdown("""<div style="background:#f9f9f9;border-radius:12px;padding:3rem;text-align:center;color:#9ca3af;border:1px dashed #e8e8e8">
                      <div style="font-size:32px;margin-bottom:0.5rem">👈</div>
                      <div style="font-size:14px">Chọn một vị trí bên trái để xem chi tiết và so sánh</div>
                    </div>""", unsafe_allow_html=True)
                else:
                    item = history[sel]
                    result = item["result"]
                    factors = result.get("factors", [])
    
                    detail_tab, compare_tab = st.tabs(["📋 Chi tiết 12 yếu tố", "🔍 So sánh tương đồng"])
    
                    # ── Chi tiết ──────────────────────────────────────────────────
                    with detail_tab:
                        render_result_table(factors, item["title"])
                        summary = result.get("summary", "")
                        if summary:
                            st.markdown(f"""<div class="summary-box" style="margin-top:1rem">
                              <h4>Nhận xét tổng quan</h4><p>{summary}</p></div>""", unsafe_allow_html=True)
    
                    # ── So sánh ───────────────────────────────────────────────────
                    with compare_tab:
                        if len(history) < 2:
                            st.info("Cần ít nhất 2 vị trí để so sánh. Hãy đánh giá thêm JD!")
                        else:
                            other_items = [h for i2, h in enumerate(history) if i2 != sel]
    
                            if st.button("🔍 Phân tích so sánh với AI", key="run_compare", use_container_width=False):
                                try:
                                    api_key = st.secrets["GEMINI_API_KEY"]
                                except Exception:
                                    st.error("❌ Chưa cấu hình GEMINI_API_KEY.")
                                    st.stop()
    
                                # Build context
                                current_summary = f"""Vị trí cần so sánh: {item['title']}
    Kết quả đánh giá: {json.dumps([{"name": f["name"], "grade": f["grade"]} for f in factors], ensure_ascii=False)}
    Tóm tắt: {result.get("summary", "")}
    Nội dung JD (tóm tắt): {item['jd'][:800]}"""
    
                                history_summary = "\n\n".join([
                                    f"Vị trí: {h['title']}\nGrades: {json.dumps([{'name': f['name'], 'grade': f['grade']} for f in h['result'].get('factors', [])], ensure_ascii=False)}\nTóm tắt: {h['result'].get('summary', '')}"
                                    for h in other_items
                                ])
    
                                user_content = f"{current_summary}\n\n---DANH SÁCH VỊ TRÍ TRONG LỊCH SỬ---\n{history_summary}"
    
                                with st.spinner("🤖 AI đang phân tích tương đồng..."):
                                    try:
                                        raw = call_gemini(api_key, COMPARE_PROMPT, user_content, max_tokens=4096)
                                        cmp_result = fix_json(raw)
                                        comparisons = cmp_result.get("comparisons", [])
                                        insight = cmp_result.get("overall_insight", "")
    
                                        if insight:
                                            st.markdown(f"""<div class="summary-box">
                                              <h4>Nhận xét tổng quan</h4><p>{insight}</p></div>""", unsafe_allow_html=True)
    
                                        comparisons_sorted = sorted(comparisons, key=lambda x: x.get("similarity_score", 0), reverse=True)
                                        for cmp in comparisons_sorted:
                                            score = cmp.get("similarity_score", 0)
                                            tc, bg = grade_color("E" if score >= 80 else "B" if score >= 60 else "A")
                                            matching = ", ".join(cmp.get("matching_factors", []))
                                            differing = ", ".join(cmp.get("differing_factors", []))
    
                                            st.markdown(f"""
                                            <div class="compare-card">
                                              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
                                                <span style="font-weight:600;font-size:14px;color:#1f2937">{cmp.get("title","")}</span>
                                                <span style="display:inline-flex;align-items:center;justify-content:center;width:42px;height:42px;border-radius:50%;background:{bg};color:{tc};font-weight:700;font-size:14px">{score}%</span>
                                              </div>
                                              <div style="background:#e8e8e8;height:6px;border-radius:3px;margin-bottom:10px">
                                                <div style="background:#F26522;height:6px;border-radius:3px;width:{score}%"></div>
                                              </div>
                                              <p style="font-size:13px;color:#374151;line-height:1.6;margin-bottom:8px">{cmp.get("explanation","")}</p>
                                              {"<div style='font-size:12px;color:#1a7a4a;margin-top:4px'>✅ Tương đồng: " + matching + "</div>" if matching else ""}
                                              {"<div style='font-size:12px;color:#993c1d;margin-top:2px'>⚠️ Khác biệt: " + differing + "</div>" if differing else ""}
                                            </div>""", unsafe_allow_html=True)
    
                                    except Exception as e:
                                        st.error(f"🔴 Lỗi so sánh: {str(e)}")
                            else:
                                # Show static grade comparison table
                                st.markdown(f"**So sánh grade nhanh:** {item['title']} vs các vị trí đã đánh giá")
                                factor_names = [f["name"] for f in factors]
                                cur_grades = {f["name"]: f["grade"] for f in factors}
    
                                rows_html = ""
                                for fname in factor_names:
                                    row = f"<td style='padding:7px 10px;font-size:12px;font-weight:500;color:#1f2937;background:white'>{fname}</td>"
                                    tc, bg = grade_color(cur_grades.get(fname,""))
                                    row += f"<td style='padding:7px 10px;text-align:center;background:white'><span style='display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:{bg};color:{tc};font-weight:700;font-size:11px'>{cur_grades.get(fname,'')}</span></td>"
                                    for h in other_items[:4]:
                                        h_grades = {f2["name"]: f2["grade"] for f2 in h["result"].get("factors",[])}
                                        g = h_grades.get(fname, "—")
                                        tc2, bg2 = grade_color(g) if g != "—" else ("#9ca3af","#f5f5f5")
                                        row += f"<td style='padding:7px 10px;text-align:center;background:white'><span style='display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:{bg2};color:{tc2};font-weight:700;font-size:11px'>{g}</span></td>"
                                    rows_html += f"<tr style='border-bottom:1px solid #f0f0f0'>{row}</tr>"
    
                                headers = "<th style='padding:7px 10px;text-align:left;font-size:12px;font-weight:600;color:#6b7280'>Yếu tố</th>"
                                headers += f"<th style='padding:7px 10px;text-align:center;font-size:12px;font-weight:600;color:#F26522'>{item['title'][:20]}</th>"
                                for h in other_items[:4]:
                                    headers += f"<th style='padding:7px 10px;text-align:center;font-size:12px;font-weight:600;color:#6b7280'>{h['title'][:20]}</th>"
    
                                st.markdown(f"""<div style="overflow-x:auto;background:white;border-radius:10px;border:1px solid #e8e8e8;margin-top:0.5rem">
                                  <table style="width:100%;border-collapse:collapse;background:white">
                                    <thead><tr style="background:#f9f9f9">{headers}</tr></thead>
                                    <tbody>{rows_html}</tbody>
                                  </table></div>""", unsafe_allow_html=True)
    
                                st.markdown("<br>", unsafe_allow_html=True)
                                st.markdown("Bấm **Phân tích so sánh với AI** để nhận phân tích chi tiết và giải thích tương đồng.")
    
    # ════════════════════════════════════════════════════════════════════════════════
    # TAB 3: TRA CỨU S-GRADE
    # ════════════════════════════════════════════════════════════════════════════════
    with tab3:
        if not JE_DATABASE:
            st.info("📭 Chưa có dữ liệu. Liên hệ admin để cập nhật file je_data.json.")
        else:
            # Filter: tên vị trí (dropdown) + S-Grade
            all_sgrades = sorted(set(d["s_grade"] for d in JE_DATABASE if d["s_grade"]))
    
            fc1, fc2 = st.columns([3, 1.5])
            with fc1:
                # 336 records — dùng tên + số thứ tự để phân biệt trùng tên
                all_labels = [
                    f"{d['title']}  |  {d['s_grade']}  |  {d['total_score']} điểm"
                    for d in JE_DATABASE
                ]
                selected_label = st.selectbox("Chọn vị trí", ["-- Chọn vị trí --"] + all_labels)
            with fc2:
                sg_filter = st.selectbox("Lọc S-Grade", ["Tất cả"] + all_sgrades)
    
            # Chỉ hiển thị khi đã chọn
            user_has_filtered = selected_label != "-- Chọn vị trí --" or sg_filter != "Tất cả"
    
            if not user_has_filtered:
                st.markdown("""<div style="background:#f9f9f9;border-radius:12px;padding:2.5rem;text-align:center;
                  color:#9ca3af;border:1px dashed #e8e8e8;margin-top:1rem">
                  <div style="font-size:28px;margin-bottom:0.5rem">🔍</div>
                  <div style="font-size:14px">Chọn vị trí hoặc S-Grade để bắt đầu tra cứu</div>
                </div>""", unsafe_allow_html=True)
            else:
                # Nếu chọn theo S-Grade thì lọc list
                if sg_filter != "Tất cả" and selected_label == "-- Chọn vị trí --":
                    filtered = [d for d in JE_DATABASE if d["s_grade"] == sg_filter]
                    st.markdown(f"<div style='font-size:13px;color:#9ca3af;margin:0.5rem 0 1rem'>Tìm thấy <strong>{len(filtered)}</strong> vị trí S-Grade {sg_filter}</div>", unsafe_allow_html=True)
                    sub_labels = [f"{d['title']}  |  {d['s_grade']}  |  {d['total_score']} điểm" for d in filtered]
                    selected_label = st.selectbox("Chọn vị trí cụ thể", sub_labels, label_visibility="collapsed")
                    sel_item = filtered[sub_labels.index(selected_label)]
                else:
                    idx = all_labels.index(selected_label) if selected_label in all_labels else 0
                    sel_item = JE_DATABASE[idx]
    
                    if sel_item:
                        # Badges: S-Grade + Tổng điểm
                        st.markdown(f"""<div style="display:flex;gap:10px;margin:1rem 0 0.5rem;flex-wrap:wrap">
                          <div style="background:#fff4ee;border-radius:8px;padding:8px 18px;border:1px solid #fcd4b8">
                            <span style="color:#9ca3af;font-size:12px">S-Grade</span><br>
                            <strong style="color:#F26522;font-size:20px">{sel_item['s_grade']}</strong>
                          </div>
                          <div style="background:#f3f4f6;border-radius:8px;padding:8px 18px;border:1px solid #e5e7eb">
                            <span style="color:#9ca3af;font-size:12px">Tổng điểm</span><br>
                            <strong style="color:#1f2937;font-size:20px">{sel_item['total_score']}</strong>
                          </div>
                        </div>""", unsafe_allow_html=True)
    
                        render_result_table(sel_item.get("factors", []), sel_item["title"])
    

# ── PAGE: TRA CỨU S-GRADE ───────────────────────────────────────────────────────
elif main_page == "lookup":
    st.markdown("""
    <div class="hero-banner" style="margin-bottom:1.5rem">
      <div class="hero-sub">Danh sách vị trí</div>
      <div class="hero-title" style="font-size:48px">TRA CỨU<br>S-GRADE</div>
      <div class="hero-tagline">491 vị trí — GHN Express, Logistics, Gido, SCOMMERCE</div>
    </div>
    """, unsafe_allow_html=True)

    if not POSITIONS:
        st.warning("Chưa có dữ liệu. Liên hệ admin để cập nhật file sgrade_positions.json.")
    else:
        # Filter state
        if "filter_open" not in st.session_state:
            st.session_state.filter_open = False
        if "f_search" not in st.session_state:
            st.session_state.f_search = ""
        if "f_rank" not in st.session_state:
            st.session_state.f_rank = "Tất cả"
        if "f_company" not in st.session_state:
            st.session_state.f_company = "Tất cả"
        if "f_block" not in st.session_state:
            st.session_state.f_block = "Tất cả"
        if "f_dept" not in st.session_state:
            st.session_state.f_dept = "Tất cả"

        # Filter bar
        fcol1, fcol2 = st.columns([6, 1])
        with fcol1:
            active_filters = sum([
                st.session_state.f_rank != "Tất cả",
                st.session_state.f_company != "Tất cả",
                st.session_state.f_block != "Tất cả",
                st.session_state.f_dept != "Tất cả",
                bool(st.session_state.f_search),
            ])
            badge = f" ({active_filters})" if active_filters else ""
            st.markdown(f"<div style='font-size:13px;color:#9ca3af;padding-top:8px'>{len(POSITIONS)} vị trí trong hệ thống</div>", unsafe_allow_html=True)
        with fcol2:
            if st.button(f"🔽 Bộ lọc{badge}", use_container_width=True):
                st.session_state.filter_open = not st.session_state.filter_open

        # Filter panel
        if st.session_state.filter_open:
            st.markdown("<div style='background:white;border:1px solid #e8e8e8;border-radius:12px;padding:1.25rem 1.5rem;margin-bottom:1rem'>", unsafe_allow_html=True)
            st.markdown("**Lọc hiển thị**")
            st.session_state.f_search = st.text_input("Tìm mã/tên vị trí", value=st.session_state.f_search, placeholder="Nhập mã/tên vị trí...")

            p1, p2 = st.columns(2)
            ranks_list = ["Tất cả"] + sorted(set(d["rank"] for d in POSITIONS if d["rank"]))
            companies_list = ["Tất cả"] + sorted(set(d["company"] for d in POSITIONS if d["company"]))
            blocks_list = ["Tất cả"] + sorted(set(d["block"] for d in POSITIONS if d["block"]))
            depts_list = ["Tất cả"] + sorted(set(d["department"] for d in POSITIONS if d["department"]))

            with p1:
                st.session_state.f_rank = st.selectbox("Cấp bậc", ranks_list, index=ranks_list.index(st.session_state.f_rank) if st.session_state.f_rank in ranks_list else 0)
                st.session_state.f_block = st.selectbox("Khối", blocks_list, index=blocks_list.index(st.session_state.f_block) if st.session_state.f_block in blocks_list else 0)
            with p2:
                st.session_state.f_company = st.selectbox("Công ty", companies_list, index=companies_list.index(st.session_state.f_company) if st.session_state.f_company in companies_list else 0)
                st.session_state.f_dept = st.selectbox("Phòng ban", depts_list, index=depts_list.index(st.session_state.f_dept) if st.session_state.f_dept in depts_list else 0)

            bc1, bc2 = st.columns([1,1])
            with bc1:
                if st.button("Xóa bộ lọc", use_container_width=True):
                    st.session_state.f_search = ""
                    st.session_state.f_rank = "Tất cả"
                    st.session_state.f_company = "Tất cả"
                    st.session_state.f_block = "Tất cả"
                    st.session_state.f_dept = "Tất cả"
                    st.rerun()
            with bc2:
                if st.button("Áp dụng", use_container_width=True):
                    st.session_state.filter_open = False
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # Apply filters
        filtered = POSITIONS
        if st.session_state.f_search:
            q2 = st.session_state.f_search.lower()
            filtered = [d for d in filtered if q2 in d["positionName"].lower() or q2 in d["vietnameseName"].lower()]
        if st.session_state.f_rank != "Tất cả":
            filtered = [d for d in filtered if d["rank"] == st.session_state.f_rank]
        if st.session_state.f_company != "Tất cả":
            filtered = [d for d in filtered if d["company"] == st.session_state.f_company]
        if st.session_state.f_block != "Tất cả":
            filtered = [d for d in filtered if d["block"] == st.session_state.f_block]
        if st.session_state.f_dept != "Tất cả":
            filtered = [d for d in filtered if d["department"] == st.session_state.f_dept]

        st.markdown(f"<div style='font-size:13px;color:#9ca3af;margin:0.5rem 0 0.75rem'>Hiển thị <strong>{len(filtered)}</strong> / {len(POSITIONS)} vị trí</div>", unsafe_allow_html=True)

        # Table
        if filtered:
            rows_html = ""
            for d in filtered:
                rank = d.get("rank","")
                tc, bg = grade_color(rank)
                ptype = d.get("positionType","")
                type_color = "#185fa5" if ptype == "Indirect" else "#1a7a4a"
                type_bg = "#e6f1fb" if ptype == "Indirect" else "#f0faf5"
                rows_html += f"""<tr style="border-bottom:1px solid #f0f0f0;background:white">
                  <td style="padding:10px 14px;font-weight:500;font-size:13px;color:#1f2937">{d.get("positionName","")}</td>
                  <td style="padding:10px 14px;font-size:13px;color:#6b7280">{d.get("vietnameseName","")}</td>
                  <td style="padding:10px 14px;text-align:center">
                    <span style="display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:50%;background:{bg};color:{tc};font-weight:700;font-size:12px">{rank}</span>
                  </td>
                  <td style="padding:10px 14px;font-size:13px;color:#6b7280">{d.get("block","")}</td>
                  <td style="padding:10px 14px;font-size:13px;color:#6b7280">{d.get("department","")}</td>
                  <td style="padding:10px 14px;text-align:center">
                    <span style="font-size:11px;font-weight:600;padding:3px 8px;border-radius:4px;background:{type_bg};color:{type_color}">{ptype}</span>
                  </td>
                </tr>"""

            st.markdown(f"""<div style="overflow-x:auto;background:white;border-radius:12px;border:1px solid #e8e8e8">
              <table style="width:100%;border-collapse:collapse;background:white">
                <thead><tr style="background:#F26522">
                  <th style="padding:12px 14px;text-align:left;font-size:13px;font-weight:700;color:white">Tên vị trí</th>
                  <th style="padding:12px 14px;text-align:left;font-size:13px;font-weight:700;color:white">Tên tiếng Việt</th>
                  <th style="padding:12px 14px;text-align:center;font-size:13px;font-weight:700;color:white">Cấp bậc</th>
                  <th style="padding:12px 14px;text-align:left;font-size:13px;font-weight:700;color:white">Khối</th>
                  <th style="padding:12px 14px;text-align:left;font-size:13px;font-weight:700;color:white">Phòng ban</th>
                  <th style="padding:12px 14px;text-align:center;font-size:13px;font-weight:700;color:white">Loại vị trí</th>
                </tr></thead>
                <tbody>{rows_html}</tbody>
              </table></div>""", unsafe_allow_html=True)

# ── PAGE: PHÚC LỢI THEO S-GRADE ─────────────────────────────────────────────────
elif main_page == "benefits":
    st.markdown("""
    <div class="hero-banner" style="margin-bottom:1.5rem">
      <div class="hero-sub">Chính sách đãi ngộ</div>
      <div class="hero-title" style="font-size:48px">PHÚC LỢI<br>THEO S-GRADE</div>
      <div class="hero-tagline">Grab for Work · Bảo hiểm sức khỏe · Khám sức khỏe</div>
    </div>
    """, unsafe_allow_html=True)

    ben1, ben2, ben3 = st.tabs(["🚗  Grab for Work", "🏥  Bảo hiểm sức khỏe", "🩺  Khám sức khỏe"])

    PROG_COLORS = {
        "Chương trình 5": ("#5b21b6", "#ede9fe"),
        "Chương trình 4": ("#185fa5", "#e6f1fb"),
        "Chương trình 3": ("#1a7a4a", "#f0faf5"),
        "Chương trình 2": ("#854f0b", "#faeeda"),
        "Chương trình 1": ("#6b7280", "#f3f4f6"),
    }
    def prog_badge(p):
        tc, bg = PROG_COLORS.get(p, ("#6b7280","#f3f4f6"))
        return '<span style="font-size:12px;font-weight:600;padding:4px 12px;border-radius:999px;background:' + bg + ';color:' + tc + '">' + p + '</span>'

    # TAB 1: GRAB FOR WORK
    with ben1:
        st.markdown("<br>", unsafe_allow_html=True)
        grab_data = [
            ("S13","Không giới hạn","Không giới hạn","Không giới hạn"),
            ("S12","Không giới hạn","Không giới hạn","Không giới hạn"),
            ("S11","Không giới hạn","Không giới hạn","Không giới hạn"),
            ("S10","Không giới hạn","Không giới hạn","Không giới hạn"),
            ("S9","5.000.000 đ","3.000.000 đ","3.000.000 đ"),
            ("S8","5.000.000 đ","3.000.000 đ","3.000.000 đ"),
            ("S7","3.000.000 đ","2.000.000 đ","2.000.000 đ"),
            ("S6","1.000.000 đ","1.000.000 đ","1.000.000 đ"),
            ("S5","1.000.000 đ","1.000.000 đ","1.000.000 đ"),
            ("S4","1.000.000 đ","1.000.000 đ","—"),
            ("S3","500.000 đ","500.000 đ","—"),
        ]
        def grab_cell(v):
            if v == "Không giới hạn":
                return '<td style="padding:10px 14px;text-align:center;border-bottom:1px solid #f0f0f0;color:#1a7a4a;font-weight:600;font-size:13px">∞ Không giới hạn</td>'
            elif v == "—":
                return '<td style="padding:10px 14px;text-align:center;border-bottom:1px solid #f0f0f0;color:#9ca3af;font-size:13px">—</td>'
            return '<td style="padding:10px 14px;text-align:center;border-bottom:1px solid #f0f0f0;color:#1f2937;font-weight:500;font-size:13px">' + v + '</td>'

        g_rows = ""
        for rank, kh, spkt, other in grab_data:
            tc, bg = grade_color(rank)
            g_rows += '<tr><td style="padding:10px 14px;text-align:center;border-bottom:1px solid #f0f0f0"><span style="display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:50%;background:' + bg + ';color:' + tc + ';font-weight:700;font-size:12px">' + rank + '</span></td>' + grab_cell(kh) + grab_cell(spkt) + grab_cell(other) + '</tr>'

        st.markdown('<div style="background:white;border-radius:12px;border:1px solid #e8e8e8;overflow:hidden"><div style="background:#1f2937;padding:1rem 1.5rem"><span style="color:white;font-weight:600;font-size:15px">🚗 Chính sách Grab for Work — Hạn mức theo cấp bậc và khối</span></div><div style="padding:0.75rem 1.5rem;font-size:13px;color:#6b7280">Dựa theo từng cấp bậc của từng Khối sẽ được xác định mức chính sách cụ thể</div><table style="width:100%;border-collapse:collapse;background:white"><thead><tr style="background:#f3f4f6"><th style="padding:10px 14px;text-align:center;font-size:13px;font-weight:600;color:#374151;border-bottom:2px solid #e5e7eb">Cấp bậc</th><th style="padding:10px 14px;text-align:center;font-size:13px;font-weight:600;color:#374151;border-bottom:2px solid #e5e7eb">Khối Khách Hàng (trực tiếp)</th><th style="padding:10px 14px;text-align:center;font-size:13px;font-weight:600;color:#374151;border-bottom:2px solid #e5e7eb">Khối Sản Phẩm & Công Nghệ</th><th style="padding:10px 14px;text-align:center;font-size:13px;font-weight:600;color:#374151;border-bottom:2px solid #e5e7eb">Các Khối Còn Lại</th></tr></thead><tbody>' + g_rows + '</tbody></table></div>', unsafe_allow_html=True)

    # TAB 2: BẢO HIỂM SỨC KHỎE
    with ben2:
        st.markdown("<br>", unsafe_allow_html=True)
        ghn_ins = [
            ("S13","Chương trình 5","5"),("S12","Chương trình 5","5"),
            ("S11","Chương trình 5","4"),("S10","Chương trình 4","3"),
            ("S09","Chương trình 4","3"),("S08","Chương trình 4","2"),
            ("S07","Chương trình 4","2"),("S06","Chương trình 3","1"),
            ("S05","Chương trình 3","1"),("S04","Chương trình 2","0"),
            ("S03","Chương trình 2","0"),("S02","Chương trình 1","0"),
            ("S01","Chương trình 1","0"),
        ]
        rows1 = ""
        for rank, prog, rel in ghn_ins:
            tc, bg = grade_color(rank)
            rel_html = '<span style="color:#1a7a4a;font-weight:600">👥 ' + rel + ' người</span>' if rel != "0" else '<span style="color:#9ca3af">—</span>'
            rows1 += '<tr style="border-bottom:1px solid #f0f0f0;background:white"><td style="padding:9px 16px;text-align:center"><span style="display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:50%;background:' + bg + ';color:' + tc + ';font-weight:700;font-size:12px">' + rank + '</span></td><td style="padding:9px 16px;text-align:center">' + prog_badge(prog) + '</td><td style="padding:9px 16px;text-align:center;font-size:13px">' + rel_html + '</td></tr>'

        aha_ins = [
            ("S12","G09","Chương trình 5","3"),("S09","G08","Chương trình 5","3"),
            ("S08","G07","Chương trình 4","3"),("S07","G06","Chương trình 4","2"),
            ("S06","G05","Chương trình 4","1"),("S04","G04","Chương trình 3","0"),
            ("S03","G03","Chương trình 3","0"),("S02","G02","Chương trình 2","0"),
            ("S01","G01","Chương trình 2","0"),
        ]
        rows2 = ""
        for rank, ggrade, prog, rel in aha_ins:
            tc, bg = grade_color(rank)
            rel_html = '<span style="color:#1a7a4a;font-weight:600">👥 ' + rel + ' người</span>' if rel != "0" else '<span style="color:#9ca3af">—</span>'
            rows2 += '<tr style="border-bottom:1px solid #f0f0f0;background:white"><td style="padding:9px 16px;text-align:center"><span style="display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:50%;background:' + bg + ';color:' + tc + ';font-weight:700;font-size:12px">' + rank + '</span></td><td style="padding:9px 16px;text-align:center;font-size:13px;color:#6b7280;font-weight:500">' + ggrade + '</td><td style="padding:9px 16px;text-align:center">' + prog_badge(prog) + '</td><td style="padding:9px 16px;text-align:center;font-size:13px">' + rel_html + '</td></tr>'

        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div style="background:white;border-radius:12px;border:1px solid #e8e8e8;overflow:hidden"><div style="background:#1f2937;padding:0.875rem 1.25rem"><span style="color:white;font-weight:600;font-size:14px">🏢 SCommerce / GHN / Nặng / Logistics</span></div><table style="width:100%;border-collapse:collapse;background:white"><thead><tr style="background:#f3f4f6"><th style="padding:9px 16px;text-align:center;font-size:12px;font-weight:600;color:#374151;border-bottom:1.5px solid #e5e7eb">S-Grade</th><th style="padding:9px 16px;text-align:center;font-size:12px;font-weight:600;color:#374151;border-bottom:1.5px solid #e5e7eb">Chương trình</th><th style="padding:9px 16px;text-align:center;font-size:12px;font-weight:600;color:#374151;border-bottom:1.5px solid #e5e7eb">Người thân CT chi trả</th></tr></thead><tbody>' + rows1 + '</tbody></table></div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div style="background:white;border-radius:12px;border:1px solid #e8e8e8;overflow:hidden"><div style="background:#1f2937;padding:0.875rem 1.25rem"><span style="color:white;font-weight:600;font-size:14px">🛵 Ahamove</span></div><table style="width:100%;border-collapse:collapse;background:white"><thead><tr style="background:#f3f4f6"><th style="padding:9px 16px;text-align:center;font-size:12px;font-weight:600;color:#374151;border-bottom:1.5px solid #e5e7eb">S-Grade</th><th style="padding:9px 16px;text-align:center;font-size:12px;font-weight:600;color:#374151;border-bottom:1.5px solid #e5e7eb">G-Grade</th><th style="padding:9px 16px;text-align:center;font-size:12px;font-weight:600;color:#374151;border-bottom:1.5px solid #e5e7eb">Chương trình</th><th style="padding:9px 16px;text-align:center;font-size:12px;font-weight:600;color:#374151;border-bottom:1.5px solid #e5e7eb">Người thân</th></tr></thead><tbody>' + rows2 + '</tbody></table></div>', unsafe_allow_html=True)

    # TAB 3: KHÁM SỨC KHỎE
    with ben3:
        st.markdown("<br>", unsafe_allow_html=True)
        health_data = [
            ("Chương trình 5", "SMT — 4 người thân đi kèm", "S11 – S13", "G9", "4 người"),
            ("Chương trình 4", "S.Director + 3 người thân<br>Director + 1 người thân<br>Senior Manager / Tech Leaders<br>Senior Lead Engineer 1&amp;2 / Lead Engineer 1&amp;2", "S7 – S10", "G6 – G8", "S10: 3 người<br>S9/G8: 2 người<br>S8/G7: 1 người<br>S7: 0 người"),
            ("Chương trình 3", "Mid manager", "S5 – S6", "G3 – G5", "0"),
            ("Chương trình 2", "Nhóm Văn phòng: Level Executive trở lên<br>Nhóm Kho (KTC+KHL+FFM): NV ký HĐLĐ &amp; CTV ≥3 tháng<br>Giao Hàng Nặng: NV ký HĐLĐ &amp; CTV ≥3 tháng", "S1 – S4", "G1 – G2", "0"),
            ("Chương trình 1", "Tài xế xe tải ký HĐLĐ với GHN, thâm niên >3 tháng tính đến 30/04/2026", "Tài xế xe tải", "—", "0"),
        ]
        rows3 = ""
        for prog, target, ghn, aha, rel in health_data:
            rel_color = "#1a7a4a" if rel != "0" else "#9ca3af"
            rows3 += '<tr style="border-bottom:1px solid #f0f0f0;background:white;vertical-align:top"><td style="padding:12px 14px">' + prog_badge(prog) + '</td><td style="padding:12px 14px;font-size:12px;color:#6b7280;line-height:1.7">' + target + '</td><td style="padding:12px 14px;text-align:center;font-size:13px;font-weight:600;color:#F26522">' + ghn + '</td><td style="padding:12px 14px;text-align:center;font-size:13px;font-weight:600;color:#185fa5">' + aha + '</td><td style="padding:12px 14px;text-align:center;font-size:12px;color:' + rel_color + ';line-height:1.6">' + rel + '</td></tr>'

        st.markdown('<div style="background:white;border-radius:12px;border:1px solid #e8e8e8;overflow:hidden"><div style="background:#1f2937;padding:1rem 1.5rem"><span style="color:white;font-weight:600;font-size:15px">🩺 Chương trình Khám sức khỏe 2026</span></div><table style="width:100%;border-collapse:collapse;background:white"><thead><tr style="background:#f3f4f6"><th style="padding:10px 14px;text-align:left;font-size:13px;font-weight:600;color:#374151;border-bottom:2px solid #e5e7eb">Chương trình</th><th style="padding:10px 14px;text-align:left;font-size:13px;font-weight:600;color:#374151;border-bottom:2px solid #e5e7eb">Đối tượng</th><th style="padding:10px 14px;text-align:center;font-size:13px;font-weight:600;color:#374151;border-bottom:2px solid #e5e7eb">Nhân viên GHN</th><th style="padding:10px 14px;text-align:center;font-size:13px;font-weight:600;color:#374151;border-bottom:2px solid #e5e7eb">Nhân viên Ahamove</th><th style="padding:10px 14px;text-align:center;font-size:13px;font-weight:600;color:#374151;border-bottom:2px solid #e5e7eb">Người thân</th></tr></thead><tbody>' + rows3 + '</tbody></table></div>', unsafe_allow_html=True)
