"""Admin JSON API: manage movies, theaters, showtimes (with ticket prices) and see bookings."""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from flask import Blueprint, request, jsonify
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from extensions import db
from models import Movie, Theater, Showtime, Booking, BookingSeat
from utils import current_user

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.before_request
def guard():
    """Every route in this file is for admins only."""
    user = current_user()
    if not user:
        return jsonify(error="Please log in first."), 401
    if not user.is_admin:
        return jsonify(error="Admins only."), 403


# ---------- small validation helpers (they raise ValueError with a friendly message) ----------
def body():
    return request.get_json(silent=True) or {}


def to_int(value, lo, hi, label):
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a whole number.")
    if not lo <= n <= hi:
        raise ValueError(f"{label} must be between {lo} and {hi}.")
    return n


def to_text(value, label, maxlen, required=False):
    text = str(value or "").strip()
    if required and not text:
        raise ValueError(f"{label} is required.")
    if len(text) > maxlen:
        raise ValueError(f"{label} is too long (max {maxlen} characters).")
    return text


def to_url(value):
    url = to_text(value, "Poster link", 255)
    if url and not url.startswith(("http://", "https://")):
        raise ValueError("Poster link must start with http:// or https://")
    return url or None


def validate_movie(d):
    try:
        rating = float(d.get("rating") or 0)
    except (TypeError, ValueError):
        raise ValueError("Rating must be a number.")
    if not 0 <= rating <= 10:
        raise ValueError("Rating must be between 0 and 10.")
    return {
        "title": to_text(d.get("title"), "Title", 150, required=True),
        "description": to_text(d.get("description"), "Description", 2000) or None,
        "genre": to_text(d.get("genre"), "Genre", 80) or None,
        "language": to_text(d.get("language"), "Language", 50) or None,
        "duration_min": to_int(d.get("duration_min"), 1, 600, "Duration"),
        "rating": rating,
        "poster_url": to_url(d.get("poster_url")),
        "is_active": bool(d.get("is_active")),
    }


def validate_theater(d):
    return {
        "name": to_text(d.get("name"), "Theater name", 120, required=True),
        "location": to_text(d.get("location"), "Location", 200, required=True),
        "rows": to_int(d.get("rows"), 1, 20, "Rows"),
        "seats_per_row": to_int(d.get("seats_per_row"), 1, 20, "Seats per row"),
    }


def validate_showtime(d):
    movie_id = to_int(d.get("movie_id"), 1, 10**9, "Movie")
    theater_id = to_int(d.get("theater_id"), 1, 10**9, "Theater")
    if not db.session.get(Movie, movie_id):
        raise ValueError("Please choose a movie.")
    if not db.session.get(Theater, theater_id):
        raise ValueError("Please choose a theater.")
    try:
        start = datetime.fromisoformat(str(d.get("start_time", "")).strip()).replace(tzinfo=None)
    except ValueError:
        raise ValueError("Please choose a valid date and time.")
    try:
        price = Decimal(str(d.get("price", "")).strip())
    except InvalidOperation:
        raise ValueError("Ticket price must be a number.")
    if not Decimal("0") < price <= Decimal("99999"):
        raise ValueError("Ticket price must be more than 0.")
    return {"movie_id": movie_id, "theater_id": theater_id, "start_time": start,
            "price": price.quantize(Decimal("0.01"))}


def showtime_has_bookings(showtime_ids):
    return db.session.query(Booking.id).filter(Booking.showtime_id.in_(showtime_ids)).first() is not None


# ---------- stats ----------
@admin_bp.get("/stats")
def stats():
    revenue = (db.session.query(func.coalesce(func.sum(Booking.total), 0))
               .filter(Booking.status == "Confirmed").scalar())
    return jsonify(
        movies=Movie.query.count(), theaters=Theater.query.count(),
        showtimes=Showtime.query.count(),
        bookings=Booking.query.filter_by(status="Confirmed").count(),
        revenue=float(revenue),
    )


# ---------- movies ----------
@admin_bp.get("/movies")
def list_movies():
    return jsonify(movies=[m.to_dict() for m in Movie.query.order_by(Movie.title).all()])


@admin_bp.post("/movies")
def add_movie():
    try:
        data = validate_movie(body())
    except ValueError as e:
        return jsonify(error=str(e)), 400
    movie = Movie(**data)
    db.session.add(movie)
    db.session.commit()
    return jsonify(movie=movie.to_dict()), 201


@admin_bp.put("/movies/<int:movie_id>")
def edit_movie(movie_id):
    movie = db.get_or_404(Movie, movie_id)
    try:
        data = validate_movie(body())
    except ValueError as e:
        return jsonify(error=str(e)), 400
    for key, value in data.items():
        setattr(movie, key, value)
    db.session.commit()
    return jsonify(movie=movie.to_dict())


