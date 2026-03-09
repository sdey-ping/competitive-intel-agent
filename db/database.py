import sqlite3
import json
import os
from datetime import datetime
from config.settings import DB_PATH

# Path to the seed file — checked into the repo, survives redeploys
SEED_FILE = os.path.join(os.path.dirname(__file__), "..", "config", "competitors.json")


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist, then seed competitors from config/competitors.json."""
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS competitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_name TEXT UNIQUE NOT NULL,
            website_url TEXT,
            blog_url TEXT,
            docs_url TEXT,
            changelog_url TEXT,
            youtube_channel TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            research_query TEXT,
            vendors_covered TEXT,
            report_markdown TEXT,
            gdrive_link TEXT,
            run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS diff_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER,
            vendor_name TEXT,
            previous_snapshot TEXT,
            new_snapshot TEXT,
            delta_summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()

    # ── Seed competitors from config/competitors.json if table is empty ────────
    _seed_competitors_if_empty(conn)

    conn.close()


def _seed_competitors_if_empty(conn):
    """
    If the competitors table is empty (e.g. after a Streamlit Cloud redeploy
    wiped the SQLite file), re-populate it from config/competitors.json.
    That file is checked into the repo and always survives redeploys.
    """
    seed_path = os.path.abspath(SEED_FILE)
    if not os.path.exists(seed_path):
        return

    c = conn.cursor()
    count = c.execute("SELECT COUNT(*) FROM competitors").fetchone()[0]
    if count > 0:
        return  # Already populated — don't overwrite

    try:
        with open(seed_path, "r") as f:
            competitors = json.load(f)

        for comp in competitors:
            c.execute("""
                INSERT OR IGNORE INTO competitors
                    (vendor_name, website_url, blog_url, docs_url, changelog_url, youtube_channel)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                comp.get("vendor_name", ""),
                comp.get("website_url", ""),
                comp.get("blog_url", ""),
                comp.get("docs_url", ""),
                comp.get("changelog_url", ""),
                comp.get("youtube_channel", ""),
            ))
        conn.commit()
    except Exception as e:
        # Non-fatal — app still works, user just needs to re-add competitors manually
        print(f"[database] Seed failed: {e}")


# ── Competitors CRUD ───────────────────────────────────────────────────────────

def get_all_competitors():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM competitors ORDER BY vendor_name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_competitor_by_name(vendor_name: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM competitors WHERE vendor_name = ?", (vendor_name,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def add_competitor(vendor_name, website_url="", blog_url="",
                   docs_url="", changelog_url="", youtube_channel="") -> bool:
    """Returns True if inserted, False if vendor_name already exists."""
    try:
        conn = get_connection()
        conn.execute("""
            INSERT INTO competitors (vendor_name, website_url, blog_url, docs_url, changelog_url, youtube_channel)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (vendor_name, website_url, blog_url, docs_url, changelog_url, youtube_channel))
        conn.commit()
        conn.close()

        # ── Also persist to seed file so it survives next redeploy ────────────
        _sync_competitor_to_seed_file(vendor_name, website_url, blog_url,
                                      docs_url, changelog_url, youtube_channel)
        return True
    except sqlite3.IntegrityError:
        return False


def update_competitor(competitor_id, vendor_name, website_url="", blog_url="",
                      docs_url="", changelog_url="", youtube_channel=""):
    conn = get_connection()
    conn.execute("""
        UPDATE competitors
        SET vendor_name=?, website_url=?, blog_url=?, docs_url=?, changelog_url=?, youtube_channel=?
        WHERE id=?
    """, (vendor_name, website_url, blog_url, docs_url, changelog_url, youtube_channel, competitor_id))
    conn.commit()
    conn.close()

    # ── Re-sync the full table to seed file ───────────────────────────────────
    _rebuild_seed_file()


def delete_competitor(competitor_id):
    conn = get_connection()
    conn.execute("DELETE FROM competitors WHERE id=?", (competitor_id,))
    conn.commit()
    conn.close()

    # ── Re-sync the full table to seed file ───────────────────────────────────
    _rebuild_seed_file()


# ── Seed file sync helpers ─────────────────────────────────────────────────────

def _sync_competitor_to_seed_file(vendor_name, website_url, blog_url,
                                   docs_url, changelog_url, youtube_channel):
    """Append a new competitor to the seed JSON file."""
    seed_path = os.path.abspath(SEED_FILE)
    try:
        existing = []
        if os.path.exists(seed_path):
            with open(seed_path, "r") as f:
                existing = json.load(f)

        # Avoid duplicates
        names = {c["vendor_name"] for c in existing}
        if vendor_name not in names:
            existing.append({
                "vendor_name": vendor_name,
                "website_url": website_url,
                "blog_url": blog_url,
                "docs_url": docs_url,
                "changelog_url": changelog_url,
                "youtube_channel": youtube_channel,
            })
            with open(seed_path, "w") as f:
                json.dump(existing, f, indent=2)
    except Exception as e:
        print(f"[database] Could not sync to seed file: {e}")


def _rebuild_seed_file():
    """Rewrite the seed file from current DB state after an update or delete."""
    seed_path = os.path.abspath(SEED_FILE)
    try:
        competitors = get_all_competitors()
        data = [
            {
                "vendor_name": c["vendor_name"],
                "website_url": c.get("website_url", ""),
                "blog_url": c.get("blog_url", ""),
                "docs_url": c.get("docs_url", ""),
                "changelog_url": c.get("changelog_url", ""),
                "youtube_channel": c.get("youtube_channel", ""),
            }
            for c in competitors
        ]
        with open(seed_path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[database] Could not rebuild seed file: {e}")


# ── Reports CRUD ───────────────────────────────────────────────────────────────

def save_report(research_query, vendors_covered, report_markdown, gdrive_link="") -> int:
    conn = get_connection()
    cursor = conn.execute("""
        INSERT INTO reports (research_query, vendors_covered, report_markdown, gdrive_link)
        VALUES (?, ?, ?, ?)
    """, (
        research_query,
        json.dumps(vendors_covered),
        report_markdown,
        gdrive_link,
    ))
    report_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return report_id


def get_all_reports():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM reports ORDER BY run_date DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_report_by_id(report_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM reports WHERE id=?", (report_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_last_report_for_vendor(vendor_name: str):
    """Return the most recent diff_log entry for a vendor (used by diff engine)."""
    conn = get_connection()
    row = conn.execute("""
        SELECT dl.*, r.run_date as created_at
        FROM diff_log dl
        JOIN reports r ON dl.report_id = r.id
        WHERE dl.vendor_name = ?
        ORDER BY r.run_date DESC
        LIMIT 1
    """, (vendor_name,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Diff log ───────────────────────────────────────────────────────────────────

def save_diff_log(report_id, vendor_name, previous_snapshot, new_snapshot, delta_summary):
    conn = get_connection()
    conn.execute("""
        INSERT INTO diff_log (report_id, vendor_name, previous_snapshot, new_snapshot, delta_summary)
        VALUES (?, ?, ?, ?, ?)
    """, (report_id, vendor_name, previous_snapshot, new_snapshot, delta_summary))
    conn.commit()
    conn.close()
