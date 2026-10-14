import calendar
import datetime as dt
import os
import re
import sqlite3
import streamlit as st

# 페이지 기본 설정 (사이드바 기본 접힘 상태)
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


# ---------- 정갈한 크림 톤 & 스타일링 ----------
st.markdown(
    """
    <style>
    /* 상단 기본 메뉴 및 불필요한 배너 숨기기 */
    [data-testid="stHeader"], footer, #MainMenu {
        display: none !important;
    }
    
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    html, body, [class*="css"], .stApp {
        background-color: #F7F5F0;
        font-family: 'Pretendard', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif !important;
        color: #2C2A29;
        line-height: 1.5;
    }
    
    h1, h2, h3, h4, p, span, div, button, input, textarea, select {
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

    [data-testid="stFileUploader"] section {
        padding: 12px !important;
    }
    [data-testid="stFileUploader"] section div {
        font-size: 12px !important;
    }

    .safe-text-block {
        word-break: break-all;
        overflow-wrap: break-word;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# 세션 상태 초기화
if "intro_passed" not in st.session_state:
    st.session_state.intro_passed = False
if "current_page" not in st.session_state:
    st.session_state.current_page = None

# ==========================================
# 0. 인트로 화면 (빛 스윕 효과 적용된 DASOL 로고)
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
# 사이드바 설정 (카테고리 내부 진입 시에만 활성화)
# ==========================================
if st.session_state.current_page is not None:
    st.sidebar.markdown(
        """
        <div style='padding-bottom: 5px;'>
            <h2 style='font-size: 18px; font-weight: 800; letter-spacing: 0.15em; color:#2C2A29; margin-bottom: 0px;'>DASOL</h2>
            <p style='font-size: 9px; letter-spacing: 0.2em; color:#7A7570; margin: 0;'>FIND A MOMENT</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.sidebar.button("🏠 메인 화면으로 이동", use_container_width=True):
        st.session_state.current_page = None
        st.rerun()

    st.sidebar.markdown(
        "<hr style='margin: 12px 0px; border:0.5px solid #E6E2DD;'>",
        unsafe_allow_html=True,
    )

    menu_options = ["러닝 일기", "미디어 보관함"]
    current_idx = menu_options.index(st.session_state.current_page)
    selected_menu = st.sidebar.radio(
        "카테고리 선택", menu_options, index=current_idx
    )

    if selected_menu != st.session_state.current_page:
        st.session_state.current_page = selected_menu
        st.rerun()


# ==========================================
# 상단 헤더 네비게이션
# ==========================================
def render_header():
    st.markdown(
        """
        <style>
        .top-logo-wrap {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-top: -15px;
            margin-bottom: 20px;
        }
        .top-logo-btn div[data-testid="stButton"] > button {
            background: transparent !important;
            border: none !important;
            color: #2C2A29 !important;
            font-weight: 800 !important;
            font-size: 1.5rem !important;
            letter-spacing: 0.15em !important;
            box-shadow: none !important;
        }
        .top-logo-btn div[data-testid="stButton"] > button:hover {
            color: #7A7570 !important;
            background: transparent !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    col_l, col_c, col_r = st.columns([4, 3, 4])
    with col_c:
        st.markdown("<div class='top-logo-wrap'><div class='top-logo-btn'>", unsafe_allow_html=True)
        if st.button("DASOL", key="header_logo_btn", use_container_width=True):
            st.session_state.current_page = None
            st.rerun()
        st.markdown("</div></div>", unsafe_allow_html=True)


# ==========================================
# 1. 카테고리 선택 화면 (대시보드)
# ==========================================
if st.session_state.current_page is None:
    st.markdown("<div style='height: 4vh;'></div>", unsafe_allow_html=True)

    # 상단 로고 및 카테고리 타이틀 섹션 (중앙 정렬 및 고급스러운 비율 적용)
    st.markdown(
        """
        <div style='text-align: center; margin-bottom: 40px;'>
            <h1 style='font-size: 2.8rem; font-weight: 800; letter-spacing: 0.18em; color: #2C2A29; margin: 0 0 4px 0;'>DASOL</h1>
            <p style='font-size: 0.85rem; font-weight: 500; letter-spacing: 0.35em; color: #8C8680; margin: 0 0 25px 0; text-transform: uppercase;'>FIND A MOMENT</p>
            <div style='display: inline-block; padding: 6px 28px; border-top: 1px solid #D6D0C7; border-bottom: 1px solid #D6D0C7;'>
                <span style='font-size: 0.8rem; font-weight: 600; letter-spacing: 0.4em; color: #7A7570; text-transform: uppercase;'>C A T E G O R Y</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_space1, c1, c2, col_space2 = st.columns([1.5, 3, 3, 1.5])

    with c1:
        # 카드 전체 클릭 유도를 위한 투명 버튼 오버레이 스타일
        st.markdown(
            """
            <style>
            .card-btn-1 div[data-testid="stButton"] > button {
                width: 100% !important;
                height: 160px !important;
                background-color: #FFFFFF !important;
                border: 1px solid #E6E2DD !important;
                border-radius: 12px !important;
                box-shadow: 0 4px 12px rgba(44, 42, 41, 0.03) !important;
                transition: all 0.25s ease !important;
                color: #2C2A29 !important;
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
                justify-content: center !important;
            }
            .card-btn-1 div[data-testid="stButton"] > button:hover {
                border-color: #2C2A29 !important;
                transform: translateY(-3px);
                box-shadow: 0 8px 20px rgba(44, 42, 41, 0.08) !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div class='card-btn-1'>", unsafe_allow_html=True)
        if st.button("러닝 일기\n\n러닝 거리와 페이스 기록", key="btn_run_card", use_container_width=True):
            st.session_state.current_page = "러닝 일기"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown(
            """
            <style>
            .card-btn-2 div[data-testid="stButton"] > button {
                width: 100% !important;
                height: 160px !important;
                background-color: #FFFFFF !important;
                border: 1px solid #E6E2DD !important;
                border-radius: 12px !important;
                box-shadow: 0 4px 12px rgba(44, 42, 41, 0.03) !important;
                transition: all 0.25s ease !important;
                color: #2C2A29 !important;
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
                justify-content: center !important;
            }
            .card-btn-2 div[data-testid="stButton"] > button:hover {
                border-color: #2C2A29 !important;
                transform: translateY(-3px);
                box-shadow: 0 8px 20px rgba(44, 42, 41, 0.08) !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div class='card-btn-2'>", unsafe_allow_html=True)
        if st.button("미디어 보관함\n\n사진 및 영상 이동보관", key="btn_media_card", use_container_width=True):
            st.session_state.current_page = "미디어 보관함"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()

TODAY = dt.date.today()

# ==========================================
# PAGE 1: 러닝 일기 (코스 관리, 중앙 정렬 테이블)
# ==========================================
if st.session_state.current_page == "러닝 일기":
    render_header()
    st.markdown(
        "<h1 style='font-weight: 800; font-size: 26px;'>러닝 일기</h1>",
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

    t_col1, t_col2, t_col3 = st.columns([2, 2, 1])
    with t_col1:
        filter_course = st.selectbox(
            "코스 필터", ["전체 코스"] + courses_list, label_visibility="collapsed"
        )
    with t_col2:
        with st.expander("코스 관리 (추가/삭제)"):
            new_course_name = st.text_input("새 코스 이름 (예: 보문산 코스 (7km))")
            if st.button("코스 추가"):
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
                    except:
                        st.error("이미 존재하는 코스이거나 형식이 잘못되었습니다.")

            if courses_list:
                del_course = st.selectbox("삭제할 코스 선택", courses_list)
                if st.button("선택 코스 삭제"):
                    conn = get_db()
                    conn.execute(
                        "DELETE FROM courses WHERE name = ?", (del_course,)
                    )
                    conn.commit()
                    conn.close()
                    st.success("코스가 삭제되었습니다.")
                    st.rerun()
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
# PAGE 2: 미디어 보관함 (BEFORE / AFTER 카드 박스 내부에 파일 목록 스크롤 적용)
# ==========================================
elif st.session_state.current_page == "미디어 보관함":
    render_header()
    st.markdown(
        "<h1 style='font-weight: 800; font-size: 26px;'>미디어 보관함</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color: #7A7570; font-size: 14px; margin-bottom: 25px;'>BEFORE와 AFTER 카드 박스 안에서 직접 파일을 업로드하고 관리하세요.</p>",
        unsafe_allow_html=True,
    )

    col_before, col_after = st.columns(2)


    def render_media_box(box_title, sub_folder):
        st.markdown(
            f"""
            <div style='background: #FFFFFF; border: 1px solid #E6E2DD; border-radius: 12px; padding: 20px;'>
                <h3 style='font-weight: 700; font-size: 18px; margin-top: 0; margin-bottom: 15px; border-bottom: 2px solid #2C2A29; padding-bottom: 8px;'>{box_title}</h3>
            """,
            unsafe_allow_html=True,
        )

        uploaded_file = st.file_uploader(
            f"{box_title} 파일 업로드", key=f"upl_{sub_folder}"
        )
        if uploaded_file is not None:
            orig_name = uploaded_file.name
            _, ext = os.path.splitext(orig_name)
            base_default_name = os.path.splitext(orig_name)[0]

            st.caption(f"원본: {orig_name}")
            new_input_name = st.text_input(
                "저장할 파일명 수정",
                value=base_default_name,
                key=f"input_name_{sub_folder}",
            )

            if st.button(
                "박스 안에 저장",
                key=f"btn_save_{sub_folder}",
                use_container_width=True,
            ):
                final_name = (
                    f"{new_input_name.strip()}{ext}"
                    if new_input_name.strip()
                    else orig_name
                )
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
                st.success("저장 완료!")
                st.rerun()

        st.markdown(
            "<hr style='margin: 15px 0px; border:0.5px solid #E6E2DD;'>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='font-weight: 700; font-size: 13px; color: #7A7570; margin-bottom: 8px;'>보관된 파일 목록</p>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<div style='max-height: 240px; overflow-y: auto; padding-right: 4px;'>",
            unsafe_allow_html=True,
        )

        conn = get_db()
        items = conn.execute(
            "SELECT * FROM media_logs WHERE category = ? ORDER BY id DESC",
            (sub_folder,),
        ).fetchall()
        conn.close()

        if items:
            for item in items:
                st.markdown(
                    f"<div class='safe-text-block' style='font-size:12px; font-weight:600; margin-bottom:2px;'>📁 {item['filename']}</div>",
                    unsafe_allow_html=True,
                )
                st.caption(f"등록일: {item['uploaded_at'][:16]}")

                b_col1, b_col2 = st.columns(2)
                with b_col1:
                    if os.path.exists(item["saved_path"]):
                        with open(item["saved_path"], "rb") as file_data:
                            f_ext = (
                                os.path.splitext(item["filename"])[1]
                                .lower()
                                .strip(".")
                            )
                            if f_ext in ["jpg", "jpeg"]:
                                mime_type = "image/jpeg"
                            elif f_ext == "png":
                                mime_type = "image/png"
                            elif f_ext in ["mp4", "mov"]:
                                mime_type = "video/mp4"
                            elif f_ext in ["cr2", "nef", "arw", "dng", "raw"]:
                                mime_type = "image/x-adobe-dng"
                            else:
                                mime_type = "application/octet-stream"

                            st.download_button(
                                label="다운로드",
                                data=file_data,
                                file_name=item["filename"],
                                mime=mime_type,
                                key=f"dl_{item['id']}",
                                use_container_width=True,
                            )
                with b_col2:
                    if st.button(
                        "삭제", key=f"del_{item['id']}", use_container_width=True
                    ):
                        conn = get_db()
                        conn.execute(
                            "DELETE FROM media_logs WHERE id = ?",
                            (item["id"],),
                        )
                        conn.commit()
                        conn.close()
                        if os.path.exists(item["saved_path"]):
                            try:
                                os.remove(item["saved_path"])
                            except:
                                pass
                        st.success("삭제되었습니다.")
                        st.rerun()

                st.markdown(
                    "<hr style='margin: 8px 0px; border:0.5px dashed #E6E2DD;'>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                "<p style='font-size:12px; color:#A8A29E; text-align:center; padding: 15px 0;'>보관된 파일이 없습니다.</p>",
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


    with col_before:
        render_media_box("BEFORE", "before")

    with col_after:
        render_media_box("AFTER", "after")
