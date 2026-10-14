import calendar
import datetime as dt
import os
import re
import sqlite3
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="DASOL · Personal Hub", page_icon="✨", layout="centered"
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


# ---------- 크림 톤 감성 CSS 스타일링 ----------
st.markdown(
    """
    <style>
    .stApp {
        background-color: #F7F5F0;
        font-family: 'Courier New', Courier, monospace, sans-serif;
        color: #2C2A29;
    }
    .stButton>button {
        background-color: #2C2A29;
        color: #F7F5F0;
        border: none;
        border-radius: 4px;
        font-family: 'Courier New', Courier, monospace;
        font-weight: 600;
        padding: 6px 14px;
    }
    .stButton>button:hover {
        background-color: #4A4745;
        color: #FFFFFF;
    }
    input, textarea, select {
        background-color: #FFFFFF !important;
        border: 1px solid #D6D0C7 !important;
        border-radius: 4px !important;
        font-family: 'Courier New', Courier, monospace !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

if "intro_passed" not in st.session_state:
    st.session_state.intro_passed = False

# ==========================================
# 0. 인트로 화면 (DASOL)
# ==========================================
if not st.session_state.intro_passed:
    st.markdown(
        """
        <style>
        .intro-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 75vh;
            cursor: pointer;
            text-align: center;
        }
        .intro-title {
            font-family: 'Courier New', Courier, monospace;
            font-size: 3.5rem;
            font-weight: 700;
            letter-spacing: 0.25em;
            color: #2C2A29;
            margin-bottom: 0.5rem;
        }
        .intro-sub {
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.85rem;
            color: #8C8680;
            letter-spacing: 0.15em;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height: 10vh;'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            """
            <div class="intro-container">
                <div class="intro-title">DASOL</div>
                <div class="intro-sub">click to enter</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("ENTER HUB", use_container_width=True):
            st.session_state.intro_passed = True
            st.rerun()
    st.stop()

# ==========================================
# 메인 허브 화면
# ==========================================
st.sidebar.markdown(
    "<h2 style='font-family:Courier New;'>DASOL HUB</h2>", unsafe_allow_html=True
)
menu = st.sidebar.selectbox(
    "메뉴 이동", ["🏃 러닝 일기", "📁 미디어 보관함 (Before / After)"]
)

TODAY = dt.date.today()

# ==========================================
# 1. 러닝 일기 페이지
# ==========================================
if menu == "🏃 러닝 일기":
    st.markdown(
        "<h1 style='font-family: Courier New;'>나의 러닝 일기</h1>",
        unsafe_allow_html=True,
    )
    weekday_str = ["월", "화", "수", "목", "금", "토", "일"][TODAY.weekday()]
    st.markdown(
        f"<p style='color: #7A7570;'>{TODAY.strftime('%Y.%m.%d')} ({weekday_str})</p>",
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

    st.markdown("<hr style='border:1px solid #E6E2DD;'>", unsafe_allow_html=True)

    f_col1, f_col2 = st.columns([2, 1])
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
        for it in filtered_logs:
            m_col = mood_colors.get(it["mood"], "#2C2A29")
            cols = st.columns([1.2, 2, 1, 1.2, 1.5, 2.5])
            cols[0].write(it["date"])
            cols[1].write(it["course"])
            cols[2].markdown(
                f"<span style='color:{m_col}; font-weight:bold;'>{it['mood']}</span>",
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
# 2. 미디어 보관함 (Before / After & 파일명 변경)
# ==========================================
elif menu == "📁 미디어 보관함 (Before / After)":
    st.markdown(
        "<h1 style='font-family: Courier New;'>미디어 보관함</h1>",
        unsafe_allow_html=True,
    )
    st.write(
        "RAW 파일이나 영상 등 원본 화질 그대로 폰과 PC 간에 이동하고, 보정 전후 파일명을 직접 변경하여 관리하세요."
    )

    tab_before, tab_after = st.tabs(["📌 BEFORE (보정 전)", "✨ AFTER (보정 후)"])


    def handle_media_tab(category_name, sub_folder):
        st.markdown(f"### {category_name} 파일 관리")

        uploaded_file = st.file_uploader(
            f"{category_name} 파일 업로드 (RAW, 영상, 이미지 등)",
            key=f"upl_{sub_folder}",
        )
        if uploaded_file is not None:
            orig_name = uploaded_file.name
            # 확장자 추출 (예: .jpg, .RAW, .mp4 등)
            _, ext = os.path.splitext(orig_name)
            # 기본 파일명 (확장자 제외)
            base_default_name = os.path.splitext(orig_name)[0]

            st.info(f"업로드된 원본 파일명: **{orig_name}**")
            new_input_name = st.text_input(
                "저장할 새 파일명 입력 (확장자 자동 유지)",
                value=base_default_name,
                key=f"input_new_name_{sub_folder}",
            )

            if st.button(
                "이 이름으로 최종 저장하기", key=f"btn_save_{sub_folder}"
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
                st.success(
                    f"'{final_name}' (으)로 파일명이 변경되어 저장되었습니다!"
                )
                st.rerun()

        st.markdown("---")
        st.markdown("#### 보관된 파일 목록 및 다운로드")

        conn = get_db()
        items = conn.execute(
            "SELECT * FROM media_logs WHERE category = ? ORDER BY id DESC",
            (sub_folder,),
        ).fetchall()
        conn.close()

        if items:
            for item in items:
                col_info, col_dl, col_del = st.columns([3, 1, 1])
                with col_info:
                    st.write(f"📁 **{item['filename']}**")
                    st.caption(f"업로드 일시: {item['uploaded_at'][:19]}")

                with col_dl:
                    if os.path.exists(item["saved_path"]):
                        with open(item["saved_path"], "rb") as file_data:
                            st.download_button(
                                label="다운로드",
                                data=file_data,
                                file_name=item["filename"],
                                key=f"dl_{item['id']}",
                            )
                    else:
                        st.error("파일 유실됨")

                with col_del:
                    if st.button("삭제", key=f"del_{item['id']}"):
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
                    "<hr style='margin: 4px 0px; border:0.5px solid #EFECE6;'>",
                    unsafe_allow_html=True,
                )
        else:
            st.info(f"등록된 {category_name} 파일이 없습니다.")


    with tab_before:
        handle_media_tab("BEFORE", "before")

    with tab_after:
        handle_media_tab("AFTER", "after")
