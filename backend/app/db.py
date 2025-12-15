import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator, Optional, Dict, Any, List

DB_PATH_ENV = "DATABASE_PATH"
DEFAULT_DB_FILENAME = "notes.db"


def _get_db_path() -> str:
    """
    Determine the sqlite database file path from env or default to instance folder.
    """
    db_path = os.getenv(DB_PATH_ENV)
    if db_path:
        return db_path
    # Place DB inside backend instance folder to keep container self-contained
    base_dir = os.path.dirname(os.path.abspath(__file__))
    instance_dir = os.path.join(os.path.dirname(base_dir), "instance")
    os.makedirs(instance_dir, exist_ok=True)
    return os.path.join(instance_dir, DEFAULT_DB_FILENAME)


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """
    Context manager yielding a SQLite connection with row factory as dict-like rows.
    """
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """
    Initialize database schema if not already created.
    Creates tables: notes, tags, note_tags
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS note_tags (
                note_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (note_id, tag_id),
                FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
            """
        )
        conn.commit()


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def get_or_create_tag_ids(conn: sqlite3.Connection, tag_names: List[str]) -> List[int]:
    """
    Ensure all tag names exist and return their IDs.
    """
    ids: List[int] = []
    for name in tag_names:
        name = name.strip()
        if not name:
            continue
        cur = conn.execute("SELECT id FROM tags WHERE name = ?", (name,))
        row = cur.fetchone()
        if row:
            ids.append(row["id"])
        else:
            cur = conn.execute("INSERT INTO tags (name) VALUES (?)", (name,))
            ids.append(cur.lastrowid)
    return ids


def set_note_tags(conn: sqlite3.Connection, note_id: int, tag_names: List[str]) -> List[str]:
    """
    Replace note tag set with provided names. Returns sorted tag names.
    """
    # Clear existing
    conn.execute("DELETE FROM note_tags WHERE note_id = ?", (note_id,))
    tag_ids = get_or_create_tag_ids(conn, tag_names)
    for tid in tag_ids:
        conn.execute("INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)", (note_id, tid))
    # Return normalized names
    names = []
    for tid in tag_ids:
        r = conn.execute("SELECT name FROM tags WHERE id = ?", (tid,)).fetchone()
        if r:
            names.append(r["name"])
    return sorted(set(names))


def get_tags_for_note(conn: sqlite3.Connection, note_id: int) -> List[str]:
    cur = conn.execute(
        """
        SELECT t.name
        FROM tags t
        JOIN note_tags nt ON nt.tag_id = t.id
        WHERE nt.note_id = ?
        ORDER BY t.name ASC
        """,
        (note_id,),
    )
    return [r["name"] for r in cur.fetchall()]


def list_notes(
    q: Optional[str] = None,
    tag: Optional[str] = None,
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    List notes with optional search q (title/content), filter by tag and category.
    """
    with get_conn() as conn:
        params: List[Any] = []
        where: List[str] = []
        join: List[str] = []

        if q:
            where.append("(n.title LIKE ? OR n.content LIKE ?)")
            like = f"%{q}%"
            params.extend([like, like])
        if category:
            where.append("n.category = ?")
            params.append(category)
        if tag:
            join.append("JOIN note_tags nt ON nt.note_id = n.id")
            join.append("JOIN tags t ON t.id = nt.tag_id")
            where.append("t.name = ?")
            params.append(tag)

        sql = f"""
        SELECT n.*
        FROM notes n
        {' '.join(join)}
        {'WHERE ' + ' AND '.join(where) if where else ''}
        ORDER BY n.updated_at DESC, n.created_at DESC
        """
        cur = conn.execute(sql, tuple(params))
        rows = cur.fetchall()
        results = []
        for r in rows:
            d = row_to_dict(r)
            d["tags"] = get_tags_for_note(conn, d["id"])
            results.append(d)
        return results


def create_note(data: Dict[str, Any]) -> Dict[str, Any]:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO notes (title, content, category)
            VALUES (?, ?, ?)
            """,
            (data["title"], data["content"], data.get("category")),
        )
        note_id = cur.lastrowid
        tags = data.get("tags") or []
        normalized_tags = set_note_tags(conn, note_id, tags) if tags else []
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        note = row_to_dict(row)
        note["tags"] = normalized_tags
        return note


def get_note(note_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not row:
            return None
        d = row_to_dict(row)
        d["tags"] = get_tags_for_note(conn, note_id)
        return d


def update_note(note_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        exists = conn.execute("SELECT id FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not exists:
            return None
        sets = []
        params: List[Any] = []
        if "title" in data:
            sets.append("title = ?")
            params.append(data["title"])
        if "content" in data:
            sets.append("content = ?")
            params.append(data["content"])
        if "category" in data:
            sets.append("category = ?")
            params.append(data["category"])
        if sets:
            sets.append("updated_at = CURRENT_TIMESTAMP")
            sql = f"UPDATE notes SET {', '.join(sets)} WHERE id = ?"
            params.append(note_id)
            conn.execute(sql, tuple(params))
        if "tags" in data:
            set_note_tags(conn, note_id, data.get("tags") or [])
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        d = row_to_dict(row)
        d["tags"] = get_tags_for_note(conn, note_id)
        return d


def delete_note(note_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        return cur.rowcount > 0


def list_all_tags() -> List[str]:
    with get_conn() as conn:
        cur = conn.execute("SELECT name FROM tags ORDER BY name ASC")
        return [r["name"] for r in cur.fetchall()]


def seed_data() -> None:
    """
    Populate database with a few notes and tags if empty.
    """
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM notes").fetchone()["c"]
        if count > 0:
            return
        samples = [
            {
                "title": "Welcome to Notes",
                "content": "This is your first note. You can edit or delete it.",
                "category": "general",
                "tags": ["welcome", "getting-started"],
            },
            {
                "title": "Grocery List",
                "content": "- Milk\n- Eggs\n- Bread\n- Coffee",
                "category": "personal",
                "tags": ["list", "errands"],
            },
            {
                "title": "Project Ideas",
                "content": "1. Build a notes app\n2. Explore Flask-Smorest\n3. Add tagging/search",
                "category": "work",
                "tags": ["ideas", "work"],
            },
        ]
        for s in samples:
            cur = conn.execute(
                "INSERT INTO notes (title, content, category) VALUES (?, ?, ?)",
                (s["title"], s["content"], s["category"]),
            )
            nid = cur.lastrowid
            set_note_tags(conn, nid, s["tags"])
