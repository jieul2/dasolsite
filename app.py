import calendar
import datetime as dt
import os
import re
import sqlite3
import streamlit as st

# 페이지 기본 설정 (사이드바 기본 접힘 상태)
st.set_page_config(
    page_title="DASOL · Personal Hub",
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


# ---------- 정갈한 크림 톤 & 고딕 폰트 스타일링 ----------
st.markdown(
    """
    <style>
    /* 상단 Streamlit 기본 메뉴바 숨기기 */
    [data-testid="stHeader"] {
        display: none !important;
    }
    
    /* 전체 배경 크림 톤 및 정갈한 고딕 폰트 통일 */
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    html, body, [class*="css"], .stApp {
        background-color: #F7F5F0;
        font-family: 'Pretendard', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif !important;
        color: #2C2A29;
    }
    
    /* 숫자와 한글 굵기 일정한 고딕 스타일 */
    h1, h2, h3, h4, p, span, div, button, input, textarea, select {
        font-family: 'Pretendard', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif !important;
    }

    /* 카드 스타일 */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E6E2DD;
        border-radius: 8px;
        padding: 12px 16px;
    }

    /* 버튼 스타일 */
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

    /* 입력창 스타일 */
    input, textarea, select {
        background-color: #FFFFFF !important;
        border: 1px solid #D6D0C7 !important;
        border-radius: 6px !important;
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
# 0. 인트로 화면 (화면 전체 클릭 터치 가능)
# ==========================================
if not st.session_state.intro_passed:
    st.markdown(
        """
        <style>
        .full-screen-btn button {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
            opacity: 0 !important;
            z-index: 99999 !important;
            cursor: pointer !important;
        }
        .dasol-center {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 80vh;
            width: 100%;
        }
        .dasol-title {
            font-size: 3.2rem;
            font-weight: 700;
            letter-spacing: 0.3em;
            color: #2C2A29;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="dasol-center">
            <div class="dasol-title">DASOL</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="full-screen-btn">', unsafe_allow_html=True)
    if st.button("ENTER", key="bg_click"):
        st.session_state.intro_passed = True
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.stop()

# ==========================================
# 1. 팝업 형식의 대시보드 메뉴 선택
# ==========================================
if st.session_state.current_page is None:
    st.markdown("<div style='height: 15vh;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<h2 style='text-align: center; font-weight: 700; margin-bottom: 2rem;'>카테고리 선택</h2>",
        unsafe_allow_html=True,
    )

    m_col1, m_col2 = st.columns(2)
    with m_col1:
        st.markdown(
            """
            <div style='background: #FFFFFF; border: 1px solid #E6E2DD; border-radius: 12px; padding: 30px; text-align: center;'>
                <h3 style='margin-bottom: 15px;'>🏃 러닝 일기</h3>
                <p style='color: #7A7570; font-size: 14px;'>오늘의 러닝 거리와 페이스 기록</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        if st.button("러닝 일기 입장", use_container_width=True):
            st.session_state.current_page = "🏃 러닝 일기"
            st.rerun()

    with m_col2:
        st.markdown(
            """
            <div style='background: #FFFFFF; border: 1px solid #E6E2DD; border-radius: 12px; padding: 30px; text-align: center;'>
                <h3 style='margin-bottom: 15px;'>📁 미디어 보관함</h3>
                <p style='color: #7A7570; font-size: 14px;'>보정 전/후 사진 및 영상 원본 관리</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        if st.button("미디어 보관함 입장", use_container_width=True):
            st.session_state.current_page = "📁 미디어 보관함"
            st.rerun()

    st.stop()

# ==========================================
# 메인 허브 화면 (사이드바 카테고리 메뉴)
# ==========================================
st.sidebar.markdown(
    "<h2 style='font-size: 22px; font-weight: 800; letter-spacing: 0.1em; color:#2C2A29;'>DASOL HUB</h2>",
    unsafe_allow_html=True,
)

menu_options = ["🏃 러닝 일기", "📁 미디어 보관함"]
selected_menu = st.sidebar.radio(
    "카테고리 이동",
    menu_options,
    index=menu_options.index(st.session_state.current_page)
    if st.session_state.current_page in menu_options
    else 0,
)

if selected_menu != st.session_state.current_page:
    st.session_state.current_page = selected_menu
    st.rerun()

TODAY = dt.date.today()

# ==========================================
# PAGE 1: 러닝 일기
# ==========================================
if st.session_state.current_page == "🏃 러닝 일기":
    st.markdown(
        "<h1 style='font-weight: 800; font-size: 28px;'>나의 러닝 일기</h1>",
        unsafe_allow_html=True,
    )
    weekday_str = ["월", "화", "수", "목", "금", "토", "일"][TODAY.weekday()]
    st.markdown(
        f"<p style='color: #7A7570; font-size: 14px; margin-bottom: 20px;'>{TODAY.strftime('%Y.%m.%d')} ({weekday_str})</p>",
        unsafe_allow_html=True,
    )

    conn = get_db()
    courses_row = conn.execute("SELECT name FROM courses").fetchall()
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

    f_col1, f_col2 = st.columns([3, 1])
    with f_col1:
        filter_course = st.selectbox(
            "코스 필터", ["전체 코스"] + courses_list, label_visibility="collapsed"
        )
    with f_col2:
        if st.button("+ 기록 추가", use_container_width=True):
            st.session_state.show_add_modal = True

    if st.session_state.get("show_add_modal", False):
        with st.form("run_add_form"):
            st.markdown("### 새로운 러닝 기록")
            r_date = st.date_input("날짜", TODAY)
            r_course = st.selectbox("코스 선택", courses_list)
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
    filtered_logs.sort(key=lambda x: x["date"])

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
            <div style='display:flex; justify-content:space-between; color:#7A7570; font-size:13px; font-weight:700; padding: 8px 0px; border-bottom: 1px solid #E6E2DD;'>
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
            cols = st.columns([1.5, 2.5, 1, 1.5, 1.5, 2])
            cols[0].write(it["date"])
            cols[1].write(it["course"])
            cols[2].markdown(
                f"<span style='color:{m_col}; font-weight:700;'>{it['mood']}</span>",
                unsafe_allow_html=True,
            )
            m_sec, s_sec = divmod(it["time_sec"], 60)
            h_sec, m_sec = divmod(m_sec, 60)
            t_str = (
                f"{h_sec:02d}:{m_sec:02d}:{s_sec:02d}"
                if h_sec
                else f"{m_sec:02d}:{s_sec:02d}"
            )
            cols[3].write(t_str)
            cols[4].write(it["pace"])
            cols[5].write(it["memo"] if it["memo"] else "-")
            st.markdown(
                "<hr style='margin: 4px 0px; border:0.5px solid #EFECE6;'>",
                unsafe_allow_html=True,
            )
    else:
        st.info("등록된 러닝 기록이 없습니다.")

# ==========================================
# PAGE 2: 미디어 보관함 (좌우 2열 배치 & jxl 다운로드 방지)
# ==========================================
elif st.session_state.current_page == "📁 미디어 보관함":
    st.markdown(
        "<h1 style='font-weight: 800; font-size: 28px;'>미디어 보관함</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color: #7A7570; font-size: 14px; margin-bottom: 20px;'>보정 전(BEFORE)과 보정 후(AFTER) 파일을 좌우로 나누어 원본 화질 그대로 관리하세요.</p>",
        unsafe_allow_html=True,
    )

    col_before, col_after = st.columns(2)


    def render_media_section(category_title, sub_folder):
        st.markdown(
            f"<h3 style='font-weight:700;'>{category_title}</h3>",
            unsafe_allow_html=True,
        )

        uploaded_file = st.file_uploader(
            f"{category_title} 파일 업로드", key=f"upl_{sub_folder}"
        )
        if uploaded_file is not None:
            orig_name = uploaded_file.name
            _, ext = os.path.splitext(orig_name)
            base_default_name = os.path.splitext(orig_name)[0]

            st.caption(f"원본 파일명: {orig_name}")
            new_input_name = st.text_input(
                "저장할 새 파일명 입력",
                value=base_default_name,
                key=f"input_name_{sub_folder}",
            )

            if st.button(
                "파일 저장", key=f"btn_save_{sub_folder}", use_container_width=True
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
                st.success(f"'{final_name}' 저장 완료!")
                st.rerun()

        st.markdown("<hr style='border:0.5px solid #E6E2DD;'>", unsafe_allow_html=True)
        st.markdown(
            "<h4 style='font-size:16px; font-weight:700;'>보관된 파일 목록</h4>",
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
                    f"**📁 {item['filename']}**", unsafe_allow_html=True
                )
                st.caption(f"일시: {item['uploaded_at'][:16]}")

                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if os.path.exists(item["saved_path"]):
                        with open(item["saved_path"], "rb") as file_data:
                            # 모바일 브라우저(크롬 등)에서 jxl로 변환되는 현상을 막기 위한 MIME 타입 제어
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
                with btn_col2:
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
                    "<hr style='margin: 8px 0px; border:0.5px solid #EFECE6;'>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("등록된 파일이 없습니다.")


    with col_before:
        render_media_section("📌 BEFORE (보정 전)", "before")

    with col_after:
        render_media_section("✨ AFTER (보정 후)", "after")
