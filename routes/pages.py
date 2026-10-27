"""HTML pages. They are only shells: the data is loaded by JavaScript from the /api/... routes."""
from flask import Blueprint, render_template, redirect, url_for
from utils import current_user, page_login_required, page_admin_required

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def index():
    return render_template("index.html")


@pages_bp.route("/movie/<int:movie_id>")
def movie(movie_id):
    return render_template("movie.html", movie_id=movie_id)


@pages_bp.route("/book/<int:showtime_id>")
@page_login_required
def book(showtime_id):
    return render_template("book.html", showtime_id=showtime_id)


@pages_bp.route("/booking/<int:booking_id>")
@page_login_required
def booking(booking_id):
    return render_template("booking.html", booking_id=booking_id)


@pages_bp.route("/my-bookings")
@page_login_required
def my_bookings():
    return render_template("my_bookings.html")


@pages_bp.route("/login")
def login():
    if current_user():
        return redirect(url_for("pages.index"))
    return render_template("login.html")


@pages_bp.route("/register")
def register():
    if current_user():
        return redirect(url_for("pages.index"))
    return render_template("register.html")


@pages_bp.route("/admin")
@page_admin_required
def admin():
    return render_template("admin.html")
