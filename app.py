"""
app.py - Flask front end for the Photographer Booking Website.

Run with:
    python app.py
Then open http://127.0.0.1:5000
Admin dashboard: http://127.0.0.1:5000/admin/login  (password: darkroom123)
"""

from datetime import date, datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, flash, session, abort
)

import database as db

app = Flask(__name__)
app.secret_key = "replace-this-with-a-real-secret-key-in-production"

ADMIN_PASSWORD = "darkroom123"


with app.app_context():
    db.init_db()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Please log in to access the studio dashboard.", "error")
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def parse_date(value):
    """Turn an <input type=date> string into a datetime.date (DB-API type)."""
    return datetime.strptime(value, "%Y-%m-%d").date()


@app.context_processor
def inject_globals():
    return {"current_year": date.today().year}


# ---------------------------------------------------------------------------
# Public site
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    featured = db.list_gallery()[:6]
    services = db.list_services()[:3]
    return render_template("index.html", featured=featured, services=services)


@app.route("/gallery")
def gallery():
    category = request.args.get("category", "All")
    items = db.list_gallery(category)
    categories = ["All"] + db.list_categories()
    return render_template(
        "gallery.html", items=items, categories=categories, active_category=category
    )


@app.route("/services")
def services():
    all_services = db.list_services()
    return render_template("services.html", services=all_services)


@app.route("/book", methods=["GET", "POST"])
def book():
    all_services = db.list_services()
    preselect = request.args.get("service_id", type=int)

    if request.method == "POST":
        client_name = request.form.get("client_name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        service_id = request.form.get("service_id", type=int)
        shoot_date_raw = request.form.get("shoot_date", "").strip()
        location = request.form.get("location", "").strip()
        message = request.form.get("message", "").strip()

        errors = []
        if not client_name:
            errors.append("Please tell us your name.")
        if not email or "@" not in email:
            errors.append("Please enter a valid email address.")
        if not phone:
            errors.append("Please enter a contact phone number.")
        if not service_id or not db.get_service(service_id):
            errors.append("Please choose a valid session type.")
        if not location:
            errors.append("Please tell us the shoot location or venue.")

        shoot_date = None
        if not shoot_date_raw:
            errors.append("Please choose a preferred date.")
        else:
            try:
                shoot_date = parse_date(shoot_date_raw)
                if shoot_date < date.today():
                    errors.append("The shoot date can't be in the past.")
            except ValueError:
                errors.append("That date doesn't look right — please use the date picker.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "booking.html", services=all_services, preselect=service_id, form=request.form
            )

        booking_id = db.create_booking(
            client_name, email, phone, service_id, shoot_date, location, message
        )
        flash("Your booking request was sent — we'll confirm by email shortly.", "success")
        return redirect(url_for("booking_success", booking_id=booking_id))

    return render_template("booking.html", services=all_services, preselect=preselect, form={})


@app.route("/booking/success/<int:booking_id>")
def booking_success(booking_id):
    booking = db.get_booking(booking_id)
    if not booking:
        abort(404)
    return render_template("booking_success.html", booking=booking)


# ---------------------------------------------------------------------------
# Admin: auth
# ---------------------------------------------------------------------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            session["is_admin"] = True
            flash("Welcome back.", "success")
            next_url = request.args.get("next") or url_for("admin_dashboard")
            return redirect(next_url)
        flash("Incorrect password.", "error")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    flash("Logged out.", "success")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Admin: dashboard
# ---------------------------------------------------------------------------
@app.route("/admin")
@admin_required
def admin_dashboard():
    counts = db.booking_counts()
    recent = db.list_bookings()[:5]
    return render_template("admin_dashboard.html", counts=counts, recent=recent)


# ---------------------------------------------------------------------------
# Admin: bookings CRUD (Read / Update / Delete — Create happens on public /book)
# ---------------------------------------------------------------------------
@app.route("/admin/bookings")
@admin_required
def admin_bookings():
    status = request.args.get("status", "All")
    bookings = db.list_bookings(status)
    return render_template("admin_bookings.html", bookings=bookings, active_status=status)


@app.route("/admin/bookings/<int:booking_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_booking(booking_id):
    booking = db.get_booking(booking_id)
    if not booking:
        abort(404)
    all_services = db.list_services()

    if request.method == "POST":
        client_name = request.form.get("client_name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        service_id = request.form.get("service_id", type=int)
        shoot_date_raw = request.form.get("shoot_date", "").strip()
        location = request.form.get("location", "").strip()
        message = request.form.get("message", "").strip()
        status = request.form.get("status", "Pending")

        errors = []
        if not client_name or not email or not phone or not location:
            errors.append("All contact fields are required.")
        try:
            shoot_date = parse_date(shoot_date_raw)
        except ValueError:
            errors.append("That date doesn't look right.")
            shoot_date = None

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("admin_edit_booking.html", booking=booking, services=all_services)

        db.update_booking(
            booking_id, client_name, email, phone, service_id, shoot_date, location, message, status
        )
        flash(f"Booking #{booking_id} updated.", "success")
        return redirect(url_for("admin_bookings"))

    return render_template("admin_edit_booking.html", booking=booking, services=all_services)


@app.route("/admin/bookings/<int:booking_id>/status/<new_status>", methods=["POST"])
@admin_required
def admin_set_status(booking_id, new_status):
    if new_status not in {"Pending", "Confirmed", "Completed", "Cancelled"}:
        abort(400)
    ok = db.update_booking_status(booking_id, new_status)
    if ok:
        flash(f"Booking #{booking_id} marked {new_status}.", "success")
    else:
        flash("Booking not found.", "error")
    return redirect(request.referrer or url_for("admin_bookings"))


@app.route("/admin/bookings/<int:booking_id>/delete", methods=["POST"])
@admin_required
def admin_delete_booking(booking_id):
    ok = db.delete_booking(booking_id)
    if ok:
        flash(f"Booking #{booking_id} deleted.", "success")
    else:
        flash("Booking not found.", "error")
    return redirect(url_for("admin_bookings"))


# ---------------------------------------------------------------------------
# Admin: gallery CRUD (Create / Read / Delete)
# ---------------------------------------------------------------------------
@app.route("/admin/gallery")
@admin_required
def admin_gallery():
    items = db.list_gallery()
    return render_template("admin_gallery.html", items=items)


@app.route("/admin/gallery/add", methods=["GET", "POST"])
@admin_required
def admin_add_gallery():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        image_file = request.form.get("image_file", "").strip()
        description = request.form.get("description", "").strip()

        errors = []
        if not title:
            errors.append("Please give the piece a title.")
        if not category:
            errors.append("Please choose a category.")
        if not image_file:
            errors.append("Please choose an image file from static/images/gallery.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("admin_add_gallery.html", form=request.form)

        db.add_gallery_item(title, category, image_file, description)
        flash("Portfolio piece added.", "success")
        return redirect(url_for("admin_gallery"))

    return render_template("admin_add_gallery.html", form={})


@app.route("/admin/gallery/<int:item_id>/delete", methods=["POST"])
@admin_required
def admin_delete_gallery(item_id):
    ok = db.delete_gallery_item(item_id)
    if ok:
        flash("Portfolio piece removed.", "success")
    else:
        flash("Item not found.", "error")
    return redirect(url_for("admin_gallery"))


if __name__ == "__main__":
    app.run(debug=True)
