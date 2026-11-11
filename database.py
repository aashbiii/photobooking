"""
database.py
-----------
All Python DB-API 2.0 (PEP 249) access lives here, using the built-in
`sqlite3` adapter.

DB-API concepts demonstrated in this file:
  * Connection objects       -> get_connection()
  * Cursor objects            -> conn.cursor()
  * Parameterized queries     -> "?" placeholders everywhere (never string
                                  formatting), which protects against SQL
                                  injection.
  * Type objects/constructors -> sqlite3.PARSE_DECLTYPES + explicit
                                  register_adapter()/register_converter()
                                  calls so Python `date` / `datetime`
                                  objects are converted to/from the SQL
                                  DATE / TIMESTAMP columns automatically
                                  (the DB-API's answer to Date(), Timestamp()
                                  constructors from other adapters such as
                                  psycopg2).
  * Transactions               -> conn.commit() / conn.rollback()
  * Resource cleanup           -> cursor.close() / conn.close() in `finally`
"""

import sqlite3
import os
from datetime import date, datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "photographer.db")

# ---------------------------------------------------------------------------
# DB-API type adapters / converters (Python <-> SQLite type objects)
# ---------------------------------------------------------------------------
sqlite3.register_adapter(date, lambda d: d.isoformat())
sqlite3.register_adapter(datetime, lambda dt: dt.isoformat(sep=" "))
sqlite3.register_converter("DATE", lambda b: date.fromisoformat(b.decode()))
sqlite3.register_converter(
    "TIMESTAMP", lambda b: datetime.fromisoformat(b.decode())
)


def get_connection():
    """Return a DB-API Connection object with foreign keys + type parsing on."""
    conn = sqlite3.connect(
        DB_PATH,
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------------------------------------------------------------------
# Schema + seed data
# ---------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS services (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    description TEXT NOT NULL,
    duration    TEXT NOT NULL,
    price       REAL NOT NULL,
    image_file  TEXT
);

CREATE TABLE IF NOT EXISTS gallery (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    category    TEXT NOT NULL,
    image_file  TEXT NOT NULL,
    description TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bookings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name   TEXT NOT NULL,
    email         TEXT NOT NULL,
    phone         TEXT NOT NULL,
    service_id    INTEGER NOT NULL,
    shoot_date    DATE NOT NULL,
    location      TEXT NOT NULL,
    message       TEXT,
    status        TEXT NOT NULL DEFAULT 'Pending',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_id) REFERENCES services (id) ON DELETE RESTRICT
);
"""

SERVICE_SEED = [
    ("Portrait Session", "A relaxed one-on-one, couple, or family portrait session on location across Kerala.", "1.5 hours", 15000.00, "frame-001.jpg"),
    ("Wedding Coverage", "Full-day candid & traditional Kerala wedding coverage from dawn rituals to the grand reception.", "8 hours", 125000.00, "frame-002.jpg"),
    ("Editorial / Cultural Branding", "Polished editorial and portfolio images for personal brands, classical artists, and creators.", "2 hours", 25000.00, "frame-006.jpg"),
    ("Event & Festival Coverage", "Cinematic candid coverage for family celebrations, temple festivals, and gatherings.", "3 hours", 35000.00, "frame-007.jpg"),
    ("Backwaters & Landscape Prints", "A custom scenic shoot across Alappuzha lagoons or Munnar, delivered as fine-art prints.", "Half day", 40000.00, "frame-003.jpg"),
]

GALLERY_SEED = [
    ("The Kasavu Bride", "Portrait", "frame-001.jpg", "Traditional Kerala bridal portrait draped in cream and gold kasavu."),
    ("A Kerala Wedding", "Wedding", "frame-002.jpg", "Bride and groom sharing a serene candid moment together."),
    ("Vembanad Houseboat", "Nature", "frame-003.jpg", "Traditional wooden kettuvallam gliding across the quiet Alappuzha backwaters."),
    ("Athirappilly Mist", "Nature", "frame-004.jpg", "Monsoon majesty cascading through the Chalakudy rainforest basin."),
    ("Munnar Tea Hills", "Nature", "frame-005.jpg", "Emerald rolling tea plantations under early morning mountain haze."),
    ("Grace of Mohiniyattam", "Editorial", "frame-006.jpg", "The dance of the enchantress — expressive eyes and mudras in kasavu attire."),
    ("Rhythm of Pooram", "Event", "frame-007.jpg", "Caparisoned elephants and soaring temple umbrellas at Arattupuzha Pooram."),
    ("Backwater Boatman", "Street", "frame-008.jpg", "A quiet morning punt through the palm-canopied canals of Kuttanad."),
    ("Cheena Vala at Dusk", "Nature", "frame-009.jpg", "Iconic Chinese fishing net silhouettes resting against a crimson Arabian Sea sunset."),
    ("Kathakali Expressions", "Editorial", "frame-010.jpg", "Intricate chutti make-up and intense navarasa expression of a Kathakali master."),
    ("The Great Snake Boat Race", "Event", "frame-011.jpg", "Oars cutting in synchronized fury at the legendary Vallam Kali boat race."),
    ("Flame of Theyyam", "Event", "frame-012.jpg", "The fierce spiritual dance and glowing embers of North Malabar Theyyam."),
]


def init_db():
    """Create tables if they don't exist yet and seed reference data once."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.executescript(SCHEMA)
        cur.execute("SELECT COUNT(*) AS n FROM services")
        if cur.fetchone()["n"] == 0:
            cur.executemany(
                "INSERT INTO services (name, description, duration, price, image_file) VALUES (?, ?, ?, ?, ?)",
                SERVICE_SEED,
            )
        cur.execute("SELECT COUNT(*) AS n FROM gallery")
        if cur.fetchone()["n"] == 0:
            cur.executemany(
                "INSERT INTO gallery (title, category, image_file, description) VALUES (?, ?, ?, ?)",
                GALLERY_SEED,
            )
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


