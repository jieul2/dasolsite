import datetime as dt
import os
import re
import sqlite3
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="DASOL",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 파일 업로드 및 저장 폴더 설정
UPLOAD_DIR = "uploaded_media"
os.makedirs(os.path.join(UPLOAD_DIR, "before"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "after"), exist_ok=True)

DB_PATH = "dasol_hub.db"


# ---------- 데이터베이스 초기화 ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS running_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            mood TEXT NOT NULL,
            course TEXT NOT NULL,
            time_sec INTEGER NOT NULL,
            pace TEXT NOT NULL,
            memo TEXT
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS media_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            filename TEXT NOT NULL,
            saved_path TEXT NOT NULL,
            uploaded_at TEXT NOT NULL
        )
        """
    )
    c.execute("SELECT COUNT(*) FROM courses")
    if c.fetchone()[0] == 0:
        defaults = [
            ("판암파출소 (6km)",),
            ("폐고속도로 (5km)",),
            ("한강 코스 (5km)",),
        ]
        c.executemany("INSERT INTO courses(name) VALUES (?)", defaults)
    conn.commit()
    conn.close()


init_db()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------- 유틸리티 함수 ----------
def parse_time_str(s):
    s = s.strip()
    if ":" not in s and s.isdigit():
        if len(s) == 6:
            s = f"{s[:2]}:{s[2:4]}:{s[4:]}"
        elif len(s) == 4:
            s = f"00:{s[:2]}:{s[2:]}"
        elif len(s) == 5:
            s = f"0{s[0]}:{s[1:3]}:{s[3:]}"
    parts = s.split(":")
    try:
        if len(parts) == 3:
            h, m, sec = int(parts[0]), int(parts[1]), int(parts[2])
        elif len(parts) == 2:
            h, m, sec = 0, int(parts[0]), int(parts[1])
        else:
            return None, None
    except ValueError:
        return None, None
    if h < 0 or not (0 <= m < 60) or not (0 <= sec < 60):
        return None, None
    total = h * 3600 + m * 60 + sec
    h_out, rem = divmod(total, 3600)
    m_out, s_out = divmod(rem, 60)
    hms = (
        f"{h_out:02d}:{m_out:02d}:{s_out:02d}"
        if h_out
        else f"{m_out:02d}:{s_out:02d}"
    )
    return total, hms


def calc_pace(course_name, sec):
    m = re.search(r"(\d+(?:\.\d+)?)\s*km", course_name, re.IGNORECASE)
    if m:
        km = float(m.group(1))
        if km > 0:
            p = sec / km
            return f"{int(p // 60)}'{int(p % 60):02d}\"/km"
    return "-"


def parse_km(course_name):
    m = re.search(r"(\d+(?:\.\d+)?)\s*km", course_name, re.IGNORECASE)
    return float(m.group(1)) if m else 0.0


def get_mime(filename):
    ext = os.path.splitext(filename)[1].lower().strip(".")
    if ext in ["jpg", "jpeg"]:
        return "image/jpeg"
    if ext == "png":
        return "image/png"
    if ext in ["mp4", "mov"]:
        return "video/mp4"
    if ext in ["cr2", "nef", "arw", "dng", "raw"]:
        return "image/x-adobe-dng"
    return "application/octet-stream"


# ---------- 공통 스타일 및 자바스크립트 강제 정화 적용 ----------
st.markdown(
    """
    <style>
    footer, #MainMenu { display: none !important; }
    [data-testid="stHeader"] { background: transparent !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }

    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

    html, body, [class*="css"], .stApp {
        background-color: #F7F5F0;
        font-family: 'Pretendard', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif !important;
        color: #2C2A29;
        line-height: 1.5;
    }
    h1, h2, h3, h4, p, span, div, button, input, textarea, select, label {
        font-family: 'Pretendard', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif !important;
    }

    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E6E2DD;
        border-radius: 8px;
        padding: 12px 16px;
    }

    .stButton>button {
        background-color: #2C2A29;
        color: #F7F5F0;
        border: none;
        border-radius: 6px;
        font-weight: 500;
        padding: 6px 14px;
        font-size: 14px;
    }
    .stButton>button:hover {
        background-color: #4A4745;
        color: #FFFFFF;
    }

    input, textarea, select {
        background-color: #FFFFFF !important;
        border: 1px solid #D6D0C7 !important;
        border-radius: 6px !important;
    }

    .safe-text-block {
        word-break: break-all;
        overflow-wrap: break-word;
    }

    /* 사이드바: 크림 톤 */
    [data-testid="stSidebar"] {
        background-color: #FBFAF7 !important;
        border-right: 1px solid #E6E2DD;
    }

    /* -------------------------------------------------------------
       왼쪽 상단 사이드바 토글 버튼 (점 3개 아이콘 강제 고정)
    ------------------------------------------------------------- */
    [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        z-index: 999999 !important;
    }
    
    [data-testid="collapsedControl"] button,
    [data-testid="stSidebarCollapseButton"] button {
        position: relative !important;
        width: 36px !important;
        height: 36px !important;
        background-color: #FFFFFF !important;
        border: 1px solid #E6E2DD !important;
        border-radius: 6px !important;
        box-shadow: 0 2px 6px rgba(44, 42, 41, 0.04) !important;
        color: transparent !important;
    }

    [data-testid="collapsedControl"] button *,
    [data-testid="stSidebarCollapseButton"] button * {
        display: none !important;
    }

    /* 사이드바 열기 버튼: 점 3개 '⋮' 아이콘 */
    [data-testid="collapsedControl"] button::after {
        content: "⋮" !important;
        position: absolute !important;
        inset: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 18px !important;
        font-weight: 900 !important;
        color: #2C2A29 !important;
    }

    /* 사이드바 닫기 버튼: '✕' 아이콘 */
    [data-testid="stSidebarCollapseButton"] button::after {
        content: "✕" !important;
        position: absolute !important;
        inset: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 14px !important;
        font-weight: 700 !important;
        color: #2C2A29 !important;
    }

    /* 파일 업로드 버튼 스타일 */
    [data-testid="stFileUploaderDropzone"] button {
        position: relative !important;
        font-size: 0 !important;
        color: transparent !important;
        background: #2C2A29 !important;
        border: none !important;
        min-width: 110px !important;
        min-height: 36px !important;
        border-radius: 6px !important;
    }
    [data-testid="stFileUploaderDropzone"] button * {
        font-size: 0 !important;
        color: transparent !important;
    }
    [data-testid="stFileUploaderDropzone"] button::after {
        content: "파일 선택";
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 13px;
        color: #F7F5F0;
    }
    </style>

    <script>
    // 브라우저 DOM에서 찌꺼기 텍스트 노드를 실시간으로 탐색하여 완전히 제거
    function removeArtifacts() {
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
        let node;
        while(node = walker.nextNode()) {
            if (node.nodeValue && (node.nodeValue.includes('double_arrow') || node.nodeValue.includes('ouble_arrow'))) {
                node.nodeValue = '';
            }
        }
    }
    const observer = new MutationObserver(removeArtifacts);
    observer.observe(document.body, { childList: true, subtree: true });
    setInterval(removeArtifacts, 200);
    </script>
    """,
    unsafe_allow_html=True,
)

# 세션 상태 초기화
if "intro_passed" not in st.session_state:
    st.session_state.intro_passed = False
if "current_page" not in st.session_state:
    st.session_state.current_page = None

# ==========================================
# 0. 인트로 화면
# ==========================================
if not st.session_state.intro_passed:
    st.markdown(
        """
        <style>
        @keyframes shineSweepRightToLeft {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }
        .intro-wrapper {
            position: fixed;
            top: 0; left: 0;
            width: 100vw; height: 100vh;
            display: flex; flex-direction: column;
            align-items: center; justify-content: center;
            background-color: #F7F5F0;
            z-index: 99999;
        }
        .dasol-logo-box {
            display: flex; flex-direction: column;
            align-items: center; text-align: center;
        }
        .dasol-logo-link {
            font-size: 4.5rem !important;
            font-weight: 800 !important;
            letter-spacing: 0.15em !important;
            text-decoration: none !important;
            margin-bottom: 2px !important;
            display: inline-block;
            background: linear-gradient(120deg, #2C2A29 30%, #FFFFFF 45%, #E8DCC4 50%, #FFFFFF 55%, #2C2A29 70%);
            background-size: 250% auto;
            color: transparent;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: shineSweepRightToLeft 6.0s infinite cubic-bezier(0.25, 1, 0.5, 1);
            text-shadow: 2px 3px 12px rgba(44, 42, 41, 0.12);
        }
        .dasol-logo-link:hover {
            transform: scale(1.02);
            transition: transform 0.2s ease;
        }
        .dasol-sub-text {
            font-size: 0.78rem; font-weight: 500;
            letter-spacing: 0.38em; color: #8C8680;
            margin-right: -0.38em; margin-top: -4px;
            opacity: 0.85; text-transform: uppercase;
        }
        </style>

        <div class="intro-wrapper">
            <div class="dasol-logo-box">
                <a href="?enter=true" class="dasol-logo-link">DASOL</a>
                <div class="dasol-sub-text">FIND A MOMENT</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    query_params = st.query_params
    if "enter" in query_params:
        st.session_state.intro_passed = True
        st.query_params.clear()
        st.rerun()

    st.stop()

# ==========================================
# 사이드바: 모든 페이지 공통 (열기/닫기 반복 가능)
# ==========================================
with st.sidebar:
    st.markdown(
        """
        <style>
        .st-key-side_logo button {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            width: 100% !important;
            height: auto !important;
            min-height: 0 !important;
            padding: 6px 0 14px 0 !important;
        }
        .st-key-side_logo button:hover { background: transparent !important; }
        .st-key-side_logo button p:first-child {
            font-size: 1.3rem !important;
            font-weight: 800 !important;
            letter-spacing: 0.15em !important;
            color: #2C2A29 !important;
            margin: 0 !important;
        }
        .st-key-side_logo button p:last-child {
            font-size: 0.6rem !important;
            font-weight: 500 !important;
            letter-spacing: 0.3em !important;
            color: #8C8680 !important;
            margin: 2px 0 0 0 !important;
        }
        .st-key-side_run_wrap button,
        .st-key-side_media_wrap button {
            background: #FFFFFF !important;
            color: #2C2A29 !important;
            border: 1px solid #E6E2DD !important;
            border-radius: 8px !important;
            text-align: left !important;
            justify-content: flex-start !important;
            padding: 10px 12px !important;
            width: 100% !important;
            box-shadow: none !important;
            font-size: 13px !important;
            font-weight: 700 !important;
            letter-spacing: 0.1em !important;
        }
        .st-key-side_run_wrap button:hover,
        .st-key-side_media_wrap button:hover {
            border-color: #2C2A29 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="side_logo"):
        if st.button("DASOL\n\nFIND A MOMENT", key="side_home_btn", use_container_width=True):
            st.session_state.current_page = None
            st.rerun()

    st.markdown(
        "<hr style='margin: 6px 0px 14px 0px; border:0.5px solid #E6E2DD;'>",
        unsafe_allow_html=True,
    )

    side_items = [
        ("러닝 일기", "side_run", "RUNNING DIARY"),
        ("미디어 보관함", "side_media", "MEDIA VAULT"),
    ]
    for label, key, sub in side_items:
        with st.container(key=f"{key}_wrap"):
            if st.button(sub, key=key, use_container_width=True):
                st.session_state.current_page = label
                st.rerun()


# ==========================================
# 1. 카테고리 선택 화면 (메인)
# ==========================================
if st.session_state.current_page is None:
    st.markdown(
        """
        <style>
        .main-logo { text-align: center; margin-top: 6vh; }
        .main-logo .logo-title {
            font-size: 4rem; font-weight: 800; letter-spacing: 0.2em;
            color: #2C2A29; margin: 0; line-height: 1.05;
        }
        .main-logo .logo-sub {
            font-size: 0.9rem; font-weight: 500; letter-spacing: 0.4em;
            color: #8C8680; margin: 10px 0 0 0; text-transform: uppercase;
        }
        .category-head {
            width: 100%; max-width: 900px;
            margin: 7vh auto 22px auto; text-align: center;
        }
        .category-head .category-line {
            width: 100%; height: 0; border-top: 0.5px solid #C9C2B8;
        }
        .category-head .category-title {
            font-size: 1.1rem; font-weight: 700; letter-spacing: 0.7em;
            color: #8B5E3C; margin: 8px 0; padding-left: 0.7em;
            text-transform: uppercase;
        }

        /* 카테고리 카드: 크기 고정 (넓게) */
        .st-key-card_run button,
        .st-key-card_media button {
            width: 400px !important;
            max-width: 100% !important;
            height: 120px !important;
            min-height: 120px !important;
            max-height: 120px !important;
            background-color: #FFFFFF !important;
            color: #2C2A29 !important;
            border: 1px solid #E6E2DD !important;
            border-radius: 10px !important;
            box-shadow: 0 3px 10px rgba(44, 42, 41, 0.03) !important;
            transition: all 0.25s ease !important;
            padding: 12px 16px !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            overflow: hidden !important;
            white-space: nowrap !important;
        }
        .st-key-card_run button:hover,
        .st-key-card_media button:hover {
            border-color: #2C2A29 !important;
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(44, 42, 41, 0.08) !important;
        }
        .st-key-card_run button p:first-child,
        .st-key-card_media button p:first-child {
            font-size: 16px !important;
            font-weight: 700 !important;
            letter-spacing: 0.14em !important;
            color: #2C2A29 !important;
            margin: 0 0 6px 0 !important;
            white-space: nowrap !important;
        }
        .st-key-card_run button p:last-child,
        .st-key-card_media button p:last-child {
            font-size: 12px !important;
            font-weight: 400 !important;
            color: #8C8680 !important;
            margin: 0 !important;
            white-space: nowrap !important;
        }
        </style>

        <div class="main-logo">
            <p class="logo-title">DASOL</p>
            <p class="logo-sub">FIND A MOMENT</p>
        </div>

        <div class="category-head">
            <div class="category-line"></div>
            <p class="category-title">CATEGORY</p>
            <div class="category-line"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, mid, _ = st.columns([1, 3, 1])
    with mid:
        b1, b2 = st.columns(2, gap="medium")
        with b1:
            with st.container(key="card_run"):
                if st.button(
                    "RUNNING DIARY\n\n러닝 거리와 페이스 기록",
                    key="btn_run_card",
                    use_container_width=True,
                ):
                    st.session_state.current_page = "러닝 일기"
                    st.rerun()
        with b2:
            with st.container(key="card_media"):
                if st.button(
                    "MEDIA VAULT\n\n사진 및 영상 이동보관",
                    key="btn_media_card",
                    use_container_width=True,
                ):
                    st.session_state.current_page = "미디어 보관함"
                    st.rerun()

    st.stop()

TODAY = dt.date.today()


# ==========================================
# 코스 관리 팝업 (st.dialog)
# ==========================================
@st.dialog("코스 관리")
def course_manager_dialog(courses_list):
    new_course_name = st.text_input("새 코스 이름 (예: 보문산 코스 (7km))")
    if st.button("코스 추가", use_container_width=True):
        if new_course_name.strip():
            try:
                conn = get_db()
                conn.execute(
                    "INSERT INTO courses(name) VALUES (?)",
                    (new_course_name.strip(),),
                )
                conn.commit()
                conn.close()
                st.success("코스가 추가되었습니다.")
                st.rerun()
            except Exception:
                st.error("이미 존재하는 코스이거나 형식이 잘못되었습니다.")

    if courses_list:
        st.markdown(
            "<hr style='margin: 12px 0px; border:0.5px solid #E6E2DD;'>",
            unsafe_allow_html=True,
        )
        del_course = st.selectbox("삭제할 코스 선택", courses_list)
        if st.button("선택 코스 삭제", use_container_width=True):
            conn = get_db()
            conn.execute("DELETE FROM courses WHERE name = ?", (del_course,))
            conn.commit()
            conn.close()
            st.success("코스가 삭제되었습니다.")
            st.rerun()


# ==========================================
# PAGE 1: 러닝 일기
# ==========================================
if st.session_state.current_page == "러닝 일기":
    st.markdown(
        "<h1 style='font-weight: 800; font-size: 26px; margin-top: 0;'>러닝 일기</h1>",
        unsafe_allow_html=True,
    )
    weekday_str = ["월", "화", "수", "목", "금", "토", "일"][TODAY.weekday()]
    st.markdown(
        f"<p style='color: #7A7570; font-size: 14px; margin-bottom: 20px;'>{TODAY.strftime('%Y.%m.%d')} ({weekday_str})</p>",
        unsafe_allow_html=True,
    )

    conn = get_db()
    courses_row = conn.execute("SELECT * FROM courses").fetchall()
    courses_list = [r["name"] for r in courses_row]
    logs = conn.execute(
        "SELECT * FROM running_logs ORDER BY date DESC"
    ).fetchall()
    conn.close()

    mon = TODAY - dt.timedelta(days=TODAY.weekday())
    sun = mon + dt.timedelta(days=6)
    prefix = TODAY.strftime("%Y-%m")

    week_km = sum(
        parse_km(it["course"])
        for it in logs
        if mon <= dt.date.fromisoformat(it["date"]) <= sun
    )
    month_cnt = sum(1 for it in logs if it["date"].startswith(prefix))
    total_km = sum(parse_km(it["course"]) for it in logs)

    dates = {it["date"] for it in logs}
    cur_d = TODAY if TODAY.isoformat() in dates else TODAY - dt.timedelta(days=1)
    streak = 0
    while cur_d.isoformat() in dates:
        streak += 1
        cur_d -= dt.timedelta(days=1)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("이번 주 거리", f"{week_km:.1f} km")
    with c2:
        st.metric("이번 달 러닝", f"{month_cnt}회")
    with c3:
        st.metric("누적 거리", f"{total_km:.1f} km")
    with c4:
        st.metric("연속 러닝", f"{streak}일째")

    st.markdown("<hr style='border:0.5px solid #E6E2DD;'>", unsafe_allow_html=True)

    st.markdown(
        """
        <style>
        .st-key-course_gear button {
            width: 44px !important;
            min-width: 44px !important;
            height: 44px !important;
            padding: 0 !important;
            font-size: 24px !important;
            background: transparent !important;
            color: #2C2A29 !important;
            border: none !important;
            box-shadow: none !important;
        }
        .st-key-course_gear button:hover {
            background: transparent !important;
            color: #8B5E3C !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    t_col1, t_col2, t_col3, t_col4 = st.columns(
        [3, 0.5, 1.5, 0.01], vertical_alignment="center", gap="small"
    )
    with t_col1:
        filter_course = st.selectbox(
            "코스 필터", ["전체 코스"] + courses_list, label_visibility="collapsed"
        )
    with t_col2:
        with st.container(key="course_gear"):
            if st.button("⚙", key="btn_course_gear", help="코스 관리"):
                course_manager_dialog(courses_list)
    with t_col3:
        if st.button("+ 기록 추가", use_container_width=True):
            st.session_state.show_add_modal = True

    if st.session_state.get("show_add_modal", False):
        with st.form("run_add_form"):
            st.markdown("### 새로운 러닝 기록")
            r_date = st.date_input("날짜", TODAY)
            r_course = (
                st.selectbox("코스 선택", courses_list)
                if courses_list
                else st.text_input("코스 입력")
            )
            r_mood = st.selectbox(
                "기분", ["GREAT", "GOOD", "SO SO", "BAD", "TERRIBLE"]
            )
            r_time = st.text_input("소요 시간 (예: 00:44:39 또는 4439)")
            r_memo = st.text_area("메모")

            col_a, col_b = st.columns(2)
            with col_a:
                submitted = st.form_submit_button(
                    "저장하기", type="primary", use_container_width=True
                )
            with col_b:
                canceled = st.form_submit_button(
                    "취소", use_container_width=True
                )

            if submitted:
                sec, hms = parse_time_str(r_time)
                if sec is None:
                    st.error(
                        "시간 형식이 올바르지 않습니다. (예: 00:44:39 또는 4439)"
                    )
                else:
                    pace = calc_pace(r_course, sec)
                    conn = get_db()
                    conn.execute(
                        """
                        INSERT INTO running_logs(date, mood, course, time_sec, pace, memo)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            r_date.isoformat(),
                            r_mood,
                            r_course,
                            sec,
                            pace,
                            r_memo,
                        ),
                    )
                    conn.commit()
                    conn.close()
                    st.session_state.show_add_modal = False
                    st.success("저장되었습니다.")
                    st.rerun()
            if canceled:
                st.session_state.show_add_modal = False
                st.rerun()

    filtered_logs = [
        it
        for it in logs
        if filter_course == "전체 코스" or it["course"] == filter_course
    ]
    filtered_logs.sort(key=lambda x: x["date"], reverse=True)

    mood_colors = {
        "GREAT": "#1F8A5B",
        "GOOD": "#3E7FC4",
        "SO SO": "#B8860B",
        "BAD": "#D9782D",
        "TERRIBLE": "#C8443F",
    }

    if filtered_logs:
        st.markdown(
            """
            <div style='display:flex; justify-content:space-between; align-items:center; color:#7A7570; font-size:13px; font-weight:700; padding: 10px 0px; border-bottom: 1px solid #E6E2DD;'>
                <div style='width:15%; text-align:center;'>날짜</div>
                <div style='width:25%; text-align:center;'>코스</div>
                <div style='width:10%; text-align:center;'>기분</div>
                <div style='width:15%; text-align:center;'>시간</div>
                <div style='width:15%; text-align:center;'>페이스</div>
                <div style='width:20%; text-align:center;'>메모</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for it in filtered_logs:
            m_col = mood_colors.get(it["mood"], "#2C2A29")
            m_sec, s_sec = divmod(it["time_sec"], 60)
            h_sec, m_sec = divmod(m_sec, 60)
            t_str = (
                f"{h_sec:02d}:{m_sec:02d}:{s_sec:02d}"
                if h_sec
                else f"{m_sec:02d}:{s_sec:02d}"
            )
            memo_text = it["memo"] if it["memo"] else "-"

            st.markdown(
                f"""
                <div style='display:flex; justify-content:space-between; align-items:center; font-size:14px; padding: 12px 0px; border-bottom: 1px solid #EFECE6;'>
                    <div class='safe-text-block' style='width:15%; text-align:center;'>{it['date']}</div>
                    <div class='safe-text-block' style='width:25%; text-align:center;'>{it['course']}</div>
                    <div class='safe-text-block' style='width:10%; text-align:center; color:{m_col}; font-weight:700;'>{it['mood']}</div>
                    <div class='safe-text-block' style='width:15%; text-align:center;'>{t_str}</div>
                    <div class='safe-text-block' style='width:15%; text-align:center;'>{it['pace']}</div>
                    <div class='safe-text-block' style='width:20%; text-align:center; color:#7A7570;'>{memo_text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("등록된 러닝 기록이 없습니다.")


# ==========================================
# PAGE 2: 미디어 보관함
# ==========================================
elif st.session_state.current_page == "미디어 보관함":
    st.markdown(
        """
        <style>
        .media-title {
            font-size: 15px; font-weight: 800; letter-spacing: 0.3em;
            color: #8B5E3C; text-transform: uppercase;
            padding-bottom: 8px; border-bottom: 1px solid #2C2A29;
            margin-bottom: 14px;
        }
        .media-name {
            font-size: 11px; font-weight: 700; color: #2C2A29;
            word-break: break-all; line-height: 1.3;
        }
        .media-meta {
            font-size: 10px; color: #8C8680;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<h1 style='font-weight: 800; font-size: 26px; margin-top: 0;'>미디어 보관함</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color: #7A7570; font-size: 14px; margin-bottom: 25px;'>파일을 고르고 이름을 확인한 뒤 보관하세요. 아래 목록에서 다운로드와 삭제를 할 수 있습니다.</p>",
        unsafe_allow_html=True,
    )

    col_before, col_after = st.columns(2, gap="large")

    def render_media_box(box_title, sub_folder):
        with st.container(border=True):
            st.markdown(f"<div class='media-title'>{box_title}</div>", unsafe_allow_html=True)

            uploaded_file = st.file_uploader(
                f"{box_title} 파일 선택",
                key=f"upl_{sub_folder}",
                label_visibility="collapsed",
            )

            if uploaded_file is not None:
                orig_name = uploaded_file.name
                base_name, ext = os.path.splitext(orig_name)

                new_name = st.text_input(
                    "저장할 파일명",
                    value=base_name,
                    key=f"name_{sub_folder}",
                )
                if st.button(
                    "보관하기",
                    key=f"save_{sub_folder}",
                    type="primary",
                    use_container_width=True,
                ):
                    final_name = (new_name.strip() or base_name) + ext
                    save_path = os.path.join(
                        UPLOAD_DIR,
                        sub_folder,
                        f"{dt.datetime.now().timestamp()}_{final_name}",
                    )
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    conn = get_db()
                    conn.execute(
                        """
                        INSERT INTO media_logs(category, filename, saved_path, uploaded_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            sub_folder,
                            final_name,
                            save_path,
                            dt.datetime.now().isoformat(),
                        ),
                    )
                    conn.commit()
                    conn.close()
                    st.success("보관되었습니다.")
                    st.rerun()

            st.markdown(
                "<hr style='margin: 14px 0px; border:0.5px solid #E6E2DD;'>",
                unsafe_allow_html=True,
            )

            conn = get_db()
            items = conn.execute(
                "SELECT * FROM media_logs WHERE category = ? ORDER BY id DESC",
                (sub_folder,),
            ).fetchall()
            conn.close()

            if not items:
                st.caption("보관된 파일이 없습니다.")
                return

            with st.container(height=520, border=False):
                cols = st.columns(3)
                for i, item in enumerate(items):
                    exists = os.path.exists(item["saved_path"])
                    mime = get_mime(item["filename"])
                    with cols[i % 3]:
                        with st.container(border=True):
                            if exists and mime in ("image/jpeg", "image/png"):
                                st.image(item["saved_path"], width=110)
                            elif exists and mime == "video/mp4":
                                st.markdown("<div style='font-size:24px;'>🎞</div>", unsafe_allow_html=True)
                            else:
                                st.markdown("<div style='font-size:24px;'>📁</div>", unsafe_allow_html=True)

                            st.markdown(
                                f"<div class='media-name'>{item['filename']}</div>",
                                unsafe_allow_html=True,
                            )
                            st.markdown(
                                f"<div class='media-meta'>{item['uploaded_at'][:10]}</div>",
                                unsafe_allow_html=True,
                            )
                            b1, b2 = st.columns(2)
                            with b1:
                                if exists:
                                    with open(item["saved_path"], "rb") as file_data:
                                        st.download_button(
                                            label="받기",
                                            data=file_data,
                                            file_name=item["filename"],
                                            mime=mime,
                                            key=f"dl_{item['id']}",
                                            use_container_width=True,
                                        )
                            with b2:
                                if st.button(
                                    "삭제",
                                    key=f"del_{item['id']}",
                                    use_container_width=True,
                                ):
                                    conn = get_db()
                                    conn.execute(
                                        "DELETE FROM media_logs WHERE id = ?",
                                        (item["id"],),
                                    )
                                    conn.commit()
                                    conn.close()
                                    st.rerun()

    with col_before:
        render_media_box("BEFORE", "before")

    with col_after:
        render_media_box("AFTER", "after")
