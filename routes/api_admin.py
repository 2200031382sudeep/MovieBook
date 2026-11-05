"""JSON API for the admin panel (movies, theaters, showtimes, bookings)."""
import re
from datetime import datetime
from decimal import Decimal

from flask import Blueprint, jsonify, request

from extensions import db
from models import Booking, Movie, Showtime, Theater
from utils import api_admin_required

bp = Blueprint("admin_api", __name__, url_prefix="/api/admin")


class Bad(Exception):
    """A problem with what the admin typed (sent back as a 400 error)."""


@bp.errorhandler(Bad)
def _bad_input(exc):
    return jsonify(error=str(exc)), 400


def body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def label(key):
    return key.replace("_", " ").capitalize()


def text(data, key, max_len, required=False):
    value = data.get(key)
    value = "" if value is None else str(value).strip()
    if required and not value:
        raise Bad(f"{label(key)} is required.")
    if len(value) > max_len:
        raise Bad(f"{label(key)} is too long (max {max_len} characters).")
    return value


def number(data, key, lo, hi, cast=int, default=None):
    raw = data.get(key)
    if raw is None or str(raw).strip() == "":
        if default is None:
            raise Bad(f"{label(key)} is required.")
        return default
    try:
        value = cast(str(raw).strip())
        if not (lo <= value <= hi):
            raise ValueError
    except (ValueError, TypeError, ArithmeticError):
        raise Bad(f"{label(key)} must be a number between {lo} and {hi}.")
    return value


def has_bookings_for(**filters):
    q = db.session.query(Booking.id).join(Showtime, Showtime.id == Booking.showtime_id)
    if "movie_id" in filters:
        q = q.filter(Showtime.movie_id == filters["movie_id"])
    if "theater_id" in filters:
        q = q.filter(Showtime.theater_id == filters["theater_id"])
    if "showtime_id" in filters:
        q = q.filter(Booking.showtime_id == filters["showtime_id"])
    return q.first() is not None


# ---------------------------------------------------------------- movies
def movie_values(data):
    poster = text(data, "poster_url", 255)
    if poster and not re.match(r"https?://", poster, re.I):
        raise Bad("Poster URL must start with http:// or https://")
    return dict(
        title=text(data, "title", 150, required=True),
        description=text(data, "description", 5000),
        genre=text(data, "genre", 80),
        language=text(data, "language", 50),
        duration_min=number(data, "duration_min", 1, 600, int, 120),
        rating=number(data, "rating", 0, 10, float, 0.0),
        poster_url=poster,
    )


@bp.get("/movies")
@api_admin_required
def list_movies():
    items = Movie.query.order_by(Movie.title).all()
    return jsonify(movies=[m.to_dict() for m in items])


@bp.post("/movies")
@api_admin_required
def add_movie():
    movie = Movie(is_active=True, **movie_values(body()))
    db.session.add(movie)
    db.session.commit()
    return jsonify(movie=movie.to_dict()), 201


@bp.patch("/movies/<int:movie_id>")
@api_admin_required
def edit_movie(movie_id):
    movie = db.get_or_404(Movie, movie_id)
    data = body()
    if set(data) == {"is_active"}:
        movie.is_active = bool(data["is_active"])
    else:
        for key, value in movie_values(data).items():
            setattr(movie, key, value)
    db.session.commit()
    return jsonify(movie=movie.to_dict())


@bp.delete("/movies/<int:movie_id>")
@api_admin_required
def delete_movie(movie_id):
    movie = db.get_or_404(Movie, movie_id)
    if has_bookings_for(movie_id=movie.id):
        return jsonify(error="This movie has bookings. Untick 'Active' to hide it instead."), 409
    db.session.delete(movie)
    db.session.commit()
    return jsonify(ok=True)


# ---------------------------------------------------------------- theaters
@bp.get("/theaters")
@api_admin_required
def list_theaters():
    items = Theater.query.order_by(Theater.city, Theater.name).all()
    return jsonify(theaters=[t.to_dict() for t in items])


@bp.post("/theaters")
@api_admin_required
def add_theater():
    data = body()
    theater = Theater(
        name=text(data, "name", 120, required=True),
        city=text(data, "city", 80, required=True),
        location=text(data, "location", 200, required=True),
        rows=number(data, "rows", 1, 26, int, 8),
        seats_per_row=number(data, "seats_per_row", 1, 30, int, 10),
    )
    db.session.add(theater)
    db.session.commit()
    return jsonify(theater=theater.to_dict()), 201


@bp.delete("/theaters/<int:theater_id>")
@api_admin_required
def delete_theater(theater_id):
    theater = db.get_or_404(Theater, theater_id)
    if has_bookings_for(theater_id=theater.id):
        return jsonify(error="This theater has bookings, so it can't be deleted."), 409
    db.session.delete(theater)
    db.session.commit()
    return jsonify(ok=True)


# ---------------------------------------------------------------- showtimes
@bp.get("/showtimes")
@api_admin_required
def list_showtimes():
    rows = (db.session.query(Showtime, Movie, Theater)
            .join(Movie, Movie.id == Showtime.movie_id)
            .join(Theater, Theater.id == Showtime.theater_id)
            .order_by(Showtime.start_time.desc()).limit(200).all())
    return jsonify(showtimes=[{
        "id": s.id, "movie_title": m.title, "theater_name": t.name, "theater_city": t.city,
        "start_time": s.start_time.isoformat(timespec="minutes"), "price": float(s.price),
    } for s, m, t in rows])


@bp.post("/showtimes")
@api_admin_required
def add_showtime():
    data = body()
    movie = db.session.get(Movie, number(data, "movie_id", 1, 10**9))
    theater = db.session.get(Theater, number(data, "theater_id", 1, 10**9))
    if not movie or not theater:
        raise Bad("Please choose a movie and a theater.")

    raw = text(data, "start_time", 30, required=True)
    try:
        start = datetime.fromisoformat(raw).replace(tzinfo=None)
    except ValueError:
        raise Bad("Invalid date and time.")
    if start <= datetime.now():
        raise Bad("The show time must be in the future.")

    price = number(data, "price", 1, 10000, Decimal).quantize(Decimal("0.01"))
    showtime = Showtime(movie_id=movie.id, theater_id=theater.id, start_time=start, price=price)
    db.session.add(showtime)
    db.session.commit()
    return jsonify(showtime=showtime.to_dict()), 201


@bp.delete("/showtimes/<int:showtime_id>")
@api_admin_required
def delete_showtime(showtime_id):
    showtime = db.get_or_404(Showtime, showtime_id)
    if has_bookings_for(showtime_id=showtime.id):
        return jsonify(error="This show has bookings, so it can't be deleted."), 409
    db.session.delete(showtime)
    db.session.commit()
    return jsonify(ok=True)


# ---------------------------------------------------------------- bookings
@bp.get("/bookings")
@api_admin_required
def list_bookings():
    items = Booking.query.order_by(Booking.created_at.desc()).limit(200).all()
    return jsonify(bookings=[b.to_dict() for b in items])
