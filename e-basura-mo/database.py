"""SQLite database layer for E-Basura Mo."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from auth import hash_password
from config import DB_PATH, PHOTOS_DIR, REPORTS_DIR


class DatabaseError(Exception):
    pass


class Database:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DB_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        self._seed_defaults()

    @staticmethod
    def clear_all_data(include_demo_accounts: bool = True) -> None:
        """Delete database, photos, and saved print files. Rebuilds fresh DB on next start."""
        for path in (DB_PATH, Path(str(DB_PATH) + "-journal"), Path(str(DB_PATH) + "-wal")):
            if path.exists():
                path.unlink()

        if PHOTOS_DIR.exists():
            for file in PHOTOS_DIR.iterdir():
                if file.is_file():
                    file.unlink()

        if REPORTS_DIR.exists():
            for file in REPORTS_DIR.glob("*.html"):
                file.unlink()

        if include_demo_accounts:
            Database()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('Admin','Staff','Captain','Viewer')),
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS residents (
                    resident_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    zone TEXT NOT NULL,
                    contact_number TEXT DEFAULT '',
                    registered_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS crew (
                    crew_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    contact_number TEXT DEFAULT '',
                    is_active INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS reports (
                    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resident_id INTEGER NOT NULL,
                    report_type TEXT NOT NULL,
                    location_description TEXT NOT NULL,
                    description TEXT NOT NULL,
                    photo_path TEXT,
                    status TEXT NOT NULL DEFAULT 'Pending',
                    date_submitted TEXT NOT NULL,
                    date_resolved TEXT,
                    assigned_crew_id INTEGER,
                    resolution_notes TEXT DEFAULT '',
                    FOREIGN KEY (resident_id) REFERENCES residents(resident_id),
                    FOREIGN KEY (assigned_crew_id) REFERENCES crew(crew_id)
                );

                CREATE TABLE IF NOT EXISTS pickup_requests (
                    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resident_id INTEGER NOT NULL,
                    waste_type TEXT NOT NULL,
                    scheduled_date TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Pending',
                    date_requested TEXT NOT NULL,
                    assigned_crew_id INTEGER,
                    notes TEXT DEFAULT '',
                    FOREIGN KEY (resident_id) REFERENCES residents(resident_id),
                    FOREIGN KEY (assigned_crew_id) REFERENCES crew(crew_id)
                );

                CREATE TABLE IF NOT EXISTS announcements (
                    announcement_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    date_posted TEXT NOT NULL,
                    posted_by INTEGER NOT NULL,
                    FOREIGN KEY (posted_by) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS assignment_log (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id INTEGER NOT NULL,
                    crew_id INTEGER NOT NULL,
                    assigned_at TEXT NOT NULL,
                    completed_at TEXT,
                    FOREIGN KEY (report_id) REFERENCES reports(report_id),
                    FOREIGN KEY (crew_id) REFERENCES crew(crew_id)
                );

                CREATE TABLE IF NOT EXISTS collection_schedule (
                    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    zone TEXT NOT NULL,
                    day_of_week TEXT NOT NULL,
                    time_slot TEXT NOT NULL,
                    notes TEXT DEFAULT ''
                );

                CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
                CREATE INDEX IF NOT EXISTS idx_reports_date ON reports(date_submitted);
                CREATE INDEX IF NOT EXISTS idx_residents_zone ON residents(zone);
                CREATE INDEX IF NOT EXISTS idx_pickup_status ON pickup_requests(status);
                """
            )

    def _seed_defaults(self) -> None:
        with self._connect() as conn:
            if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
                now = _now()
                conn.execute(
                    """
                    INSERT INTO users (full_name, role, username, password_hash, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    ("Barangay Admin", "Admin", "admin", hash_password("admin123"), now),
                )
                conn.execute(
                    """
                    INSERT INTO users (full_name, role, username, password_hash, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    ("Barangay Secretary", "Staff", "staff", hash_password("staff123"), now),
                )
                conn.execute(
                    """
                    INSERT INTO users (full_name, role, username, password_hash, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    ("Barangay Captain", "Captain", "captain", hash_password("captain123"), now),
                )

            if conn.execute("SELECT COUNT(*) FROM crew").fetchone()[0] == 0:
                crew = [
                    ("Juan Dela Cruz", "09171234567"),
                    ("Maria Santos", "09189876543"),
                    ("Pedro Reyes", "09175551234"),
                ]
                for name, contact in crew:
                    conn.execute(
                        "INSERT INTO crew (full_name, contact_number, is_active) VALUES (?, ?, 1)",
                        (name, contact),
                    )

            if conn.execute("SELECT COUNT(*) FROM residents").fetchone()[0] == 0:
                now = _now()
                residents = [
                    ("Ana Reyes", "Barangay Poblacion", "09171112233"),
                    ("Ben Cruz", "Barangay San Roque", "09174445566"),
                    ("Carla Gomez", "Barangay Sta. Cruz", ""),
                ]
                for name, zone, contact in residents:
                    conn.execute(
                        "INSERT INTO residents (full_name, zone, contact_number, registered_at) VALUES (?, ?, ?, ?)",
                        (name, zone, contact, now),
                    )

            if conn.execute("SELECT COUNT(*) FROM collection_schedule").fetchone()[0] == 0:
                samples = [
                    ("Barangay Poblacion", "Monday", "6:00 AM – 10:00 AM"),
                    ("Barangay San Roque", "Wednesday", "6:00 AM – 10:00 AM"),
                    ("Barangay Sta. Cruz", "Friday", "6:00 AM – 10:00 AM"),
                ]
                for brgy, day, slot in samples:
                    conn.execute(
                        """
                        INSERT INTO collection_schedule (zone, day_of_week, time_slot, notes)
                        VALUES (?, ?, ?, ?)
                        """,
                        (brgy, day, slot, "Regular garbage collection"),
                    )

    # ── Users ──────────────────────────────────────────────────────────

    def authenticate(self, username: str, password: str) -> dict | None:
        from auth import verify_password

        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username.strip(),)
            ).fetchone()
            if row and verify_password(password, row["password_hash"]):
                return dict(row)
        return None

    # ── Residents ──────────────────────────────────────────────────────

    def create_resident(self, data: dict) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO residents (full_name, zone, contact_number, registered_at)
                VALUES (?, ?, ?, ?)
                """,
                (data["full_name"], data["zone"], data.get("contact_number", ""), _now()),
            )
            return int(cur.lastrowid)

    def search_residents(self, query: str = "") -> list[dict]:
        sql = "SELECT * FROM residents WHERE 1=1"
        params: list[Any] = []
        if query.strip():
            sql += " AND (full_name LIKE ? OR zone LIKE ? OR contact_number LIKE ?)"
            t = f"%{query.strip()}%"
            params = [t, t, t]
        sql += " ORDER BY full_name COLLATE NOCASE"
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(sql, params)]

    def get_resident(self, resident_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM residents WHERE resident_id = ?", (resident_id,)).fetchone()
            return dict(row) if row else None

    def update_resident(self, resident_id: int, data: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE residents SET full_name=?, zone=?, contact_number=?
                WHERE resident_id=?
                """,
                (data["full_name"], data["zone"], data.get("contact_number", ""), resident_id),
            )

    def resident_record_count(self, resident_id: int) -> int:
        with self._connect() as conn:
            reports = conn.execute(
                "SELECT COUNT(*) FROM reports WHERE resident_id=?", (resident_id,)
            ).fetchone()[0]
            pickups = conn.execute(
                "SELECT COUNT(*) FROM pickup_requests WHERE resident_id=?", (resident_id,)
            ).fetchone()[0]
            return int(reports) + int(pickups)

    def delete_resident(self, resident_id: int) -> None:
        linked = self.resident_record_count(resident_id)
        if linked > 0:
            raise DatabaseError(
                f"Cannot delete: this resident has {linked} report(s) or pickup request(s). "
                "Remove or reassign those records first."
            )
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM residents WHERE resident_id=?", (resident_id,))
            if cur.rowcount == 0:
                raise DatabaseError("Resident not found.")

    # ── Crew ───────────────────────────────────────────────────────────

    def get_crew(self, active_only: bool = True) -> list[dict]:
        sql = "SELECT * FROM crew"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY full_name"
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(sql)]

    def save_crew(self, data: dict, crew_id: int | None = None) -> int:
        with self._connect() as conn:
            if crew_id:
                conn.execute(
                    """
                    UPDATE crew SET full_name=?, contact_number=?, is_active=?
                    WHERE crew_id=?
                    """,
                    (data["full_name"], data["contact_number"], int(data["is_active"]), crew_id),
                )
                return crew_id
            cur = conn.execute(
                "INSERT INTO crew (full_name, contact_number, is_active) VALUES (?, ?, ?)",
                (data["full_name"], data["contact_number"], int(data["is_active"])),
            )
            return int(cur.lastrowid)

    def delete_crew(self, crew_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM assignment_log WHERE crew_id=?", (crew_id,))
            conn.execute(
                "UPDATE reports SET assigned_crew_id=NULL WHERE assigned_crew_id=?", (crew_id,)
            )
            conn.execute(
                "UPDATE pickup_requests SET assigned_crew_id=NULL WHERE assigned_crew_id=?",
                (crew_id,),
            )
            cur = conn.execute("DELETE FROM crew WHERE crew_id=?", (crew_id,))
            if cur.rowcount == 0:
                raise DatabaseError("Crew member not found.")

    # ── Reports ────────────────────────────────────────────────────────

    def create_report(self, data: dict) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO reports
                (resident_id, report_type, location_description, description,
                 photo_path, status, date_submitted, resolution_notes)
                VALUES (?, ?, ?, ?, ?, 'Pending', ?, '')
                """,
                (
                    data["resident_id"],
                    data["report_type"],
                    data["location_description"],
                    data["description"],
                    data.get("photo_path"),
                    _now(),
                ),
            )
            return int(cur.lastrowid)

    def update_report(self, report_id: int, data: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE reports SET
                    report_type=?, location_description=?, description=?,
                    photo_path=?, resolution_notes=?
                WHERE report_id=?
                """,
                (
                    data["report_type"],
                    data["location_description"],
                    data["description"],
                    data.get("photo_path"),
                    data.get("resolution_notes", ""),
                    report_id,
                ),
            )

    def assign_report(self, report_id: int, crew_id: int) -> None:
        now = _now()
        with self._connect() as conn:
            conn.execute(
                "UPDATE reports SET status='Assigned', assigned_crew_id=? WHERE report_id=?",
                (crew_id, report_id),
            )
            conn.execute(
                """
                INSERT INTO assignment_log (report_id, crew_id, assigned_at)
                VALUES (?, ?, ?)
                """,
                (report_id, crew_id, now),
            )

    def resolve_report(self, report_id: int, notes: str = "") -> None:
        now = _now()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE reports SET status='Resolved', date_resolved=?, resolution_notes=?
                WHERE report_id=?
                """,
                (now, notes, report_id),
            )
            conn.execute(
                """
                UPDATE assignment_log SET completed_at=?
                WHERE report_id=? AND completed_at IS NULL
                """,
                (now, report_id),
            )

    def delete_report(self, report_id: int) -> bool:
        with self._connect() as conn:
            # Delete child rows first (FK: assignment_log -> reports)
            conn.execute("DELETE FROM assignment_log WHERE report_id=?", (report_id,))
            cur = conn.execute("DELETE FROM reports WHERE report_id=?", (report_id,))
            return cur.rowcount > 0

    def search_reports(
        self,
        query: str = "",
        status: str = "",
        zone: str = "",
        date_from: str = "",
        date_to: str = "",
        report_type: str = "",
    ) -> list[dict]:
        sql = """
            SELECT r.*, res.full_name AS resident_name, res.zone,
                   c.full_name AS crew_name
            FROM reports r
            JOIN residents res ON r.resident_id = res.resident_id
            LEFT JOIN crew c ON r.assigned_crew_id = c.crew_id
            WHERE 1=1
        """
        params: list[Any] = []
        if query.strip():
            sql += " AND (res.full_name LIKE ? OR r.location_description LIKE ? OR r.description LIKE ?)"
            t = f"%{query.strip()}%"
            params.extend([t, t, t])
        if status and status != "All":
            sql += " AND r.status = ?"
            params.append(status)
        if zone and zone.strip():
            sql += " AND res.zone LIKE ?"
            params.append(f"%{zone.strip()}%")
        if report_type and report_type != "All Types":
            sql += " AND r.report_type = ?"
            params.append(report_type)
        if date_from:
            sql += " AND date(r.date_submitted) >= date(?)"
            params.append(date_from)
        if date_to:
            sql += " AND date(r.date_submitted) <= date(?)"
            params.append(date_to)
        sql += " ORDER BY r.date_submitted DESC"
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(sql, params)]

    def get_report(self, report_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT r.*, res.full_name AS resident_name, res.zone,
                       c.full_name AS crew_name
                FROM reports r
                JOIN residents res ON r.resident_id = res.resident_id
                LEFT JOIN crew c ON r.assigned_crew_id = c.crew_id
                WHERE r.report_id = ?
                """,
                (report_id,),
            ).fetchone()
            return dict(row) if row else None

    # ── Pickup requests ────────────────────────────────────────────────

    def create_pickup(self, data: dict) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO pickup_requests
                (resident_id, waste_type, scheduled_date, status, date_requested, notes)
                VALUES (?, ?, ?, 'Pending', ?, ?)
                """,
                (
                    data["resident_id"],
                    data["waste_type"],
                    data["scheduled_date"],
                    _now(),
                    data.get("notes", ""),
                ),
            )
            return int(cur.lastrowid)

    def assign_pickup(self, request_id: int, crew_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE pickup_requests SET status='Assigned', assigned_crew_id=? WHERE request_id=?",
                (crew_id, request_id),
            )

    def complete_pickup(self, request_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE pickup_requests SET status='Completed' WHERE request_id=?",
                (request_id,),
            )

    def search_pickups(
        self, query: str = "", status: str = "", zone: str = ""
    ) -> list[dict]:
        sql = """
            SELECT p.*, res.full_name AS resident_name, res.zone,
                   c.full_name AS crew_name
            FROM pickup_requests p
            JOIN residents res ON p.resident_id = res.resident_id
            LEFT JOIN crew c ON p.assigned_crew_id = c.crew_id
            WHERE 1=1
        """
        params: list[Any] = []
        if query.strip():
            sql += " AND (res.full_name LIKE ? OR p.waste_type LIKE ?)"
            t = f"%{query.strip()}%"
            params.extend([t, t])
        if status and status != "All":
            sql += " AND p.status = ?"
            params.append(status)
        if zone and zone.strip():
            sql += " AND res.zone LIKE ?"
            params.append(f"%{zone.strip()}%")
        sql += " ORDER BY p.date_requested DESC"
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(sql, params)]

    # ── Announcements ──────────────────────────────────────────────────

    def create_announcement(self, title: str, message: str, user_id: int) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO announcements (title, message, date_posted, posted_by)
                VALUES (?, ?, ?, ?)
                """,
                (title, message, _now(), user_id),
            )
            return int(cur.lastrowid)

    def get_announcements(self, limit: int = 50) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT a.*, u.full_name AS posted_by_name
                FROM announcements a
                JOIN users u ON a.posted_by = u.user_id
                ORDER BY a.date_posted DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_announcement(self, announcement_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM announcements WHERE announcement_id=?", (announcement_id,))

    # ── Schedule ───────────────────────────────────────────────────────

    def get_schedule(self, zone: str = "") -> list[dict]:
        sql = "SELECT * FROM collection_schedule"
        params: list[Any] = []
        if zone:
            sql += " WHERE zone = ?"
            params.append(zone)
        sql += " ORDER BY zone, day_of_week"
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(sql, params)]

    def save_schedule(self, data: dict, schedule_id: int | None = None) -> int:
        with self._connect() as conn:
            if schedule_id:
                conn.execute(
                    """
                    UPDATE collection_schedule SET zone=?, day_of_week=?, time_slot=?, notes=?
                    WHERE schedule_id=?
                    """,
                    (data["zone"], data["day_of_week"], data["time_slot"], data["notes"], schedule_id),
                )
                return schedule_id
            cur = conn.execute(
                """
                INSERT INTO collection_schedule (zone, day_of_week, time_slot, notes)
                VALUES (?, ?, ?, ?)
                """,
                (data["zone"], data["day_of_week"], data["time_slot"], data.get("notes", "")),
            )
            return int(cur.lastrowid)

    def get_schedule_entry(self, schedule_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM collection_schedule WHERE schedule_id=?", (schedule_id,)
            ).fetchone()
            return dict(row) if row else None

    def delete_schedule(self, schedule_id: int) -> None:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM collection_schedule WHERE schedule_id=?", (schedule_id,)
            )
            if cur.rowcount == 0:
                raise DatabaseError("Schedule entry not found.")

    # ── Dashboard stats ────────────────────────────────────────────────

    def get_dashboard_stats(self) -> dict:
        with self._connect() as conn:
            reports = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status='Pending' THEN 1 ELSE 0 END) AS pending,
                    SUM(CASE WHEN status='Assigned' THEN 1 ELSE 0 END) AS assigned,
                    SUM(CASE WHEN status='Resolved' THEN 1 ELSE 0 END) AS resolved
                FROM reports
                """
            ).fetchone()
            pickups = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status='Pending' THEN 1 ELSE 0 END) AS pending
                FROM pickup_requests
                """
            ).fetchone()
            return {
                "reports_total": reports["total"] or 0,
                "reports_pending": reports["pending"] or 0,
                "reports_assigned": reports["assigned"] or 0,
                "reports_resolved": reports["resolved"] or 0,
                "pickups_total": pickups["total"] or 0,
                "pickups_pending": pickups["pending"] or 0,
            }

    def get_report_type_counts(self, days: int = 30) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT report_type, COUNT(*) AS count
                FROM reports
                WHERE date(date_submitted) >= date('now', ?)
                GROUP BY report_type
                ORDER BY count DESC
                """,
                (f"-{days} days",),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_zone_counts(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT res.zone, COUNT(*) AS count
                FROM reports r
                JOIN residents res ON r.resident_id = res.resident_id
                WHERE r.status != 'Resolved'
                GROUP BY res.zone
                ORDER BY count DESC
                """
            ).fetchall()
            return [dict(r) for r in rows]

    def get_todays_assigned_reports(self) -> list[dict]:
        return self.search_reports(status="Assigned")

    def get_todays_assigned_pickups(self) -> list[dict]:
        return self.search_pickups(status="Assigned")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