@admin_bp.delete("/movies/<int:movie_id>")
def delete_movie(movie_id):
    movie = db.get_or_404(Movie, movie_id)
    ids = [s.id for s in movie.showtimes]
    if ids and showtime_has_bookings(ids):
        return jsonify(error="This movie has bookings, so it can't be deleted. Edit it and turn off 'Show on website' instead."), 409
    db.session.delete(movie)  # its showtimes go with it
    db.session.commit()
    return jsonify(ok=True)


# ---------- theaters ----------
@admin_bp.get("/theaters")
def list_theaters():
    return jsonify(theaters=[t.to_dict() for t in Theater.query.order_by(Theater.name).all()])


@admin_bp.post("/theaters")
def add_theater():
    try:
        data = validate_theater(body())
    except ValueError as e:
        return jsonify(error=str(e)), 400
    theater = Theater(**data)
    db.session.add(theater)
    db.session.commit()
    return jsonify(theater=theater.to_dict()), 201


@admin_bp.put("/theaters/<int:theater_id>")
def edit_theater(theater_id):
    theater = db.get_or_404(Theater, theater_id)
    try:
        data = validate_theater(body())
    except ValueError as e:
        return jsonify(error=str(e)), 400
    layout_changed = (data["rows"], data["seats_per_row"]) != (theater.rows, theater.seats_per_row)
    if layout_changed:
        has_seats = (db.session.query(BookingSeat.id)
                     .join(Showtime, BookingSeat.showtime_id == Showtime.id)
                     .filter(Showtime.theater_id == theater.id).first())
        if has_seats:
            return jsonify(error="Seats are already booked in this theater, so its seat layout can't be changed."), 409
    for key, value in data.items():
        setattr(theater, key, value)
    db.session.commit()
    return jsonify(theater=theater.to_dict())


@admin_bp.delete("/theaters/<int:theater_id>")
def delete_theater(theater_id):
    theater = db.get_or_404(Theater, theater_id)
    ids = [s.id for s in theater.showtimes]
    if ids and showtime_has_bookings(ids):
        return jsonify(error="This theater has bookings, so it can't be deleted."), 409
    db.session.delete(theater)
    db.session.commit()
    return jsonify(ok=True)


# ---------- showtimes (each one carries the ticket price) ----------
@admin_bp.get("/showtimes")
def list_showtimes():
    rows = Showtime.query.order_by(Showtime.start_time.desc()).all()
    return jsonify(showtimes=[s.to_dict() for s in rows])


def clash(theater_id, start, ignore_id=None):
    q = Showtime.query.filter_by(theater_id=theater_id, start_time=start)
    if ignore_id:
        q = q.filter(Showtime.id != ignore_id)
    return q.first() is not None


@admin_bp.post("/showtimes")
def add_showtime():
    try:
        data = validate_showtime(body())
    except ValueError as e:
        return jsonify(error=str(e)), 400
    if data["start_time"] <= datetime.now():
        return jsonify(error="Please choose a time in the future."), 400
    if clash(data["theater_id"], data["start_time"]):
        return jsonify(error="That theater already has a show at this time."), 409
    showtime = Showtime(**data)
    db.session.add(showtime)
    db.session.commit()
    return jsonify(showtime=showtime.to_dict()), 201


@admin_bp.put("/showtimes/<int:showtime_id>")
def edit_showtime(showtime_id):
    showtime = db.get_or_404(Showtime, showtime_id)
    try:
        data = validate_showtime(body())
    except ValueError as e:
        return jsonify(error=str(e)), 400
    if showtime_has_bookings([showtime.id]) and (
            data["movie_id"] != showtime.movie_id or data["theater_id"] != showtime.theater_id):
        return jsonify(error="This show already has bookings, so its movie and theater can't be changed."), 409
    if clash(data["theater_id"], data["start_time"], ignore_id=showtime.id):
        return jsonify(error="That theater already has a show at this time."), 409
    for key, value in data.items():
        setattr(showtime, key, value)
    db.session.commit()
    return jsonify(showtime=showtime.to_dict())


@admin_bp.delete("/showtimes/<int:showtime_id>")
def delete_showtime(showtime_id):
    showtime = db.get_or_404(Showtime, showtime_id)
    if showtime_has_bookings([showtime.id]):
        return jsonify(error="This show has bookings, so it can't be deleted."), 409
    db.session.delete(showtime)
    db.session.commit()
    return jsonify(ok=True)


# ---------- bookings (read only) ----------
@admin_bp.get("/bookings")
def list_bookings():
    rows = Booking.query.order_by(Booking.created_at.desc()).limit(300).all()
    return jsonify(bookings=[b.to_dict() for b in rows])


@admin_bp.errorhandler(IntegrityError)
def integrity_error(_):
    db.session.rollback()
    return jsonify(error="That change conflicts with existing data."), 409
