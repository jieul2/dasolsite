import calendar
import datetime as dt
import re
import sqlite3
import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="Ember & Trail · 통합 기록", page_icon="⏱️", layout="centered"
)

DB_PATH = "integrated_ember_trail.db"


# ---------- 데이터베이스 초기화 ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # 1. 과목 테이블
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            color TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            archived INTEGER NOT NULL DEFAULT 0
        )
    """
    )
    # 2. 공부 시간 로그 테이블
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS study_logs (
            day TEXT NOT NULL,
            subject_id INTEGER NOT NULL,
            seconds INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (day, subject_id)
        )
    """
    )
    # 3. 일자별 메모 테이블
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS study_notes (
            day TEXT PRIMARY KEY,
            text TEXT NOT NULL
        )
    """
    )
    # 4. 인강 진도율 테이블
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS lectures (
            subject_id INTEGER PRIMARY KEY,
            total INTEGER NOT NULL DEFAULT 0,
            done INTEGER NOT NULL DEFAULT 0
        )
    """
    )
    # 5. 러닝 기록 테이블
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
    # 6. 설정 테이블
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS kv (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """
    )

    # 기본 과목 세팅 (없을 경우)
    c.execute("SELECT COUNT(*) FROM subjects")
    if c.fetchone()[0] == 0:
        defaults = [
            ("헌법", "#D9733B", 0),
            ("경찰학", "#4E8CD6", 1),
            ("형사법", "#3F9A69", 2),
        ]
        c.executemany(
            "INSERT INTO subjects(name, color, position) VALUES (?, ?, ?)",
            defaults,
        )
    conn.commit()
    conn.close()


init_db()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------- 유틸리티 함수 ----------
def fmt_kor(sec):
    sec = int(sec)
    return f"{sec // 3600}시간 {sec % 3600 // 60}분"


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


def get_setting(key, default):
    conn = get_db()
    row = conn.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
    conn.close()
    if row:
        import json

        return json.loads(row["value"])
    return default


def set_setting(key, value):
    import json

    conn = get_db()
    conn.execute(
        "INSERT INTO kv(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, json.dumps(value, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()


# ---------- 사이드바 네비게이션 ----------
st.sidebar.title("📌 통합 기록장")
menu = st.sidebar.selectbox(
    "메뉴 선택",
    [
        "🍅 공부 타이머",
        "📅 공부 캘린더/기록",
        "🏃 러닝 일기",
        "📚 과목 & 인강 관리",
        "⚙️ 설정",
    ],
)

TODAY = dt.date.today().isoformat()

# ==========================================
# 1. 공부 타이머 페이지
# ==========================================
if menu == "🍅 공부 타이머":
    st.title("🍅 오늘의 집중 공부")
    exam_date = get_setting("exam_date", "2027-03-13")
    try:
        diff = (dt.date.fromisoformat(exam_date) - dt.date.today()).days
        if diff == 0:
            dday_str = "D-DAY"
        elif diff > 0:
            dday_str = f"D-{diff}"
        else:
            dday_str = f"D+{-diff}"
    except:
        dday_str = "시험일 미설정"

    weekday_str = ["월", "화", "수", "목", "금", "토", "일"][dt.date.today().weekday()]
    st.write(
        f"📅 {dt.date.today().strftime('%Y.%m.%d')} ({weekday_str}) · **{dday_str}**"
    )

    conn = get_db()
    subjects = conn.execute(
        "SELECT id, name, color FROM subjects WHERE archived = 0"
    ).fetchall()
    conn.close()

    if not subjects:
        st.warning("등록된 과목이 없습니다. '과목 & 인강 관리'에서 추가해주세요.")
    else:
        subj_dict = {s["name"]: s["id"] for s in subjects}
        selected_subj_name = st.selectbox("공부할 과목", list(subj_dict.keys()))
        selected_subj_id = subj_dict[selected_subj_name]

        col1, col2 = st.columns(2)
        with col1:
            study_minutes = st.number_input(
                "집중 시간 (분)", min_value=1, max_value=300, value=50
            )
        with col2:
            st.write("")
            st.write("")
            save_btn = st.button(
                "공부 시간 기록하기", type="primary", use_container_width=True
            )

        if save_btn:
            add_sec = study_minutes * 60
            conn = get_db()
            conn.execute(
                """
                INSERT INTO study_logs(day, subject_id, seconds) VALUES(?, ?, ?)
                ON CONFLICT(day, subject_id) DO UPDATE SET seconds = seconds + excluded.seconds
            """,
                (TODAY, selected_subj_id, add_sec),
            )
            conn.commit()
            conn.close()
            st.success(
                f"🎉 [{selected_subj_name}] {study_minutes}분 공부 기록이 저장되었습니다!"
            )

        # 오늘 현황
        st.subheader("📈 오늘 과목별 현황")
        conn = get_db()
        logs = conn.execute(
            """
            SELECT s.name, s.color, l.seconds FROM study_logs l
            JOIN subjects s ON l.subject_id = s.id
            WHERE l.day = ?
        """,
            (TODAY,),
        ).fetchall()
        conn.close()

        if logs:
            total_sec = sum(row["seconds"] for row in logs)
            goal_hours = get_setting("goal_hours", 8.0)
            goal_sec = goal_hours * 3600
            pct = min(100, (total_sec / goal_sec) * 100) if goal_sec else 0

            st.info(
                f"오늘 총 집중 시간: **{fmt_kor(total_sec)}** (목표 {goal_hours}시간 중 {pct:.0f}%)"
            )
            st.progress(pct / 100)

            for r in logs:
                st.markdown(
                    f"- <span style='color:{r['color']}'>●</span> **{r['name']}**: {fmt_kor(r['seconds'])}",
                    unsafe_allow_html=True,
                )
        else:
            st.write("아직 오늘 기록된 공부 시간이 없습니다.")

# ==========================================
# 2. 공부 캘린더 / 기록 페이지
# ==========================================
elif menu == "📅 공부 캘린더/기록":
    st.title("📅 날짜별 공부 기록")
    pick_date = st.date_input("날짜 선택", dt.date.today())
    day_str = pick_date.isoformat()

    conn = get_db()
    subs = conn.execute(
        "SELECT id, name, color FROM subjects WHERE archived = 0"
    ).fetchall()
    existing_logs = {
        r["subject_id"]: r["seconds"]
        for r in conn.execute(
            "SELECT subject_id, seconds FROM study_logs WHERE day = ?",
            (day_str,),
        ).fetchall()
    }
    note_row = conn.execute(
        "SELECT text FROM study_notes WHERE day = ?", (day_str,)
    ).fetchone()
    conn.close()

    current_note = note_row["text"] if note_row else ""

    st.subheader(f"📝 {day_str} 과목별 시간 수정 (분 단위)")
    new_logs = {}
    for s in subs:
        val_min = int(existing_logs.get(s["id"], 0) // 60)
        new_logs[s["id"]] = (
            st.number_input(
                f"{s['name']}",
                min_value=0,
                max_value=1440,
                value=val_min,
                step=10,
            )
            * 60
        )

    new_memo = st.text_area("하루 공부 메모", value=current_note)

    if st.button("기록 저장", type="primary"):
        conn = get_db()
        conn.execute("DELETE FROM study_logs WHERE day = ?", (day_str,))
        for sid, sec in new_logs.items():
            if sec > 0:
                conn.execute(
                    "INSERT INTO study_logs(day, subject_id, seconds) VALUES(?, ?, ?)",
                    (day_str, sid, sec),
                )
        if new_memo.strip():
            conn.execute(
                "INSERT OR REPLACE INTO study_notes(day, text) VALUES(?, ?)",
                (day_str, new_memo),
            )
        else:
            conn.execute("DELETE FROM study_notes WHERE day = ?", (day_str,))
        conn.commit()
        conn.close()
        st.success("저장되었습니다!")

# ==========================================
# 3. 러닝 일기 페이지
# ==========================================
elif menu == "🏃 러닝 일기":
    st.title("🏃 나의 러닝 일기")

    with st.form("running_form"):
        st.subheader("새 러닝 기록 추가")
        r_date = st.date_input("러닝 날짜", dt.date.today())
        r_course = st.text_input(
            "코스명 (예: 한강 코스 (5km))", value="한강 코스 (5km)"
        )
        r_mood = st.selectbox(
            "기분", ["GREAT", "GOOD", "SO SO", "BAD", "TERRIBLE"]
        )
        r_time_input = st.text_input(
            "소요 시간 (예: 00:25:00 또는 2530)", value="00:25:00"
        )
        r_memo = st.text_area("러닝 메모")

        submit_run = st.form_submit_button("러닝 기록 저장", type="primary")

        if submit_run:
            sec, hms = parse_time_str(r_time_input)
            if sec is None:
                st.error(
                    "시간 형식이 올바르지 않습니다. (예: 00:25:00 또는 2530)"
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
                st.success("러닝 기록이 저장되었습니다!")

    st.subheader("📋 러닝 기록 목록")
    conn = get_db()
    runs = conn.execute(
        "SELECT * FROM running_logs ORDER BY date DESC"
    ).fetchall()
    conn.close()

    if runs:
        for run in runs:
            with st.expander(
                f"📅 {run['date']} — {run['course']} ({run['pace']})"
            ):
                m, s = divmod(run["time_sec"], 60)
                h, m = divmod(m, 60)
                t_str = f"{h}시간 {m}분 {s}초" if h else f"{m}분 {s}초"
                st.write(
                    f"**기분:** {run['mood']} | **소요 시간:** {t_str}"
                )
                if run["memo"]:
                    st.write(f"**메모:** {run['memo']}")
    else:
        st.write("저장된 러닝 기록이 없습니다.")

# ==========================================
# 4. 과목 & 인강 관리 페이지
# ==========================================
elif menu == "📚 과목 & 인강 관리":
    st.title("📚 과목 및 인강 진도율 관리")

    # 새 과목 추가
    with st.form("add_subj_form"):
        new_name = st.text_input("새 과목 이름 (최대 20자)")
        add_sub_btn = st.form_submit_button("과목 추가", type="primary")
        if add_sub_btn:
            if not new_name.strip() or len(new_name) > 20:
                st.warning("과목명은 1~20자로 입력하세요.")
            else:
                swatches = [
                    "#D9733B",
                    "#4E8CD6",
                    "#3F9A69",
                    "#9B63C7",
                    "#D0587A",
                    "#C9A227",
                    "#3AA3A3",
                    "#7A7A8C",
                ]
                conn = get_db()
                cnt = conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[
                    0
                ]
                color = swatches[cnt % len(swatches)]
                try:
                    conn.execute(
                        "INSERT INTO subjects(name, color, position) VALUES(?, ?, ?)",
                        (new_name.strip(), color, cnt),
                    )
                    conn.commit()
                    st.success(f"[{new_name.strip()}] 과목이 추가되었습니다!")
                except sqlite3.IntegrityError:
                    st.error("이미 존재하는 과목 이름입니다.")
                conn.close()

    st.subheader("과목 목록 및 인강 진도 설정")
    conn = get_db()
    subs = conn.execute(
        "SELECT id, name, color, archived FROM subjects ORDER BY position"
    ).fetchall()
    conn.close()

    for s in subs:
        col1, col2 = st.columns([2, 1])
        with col1:
            archived_text = " (보관됨)" if s["archived"] else ""
            st.markdown(
                f"<span style='color:{s['color']}'>●</span> **{s['name']}**{archived_text}",
                unsafe_allow_html=True,
            )
        with col2:
            if s["archived"]:
                if st.button("복원", key=f"unarch_{s['id']}"):
                    conn = get_db()
                    conn.execute(
                        "UPDATE subjects SET archived = 0 WHERE id = ?",
                        (s["id"],),
                    )
                    conn.commit()
                    conn.close()
                    st.rerun()
            else:
                if st.button("보관", key=f"arch_{s['id']}"):
                    conn = get_db()
                    conn.execute(
                        "UPDATE subjects SET archived = 1 WHERE id = ?",
                        (s["id"],),
                    )
                    conn.commit()
                    conn.close()
                    st.rerun()

# ==========================================
# 5. 설정 페이지
# ==========================================
elif menu == "⚙️ 설정":
    st.title("⚙️ 환경 설정")

    current_goal = get_setting("goal_hours", 8.0)
    current_exam = get_setting("exam_date", "2027-03-13")

    new_goal = st.number_input(
        "하루 공부 목표 시간 (시간)",
        min_value=1.0,
        max_value=16.0,
        value=float(current_goal),
        step=0.5,
    )

    try:
        d_init = dt.date.fromisoformat(current_exam)
    except:
        d_init = dt.date.today()

    new_exam = st.date_input("시험일 선택", d_init)

    if st.button("설정 저장", type="primary"):
        set_setting("goal_hours", new_goal)
        set_setting("exam_date", new_exam.isoformat())
        st.success("설정이 저장되었습니다!")
