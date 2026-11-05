"""HTML pages. The pages are mostly empty shells; JavaScript loads the data from the JSON API."""
from flask import Blueprint, abort, redirect, render_template, url_for

from extensions import db
from models import Booking, Movie, Showtime
from utils import current_user, page_admin_required, page_login_required

bp = Blueprint("pages", __name__)


@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/login")
def login():
    if current_user():
        return redirect(url_for("theater_search.theaters_page"))
    return render_template("login.html")


@bp.get("/register")
def register():
    if current_user():
        return redirect(url_for("theater_search.theaters_page"))
    return render_template("register.html")


@bp.get("/movie/<int:movie_id>")
def movie_page(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie or not movie.is_active:
        abort(404)
    return render_template("movie.html", movie=movie.to_dict())


@bp.get("/book/<int:showtime_id>")
@page_login_required
def book(showtime_id):
    if not db.session.get(Showtime, showtime_id):
        abort(404)
    return render_template("book.html", showtime_id=showtime_id)


@bp.get("/booking/<reference>")
@page_login_required
def booking_page(reference):
    booking = Booking.query.filter_by(reference=reference).first_or_404()
    user = current_user()
    if booking.user_id != user.id and not user.is_admin:
        abort(403)
    return render_template("booking.html", b=booking.to_dict())


@bp.get("/my-bookings")
@page_login_required
def my_bookings():
    return render_template("my_bookings.html")


@bp.get("/admin")
@page_admin_required
def admin():
    return render_template("admin.html")
