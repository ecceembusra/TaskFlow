import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional, List

import streamlit as st

# -----------------------------
# Config
# -----------------------------
DB_PATH = Path("data") / "kanban.db"
WIP_LIMIT = 3
STATUSES = ["BACKLOG", "DOING", "DONE"]


# -----------------------------
# Domain
# -----------------------------
@dataclass
class Task:
    id: int
    project_id: int
    title: str
    description: str
    priority: int
    status: str
    due_date: Optional[str]
    tags: List[str]
    created_at: str


# -----------------------------
# DB helpers
# -----------------------------
def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        priority INTEGER NOT NULL,
        status TEXT NOT NULL,
        due_date TEXT,
        tags_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(project_id) REFERENCES projects(id)
    );
    """)
    conn.commit()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def normalize_tags(tags: List[str]) -> List[str]:
    cleaned: List[str] = []
    for t in tags:
        t = (t or "").strip().lower()
        if t and t not in cleaned:
            cleaned.append(t)
    return cleaned


def parse_tags(s: str) -> List[str]:
    s = (s or "").strip()
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def tags_to_json(tags: List[str]) -> str:
    return json.dumps(tags, ensure_ascii=False)


def tags_from_json(s: str) -> List[str]:
    if not s:
        return []
    try:
        data = json.loads(s)
        if isinstance(data, list):
            return [str(x) for x in data]
    except Exception:
        pass
    return []


# -----------------------------
# Repositories (inline)
# -----------------------------
def list_projects(conn: sqlite3.Connection):
    return conn.execute("SELECT * FROM projects ORDER BY id DESC").fetchall()


def get_project_by_name(conn: sqlite3.Connection, name: str):
    return conn.execute("SELECT * FROM projects WHERE name = ?", (name.strip(),)).fetchone()


def get_project_by_id(conn: sqlite3.Connection, project_id: int):
    return conn.execute("SELECT * FROM projects WHERE id = ?", (int(project_id),)).fetchone()


def create_project(conn: sqlite3.Connection, name: str) -> int:
    name = (name or "").strip()
    if len(name) < 2:
        raise ValueError("Proje adı en az 2 karakter olmalı.")
    cur = conn.cursor()
    cur.execute("INSERT INTO projects(name, created_at) VALUES (?, ?)", (name, now_iso()))
    conn.commit()
    return int(cur.lastrowid)


def rename_project(conn: sqlite3.Connection, project_id: int, new_name: str) -> None:
    new_name = (new_name or "").strip()
    if len(new_name) < 2:
        raise ValueError("Yeni proje adı en az 2 karakter olmalı.")

    # aynı isim var mı?
    existing = conn.execute(
        "SELECT id FROM projects WHERE name = ?",
        (new_name,),
    ).fetchone()
    if existing and int(existing["id"]) != int(project_id):
        raise ValueError("Bu isimde başka bir proje zaten var. Farklı bir isim dene.")

    conn.execute("UPDATE projects SET name = ? WHERE id = ?", (new_name, int(project_id)))
    conn.commit()


def add_task(
    conn: sqlite3.Connection,
    project_id: int,
    title: str,
    description: str,
    priority: int,
    due_date: Optional[str],
    tags: List[str],
) -> int:
    title = (title or "").strip()
    if len(title) < 2:
        raise ValueError("Başlık en az 2 karakter olmalı.")
    priority = int(priority)
    if not (1 <= priority <= 5):
        raise ValueError("Öncelik 1-5 arasında olmalı.")
    if due_date:
        date.fromisoformat(due_date)  # validate YYYY-MM-DD

    tags = normalize_tags(tags)

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO tasks(project_id, title, description, priority, status, due_date, tags_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(project_id),
            title,
            (description or "").strip(),
            int(priority),
            "BACKLOG",
            due_date,
            tags_to_json(tags),
            now_iso(),
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def fetch_tasks(conn: sqlite3.Connection, project_id: int) -> List[Task]:
    rows = conn.execute(
        "SELECT * FROM tasks WHERE project_id = ? ORDER BY priority ASC, id DESC",
        (int(project_id),),
    ).fetchall()

    out: List[Task] = []
    for r in rows:
        out.append(
            Task(
                id=int(r["id"]),
                project_id=int(r["project_id"]),
                title=str(r["title"]),
                description=str(r["description"]),
                priority=int(r["priority"]),
                status=str(r["status"]),
                due_date=None if r["due_date"] is None else str(r["due_date"]),
                tags=tags_from_json(str(r["tags_json"])),
                created_at=str(r["created_at"]),
            )
        )
    return out


def move_task(conn: sqlite3.Connection, project_id: int, task_id: int, new_status: str) -> None:
    new_status = (new_status or "").strip().upper()
    if new_status not in STATUSES:
        raise ValueError("Geçersiz status.")

    row = conn.execute("SELECT id, project_id, status FROM tasks WHERE id = ?", (int(task_id),)).fetchone()
    if not row:
        raise ValueError("Task bulunamadı.")
    if int(row["project_id"]) != int(project_id):
        raise ValueError("Bu task aktif projeye ait değil.")

    if new_status == "DOING":
        doing_count = conn.execute(
            "SELECT COUNT(*) AS c FROM tasks WHERE project_id = ? AND status = 'DOING'",
            (int(project_id),),
        ).fetchone()["c"]
        if str(row["status"]) != "DOING" and int(doing_count) >= WIP_LIMIT:
            raise ValueError(f"WIP limit dolu: DOING en fazla {WIP_LIMIT} task olabilir.")

    conn.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, int(task_id)))
    conn.commit()


def delete_task(conn: sqlite3.Connection, project_id: int, task_id: int) -> None:
    row = conn.execute("SELECT id, project_id FROM tasks WHERE id = ?", (int(task_id),)).fetchone()
    if not row:
        return
    if int(row["project_id"]) != int(project_id):
        raise ValueError("Bu task aktif projeye ait değil.")
    conn.execute("DELETE FROM tasks WHERE id = ?", (int(task_id),))
    conn.commit()


# -----------------------------
# UI helpers
# -----------------------------
def deadline_badge(due_date: Optional[str]) -> str:
    if not due_date:
        return ""
    try:
        d = date.fromisoformat(due_date)
        days_left = (d - date.today()).days
        if days_left < 0:
            return " ⛔"
        if days_left <= 2:
            return " ⚠️"
        return ""
    except Exception:
        return ""


def filter_tasks(tasks: List[Task], query: str, tag: str) -> List[Task]:
    q = (query or "").strip().lower()
    t = (tag or "").strip().lower()

    def ok(task: Task) -> bool:
        if q:
            hay = f"{task.title} {task.description}".lower()
            if q not in hay:
                return False
        if t:
            if t not in [x.lower() for x in task.tags]:
                return False
        return True

    return [x for x in tasks if ok(x)]


def tasks_to_csv(tasks: List[Task]) -> str:
    import csv
    import io

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["id", "title", "description", "priority", "status", "due_date", "tags", "created_at"])
    for t in tasks:
        w.writerow([t.id, t.title, t.description, t.priority, t.status, t.due_date or "", ",".join(t.tags), t.created_at])
    return out.getvalue()


# -----------------------------
# Streamlit App
# -----------------------------
st.set_page_config(page_title="TaskFlow", page_icon="🗂️", layout="wide")
st.title("📋 TaskFlow ")

conn = get_conn()
init_db(conn)

# Sidebar Project
st.sidebar.header("📁 Proje")

if "active_project_id" not in st.session_state:
    st.session_state.active_project_id = None
if "active_project_name" not in st.session_state:
    st.session_state.active_project_name = None

projects = list_projects(conn)
project_names = [p["name"] for p in projects]

# Create project
new_project_name = st.sidebar.text_input("Yeni proje adı")
if st.sidebar.button("Proje Oluştur"):
    try:
        existing = get_project_by_name(conn, new_project_name)
        if existing:
            st.session_state.active_project_id = int(existing["id"])
            st.session_state.active_project_name = str(existing["name"])
            st.sidebar.success("Proje zaten vardı, seçildi.")
        else:
            pid = create_project(conn, new_project_name)
            st.session_state.active_project_id = pid
            st.session_state.active_project_name = new_project_name.strip()
            st.sidebar.success("Proje oluşturuldu ve seçildi.")
        st.rerun()
    except Exception as e:
        st.sidebar.error(str(e))

# Select project
if project_names:
    default_idx = 0
    if st.session_state.active_project_name in project_names:
        default_idx = project_names.index(st.session_state.active_project_name)

    selected_name = st.sidebar.selectbox("Proje seç", project_names, index=default_idx)
    selected_row = get_project_by_name(conn, selected_name)
    if selected_row:
        st.session_state.active_project_id = int(selected_row["id"])
        st.session_state.active_project_name = str(selected_row["name"])
else:
    st.info("Soldan bir proje oluştur. (En az 2 karakter)")
    st.stop()

if not st.session_state.active_project_id:
    st.stop()

# ---- RENAME UI (NEW) ----
st.sidebar.divider()
st.sidebar.subheader("✏️ Proje adını düzenle")

current_project = get_project_by_id(conn, st.session_state.active_project_id)
current_name = str(current_project["name"]) if current_project else (st.session_state.active_project_name or "")

new_name = st.sidebar.text_input("Yeni ad", value=current_name)
if st.sidebar.button("Rename"):
    try:
        rename_project(conn, st.session_state.active_project_id, new_name)
        # session state update
        st.session_state.active_project_name = new_name.strip()
        st.sidebar.success("Proje adı güncellendi.")
        st.rerun()
    except Exception as e:
        st.sidebar.error(str(e))
# -------------------------

st.caption(
    f"Aktif proje: **{st.session_state.active_project_name}** | "
    f"WIP(DOING) limit: **{WIP_LIMIT}** | "
    f"Tarih: **{date.today().isoformat()}**"
)

# Search/filter row
c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    query = st.text_input("🔎 Ara (başlık/açıklama)")
with c2:
    tag_filter = st.text_input("🏷️ Tag filtre (örn: acil)")
with c3:
    st.write("")
    st.write("")
    if st.button("🔄 Yenile"):
        st.rerun()

# Add Task (FORM: clear_on_submit fixes session_state widget issue)
with st.expander("➕ Task Ekle", expanded=True):
    with st.form("add_task_form", clear_on_submit=True):
        f1, f2, f3, f4 = st.columns([2, 2, 1, 1])
        with f1:
            title = st.text_input("Başlık")
        with f2:
            tags_s = st.text_input("Etiketler (virgülle)", placeholder="bug, acil, okul")
        with f3:
            priority = st.number_input("Öncelik (1-5)", min_value=1, max_value=5, value=3, step=1)
        with f4:
            due = st.text_input("Bitiş (YYYY-MM-DD)", placeholder="2025-12-31")

        desc = st.text_area("Açıklama (opsiyonel)")
        submitted = st.form_submit_button("✅ Kaydet")

    if submitted:
        try:
            due_val = due.strip() or None
            tid = add_task(
                conn,
                st.session_state.active_project_id,
                title=title,
                description=desc,
                priority=int(priority),
                due_date=due_val,
                tags=parse_tags(tags_s),
            )
            st.success(f"Task oluşturuldu: #{tid}")
            st.rerun()
        except Exception as e:
            st.error(str(e))

# Load tasks
all_tasks = fetch_tasks(conn, st.session_state.active_project_id)
filtered = filter_tasks(all_tasks, query=query, tag=tag_filter)

# CSV Export
csv_data = tasks_to_csv(filtered)
st.download_button(
    "⬇️ CSV indir (filtrelenmiş)",
    data=csv_data.encode("utf-8"),
    file_name="kanban_tasks.csv",
    mime="text/csv",
)

st.divider()

backlog = [t for t in filtered if t.status == "BACKLOG"]
doing = [t for t in filtered if t.status == "DOING"]
done = [t for t in filtered if t.status == "DONE"]

# For WIP info we need actual DOING count (not filtered)
doing_count_all = len([t for t in all_tasks if t.status == "DOING"])

col1, col2, col3 = st.columns(3)

def render_task_card(t: Task):
    badge = deadline_badge(t.due_date)
    st.markdown(f"**#{t.id}** — (p{t.priority}) {t.title}{badge}")

    meta = []
    if t.due_date:
        meta.append(f"📅 {t.due_date}")
    if t.tags:
        meta.append("🏷️ " + ", ".join(t.tags))
    meta.append(f"🕒 {t.created_at}")
    st.caption(" | ".join(meta))

    if t.description:
        st.write(t.description)

    b1, b2, b3, b4 = st.columns([1, 1, 1, 1])
    with b1:
        if st.button("⬅️ BACKLOG", key=f"to_backlog_{t.id}", disabled=(t.status == "BACKLOG")):
            try:
                move_task(conn, t.project_id, t.id, "BACKLOG")
                st.rerun()
            except Exception as e:
                st.error(str(e))
    with b2:
        if st.button("➡️ DOING", key=f"to_doing_{t.id}", disabled=(t.status == "DOING")):
            try:
                move_task(conn, t.project_id, t.id, "DOING")
                st.rerun()
            except Exception as e:
                st.error(str(e))
    with b3:
        if st.button("✅ DONE", key=f"to_done_{t.id}", disabled=(t.status == "DONE")):
            try:
                move_task(conn, t.project_id, t.id, "DONE")
                st.rerun()
            except Exception as e:
                st.error(str(e))
    with b4:
        if st.button("🗑️ Sil", key=f"del_{t.id}"):
            try:
                delete_task(conn, t.project_id, t.id)
                st.rerun()
            except Exception as e:
                st.error(str(e))

    st.divider()

with col1:
    st.subheader(f"📌 BACKLOG ({len(backlog)})")
    for t in backlog:
        render_task_card(t)

with col2:
    st.subheader(f"⚙️ DOING ({len(doing)}/{WIP_LIMIT})")
    if doing_count_all >= WIP_LIMIT:
        st.info("WIP limit dolu: DOING için önce bir task’ı DONE/BACKLOG yap.")
    for t in doing:
        render_task_card(t)

with col3:
    st.subheader(f"🏁 DONE ({len(done)})")
    for t in done:
        render_task_card(t)