# ---------------------------------------------------------------------------
# SERVICES  (Read is used by the public site; kept simple by design)
# ---------------------------------------------------------------------------
def list_services():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM services ORDER BY price ASC")
        return [dict(row) for row in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def get_service(service_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM services WHERE id = ?", (service_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        cur.close()
        conn.close()


# ---------------------------------------------------------------------------
# GALLERY  -  Create / Read / Delete
# ---------------------------------------------------------------------------
def list_gallery(category=None):
    conn = get_connection()
    cur = conn.cursor()
    try:
        if category and category != "All":
            cur.execute(
                "SELECT * FROM gallery WHERE category = ? ORDER BY id DESC", (category,)
            )
        else:
            cur.execute("SELECT * FROM gallery ORDER BY id DESC")
        return [dict(row) for row in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def list_categories():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT DISTINCT category FROM gallery ORDER BY category ASC")
        return [row["category"] for row in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def add_gallery_item(title, category, image_file, description):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO gallery (title, category, image_file, description) VALUES (?, ?, ?, ?)",
            (title, category, image_file, description),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def delete_gallery_item(item_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM gallery WHERE id = ?", (item_id,))
        conn.commit()
        return cur.rowcount > 0
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


# ---------------------------------------------------------------------------
# BOOKINGS  -  full Create / Read / Update / Delete
# ---------------------------------------------------------------------------
def create_booking(client_name, email, phone, service_id, shoot_date, location, message):
    """shoot_date is a datetime.date object -> exercises the DATE type adapter."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO bookings
               (client_name, email, phone, service_id, shoot_date, location, message, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (client_name, email, phone, service_id, shoot_date, location, message, "Pending"),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def list_bookings(status=None):
    conn = get_connection()
    cur = conn.cursor()
    try:
        query = """
            SELECT bookings.*, services.name AS service_name, services.price AS service_price
            FROM bookings
            JOIN services ON services.id = bookings.service_id
        """
        params = ()
        if status and status != "All":
            query += " WHERE bookings.status = ?"
            params = (status,)
        query += " ORDER BY bookings.created_at DESC"
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def get_booking(booking_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """SELECT bookings.*, services.name AS service_name, services.price AS service_price
               FROM bookings JOIN services ON services.id = bookings.service_id
               WHERE bookings.id = ?""",
            (booking_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        cur.close()
        conn.close()


def update_booking(booking_id, client_name, email, phone, service_id, shoot_date, location, message, status):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """UPDATE bookings
               SET client_name = ?, email = ?, phone = ?, service_id = ?,
                   shoot_date = ?, location = ?, message = ?, status = ?
               WHERE id = ?""",
            (client_name, email, phone, service_id, shoot_date, location, message, status, booking_id),
        )
        conn.commit()
        return cur.rowcount > 0
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def update_booking_status(booking_id, status):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE bookings SET status = ? WHERE id = ?", (status, booking_id))
        conn.commit()
        return cur.rowcount > 0
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def delete_booking(booking_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
        conn.commit()
        return cur.rowcount > 0
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def booking_counts():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT status, COUNT(*) AS n FROM bookings GROUP BY status")
        counts = {row["status"]: row["n"] for row in cur.fetchall()}
        cur.execute("SELECT COUNT(*) AS n FROM bookings")
        counts["Total"] = cur.fetchone()["n"]
        return counts
    finally:
        cur.close()
        conn.close()
