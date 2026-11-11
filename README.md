# KuttyStories — Kerala Photographer Booking Website

A Flask + SQLite web application built for the **Python DB-API practical
assignment**. It's a working photographer's portfolio and booking site:
visitors browse the photo gallery, view session pricing, and submit a
booking request; the photographer manages bookings and the portfolio from
a password-protected dashboard.

## How this maps to the assignment requirements

| # | Requirement | Where it lives |
|---|---|---|
| 1 | Create/manage a database with a Python adapter | `database.py` — built-in `sqlite3` module, tables created in `init_db()` |
| 2 | Connection object | `database.get_connection()` — a DB-API `Connection`, opened fresh per request and always closed |
| 3 | Cursor objects execute SQL | every function in `database.py` does `cur = conn.cursor()` then `cur.execute(...)` |
| 4 | CRUD operations | **Bookings**: Create (`create_booking`), Read (`list_bookings`, `get_booking`), Update (`update_booking`, `update_booking_status`), Delete (`delete_booking`). **Gallery**: Create/Read/Delete (`add_gallery_item`, `list_gallery`, `delete_gallery_item`). **Services**: Read (seeded reference data) |
| 5 | Parameterized queries + type objects | every query uses `?` placeholders (never string-formatted SQL); `sqlite3.register_adapter`/`register_converter` register Python `date`/`datetime` as DB-API type constructors for the `DATE`/`TIMESTAMP` columns |
| 6 | Transactions + cleanup | every write calls `conn.commit()` (with `conn.rollback()` on `sqlite3.Error`), and every function closes its cursor and connection in a `finally` block |
| 7 | Web client | Flask app (`app.py`) with a full Jinja2 template front end (`templates/`) |
| 8 | Success/error messages | Flask `flash()` messages shown on every create/update/delete action, plus inline form validation errors |

## Project structure

```
photobooking/
├── app.py                 # Flask routes (public site + admin dashboard)
├── database.py             # All DB-API 2.0 / sqlite3 code (schema + CRUD)
├── generate_images.py      # One-off script used to generate the demo portfolio images
├── requirements.txt
├── static/
│   ├── css/style.css
│   └── images/
│       ├── hero.jpg
│       └── gallery/frame-001.jpg ... frame-012.jpg
└── templates/
    ├── base.html, index.html, gallery.html, services.html,
    │   booking.html, booking_success.html
    └── admin_login.html, admin_base.html, admin_dashboard.html,
        admin_bookings.html, admin_edit_booking.html,
        admin_gallery.html, admin_add_gallery.html
```

## Running it

```bash
cd photobooking
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000**.

The SQLite database file `photographer.db` is created automatically the
first time the app runs, with a `services` table and 12 seeded gallery
photos already in place — nothing else to set up.

## Using the site

**Public site**
- `/` — home page
- `/gallery` — full portfolio, filterable by category
- `/services` — session types and pricing
- `/book` — booking request form (writes a row to `bookings`)

**Studio dashboard** (admin)
- `/admin/login` — password: `darkroom123`
- `/admin` — overview with booking counts
- `/admin/bookings` — list, filter, edit, confirm, or delete bookings
- `/admin/gallery` — add or remove portfolio photographs

> This is a demo app: the admin password is hardcoded in `app.py`
> (`ADMIN_PASSWORD`) and the Flask `secret_key` is a placeholder. Replace
> both, and add proper user auth and HTTPS, before deploying for real.

## About the portfolio images

Real client photographs obviously aren't available in this environment,
so the twelve gallery images were generated as abstract, moody gradient
studies (`generate_images.py`, using Pillow) tagged like film negatives —
they stand in for real photography so the CRUD and gallery-browsing flow
can be demonstrated end to end. To use real photos: drop `.jpg`/`.png`
files into `static/images/gallery/`, then add them through
**Studio dashboard → Portfolio → Add a photograph** (or insert rows
directly into the `gallery` table).

## Notes on the DB-API usage

- `sqlite3.connect(..., detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)`
  is used so SQLite's declared `DATE` / `TIMESTAMP` column types round-trip
  to real Python `datetime.date` / `datetime.datetime` objects.
- `sqlite3.register_adapter()` / `register_converter()` are the DB-API's
  type-object mechanism in the `sqlite3` module (the equivalent of
  `Date()`/`Timestamp()` constructors in adapters like `psycopg2`).
- `conn.row_factory = sqlite3.Row` lets query results be accessed like
  dictionaries in the templates (`row["client_name"]`) while still being
  real DB-API cursor rows.
- Foreign keys are enforced (`PRAGMA foreign_keys = ON`) — the `bookings`
  table references `services.id`.
