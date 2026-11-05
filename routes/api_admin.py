"""Admin JSON API: Dashboard stats, Movies, Theaters, Showtimes, Prices, and Bookings."""
import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from extensions import db
from models import Booking, BookingSeat, Movie, Showtime, Theater
from utils import api_admin_required

bp = Blueprint("admin_api", __name__, url_prefix="/api/admin")


# Guard all routes in this blueprint for admins
@bp.before_request
@api_admin_required
def admin_guard():
    pass


class ValidationError(Exception):
    """Raised when request payload fails validation."""


@bp.errorhandler(ValidationError)
def handle_validation_error(exc):
    return jsonify(error=str(exc)), 400


def get_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def validate_text(data, key, label, max_len, required=False):
    val = str(data.get(key, "") if data.get(key) is not None else "").strip()
    if required and not val:
        raise ValidationError(f"{label} is required.")
    if len(val) > max_len:
        raise ValidationError(f"{label} must be under {max_len} characters.")
    return val


def validate_num(data, key, label, lo, hi, cast=int, default=None):
    raw = data.get(key)
    if raw is None or str(raw).strip() == "":
        if default is not None:
            return default
        raise ValidationError(f"{label} is required.")
    try:
        val = cast(str(raw).strip())
        if not (lo <= val <= hi):
            raise ValueError
        return val
    except (ValueError, TypeError, ArithmeticError, InvalidOperation):
        raise ValidationError(f"{label} must be a number between {lo} and {hi}.")


def movie_payload(data):
    poster = validate_text(data, "poster_url", "Poster URL", 500)
    if poster and not re.match(r"^https?://", poster, re.I):
        raise ValidationError("Poster URL must start with http:// or https://")

    return {
        "title": validate_text(data, "title", "Movie Title", 150, required=True),
        "description": validate_text(data, "description", "Description", 5000),
        "genre": validate_text(data, "genre", "Genre", 80),
        "language": validate_text(data, "language", "Language", 50),
        "duration_min": validate_num(data, "duration_min", "Duration (minutes)", 1, 600, int, 120),
        "rating": validate_num(data, "rating", "Rating", 0.0, 10.0, float, 0.0),
        "poster_url": poster or None,
        "is_active": bool(data.get("is_active", True)),
    }


def has_bookings_for(**filters):
    q = db.session.query(Booking.id).join(Showtime, Showtime.id == Booking.showtime_id)
    if "movie_id" in filters:
        q = q.filter(Showtime.movie_id == filters["movie_id"])
    if "theater_id" in filters:
        q = q.filter(Showtime.theater_id == filters["theater_id"])
    if "showtime_id" in filters:
        q = q.filter(Booking.showtime_id == filters["showtime_id"])
    return q.first() is not None


# ==============================================================================
# 1. ADMIN DASHBOARD STATS
# ==============================================================================
@bp.get("/stats")
def dashboard_stats():
    now = datetime.now()
    total_rev = (
        db.session.query(func.coalesce(func.sum(Booking.total), 0))
        .filter(Booking.status == "Confirmed")
        .scalar()
    )
    total_bookings = Booking.query.filter_by(status="Confirmed").count()
    total_movies = Movie.query.count()
    active_movies = Movie.query.filter_by(is_active=True).count()
    total_theaters = Theater.query.count()
    upcoming_showtimes = Showtime.query.filter(Showtime.start_time > now).count()

    recent = Booking.query.order_by(Booking.created_at.desc()).limit(6).all()

    return jsonify(
        revenue=float(total_rev),
        total_bookings=total_bookings,
        total_movies=total_movies,
        active_movies=active_movies,
        total_theaters=total_theaters,
        upcoming_showtimes=upcoming_showtimes,
        recent_bookings=[b.to_dict() for b in recent],
    )


# ==============================================================================
# 2. MANAGE MOVIES (Add, Edit, Delete, Toggle Active)
# ==============================================================================
@bp.get("/movies")
def list_movies():
    items = Movie.query.order_by(Movie.is_active.desc(), Movie.title).all()
    return jsonify(movies=[m.to_dict() for m in items])


@bp.post("/movies")
def add_movie():
    fields = movie_payload(get_body())
    movie = Movie(**fields)
    db.session.add(movie)
    db.session.commit()
    return jsonify(movie=movie.to_dict()), 201


@bp.put("/movies/<int:movie_id>")
def edit_movie(movie_id):
    movie = db.get_or_404(Movie, movie_id)
    fields = movie_payload(get_body())
    for k, v in fields.items():
        setattr(movie, k, v)
    db.session.commit()
    return jsonify(movie=movie.to_dict())


@bp.patch("/movies/<int:movie_id>")
def patch_movie(movie_id):
    movie = db.get_or_404(Movie, movie_id)
    data = get_body()
    if "is_active" in data:
        movie.is_active = bool(data["is_active"])
    db.session.commit()
    return jsonify(movie=movie.to_dict())


@bp.delete("/movies/<int:movie_id>")
def delete_movie(movie_id):
    movie = db.get_or_404(Movie, movie_id)
    if has_bookings_for(movie_id=movie.id):
        return jsonify(error="This movie has active bookings and cannot be deleted. You can mark it inactive instead."), 409
    db.session.delete(movie)
    db.session.commit()
    return jsonify(ok=True)


# ==============================================================================
# 3. MANAGE THEATERS (Add, Edit, Delete)
# ==============================================================================
@bp.get("/theaters")
def list_theaters():
    items = Theater.query.order_by(Theater.city, Theater.name).all()
    return jsonify(theaters=[t.to_dict() for t in items])


@bp.post("/theaters")
def add_theater():
    data = get_body()
    theater = Theater(
        name=validate_text(data, "name", "Theater Name", 120, required=True),
        city=validate_text(data, "city", "City", 80, required=True),
        location=validate_text(data, "location", "Area / Address", 200, required=True),
        rows=validate_num(data, "rows", "Rows (A-Z)", 1, 26, int, 8),
        seats_per_row=validate_num(data, "seats_per_row", "Seats per Row", 1, 30, int, 10),
    )
    db.session.add(theater)
    db.session.commit()
    return jsonify(theater=theater.to_dict()), 201


@bp.put("/theaters/<int:theater_id>")
def edit_theater(theater_id):
    theater = db.get_or_404(Theater, theater_id)
    data = get_body()
    name = validate_text(data, "name", "Theater Name", 120, required=True)
    city = validate_text(data, "city", "City", 80, required=True)
    location = validate_text(data, "location", "Area / Address", 200, required=True)
    rows = validate_num(data, "rows", "Rows", 1, 26, int, theater.rows)
    seats_per_row = validate_num(data, "seats_per_row", "Seats per Row", 1, 30, int, theater.seats_per_row)

    # If seat layout shrunk, verify booked seats don't fall outside new bounds
    if rows < theater.rows or seats_per_row < theater.seats_per_row:
        booked_seats = (
            db.session.query(BookingSeat.seat_label)
            .join(Showtime, Showtime.id == BookingSeat.showtime_id)
            .filter(Showtime.theater_id == theater.id)
            .distinct()
            .all()
        )
        for (label,) in booked_seats:
            row_idx = ord(label[0].upper()) - 65
            col_idx = int(label[1:])
            if row_idx >= rows or col_idx > seats_per_row:
                return jsonify(error=f"Cannot reduce capacity: seat {label} has already been booked in an existing show."), 409

    theater.name = name
    theater.city = city
    theater.location = location
    theater.rows = rows
    theater.seats_per_row = seats_per_row
    db.session.commit()
    return jsonify(theater=theater.to_dict())


@bp.delete("/theaters/<int:theater_id>")
def delete_theater(theater_id):
    theater = db.get_or_404(Theater, theater_id)
    if has_bookings_for(theater_id=theater.id):
        return jsonify(error="This theater has bookings and cannot be deleted."), 409
    db.session.delete(theater)
    db.session.commit()
    return jsonify(ok=True)


# ==============================================================================
# 4 & 5. MANAGE SHOWS, TIMINGS & TICKET PRICES (Add, Edit, Delete)
# ==============================================================================
@bp.get("/showtimes")
def list_showtimes():
    rows = (
        db.session.query(Showtime)
        .order_by(Showtime.start_time.desc())
        .limit(300)
        .all()
    )
    return jsonify(showtimes=[s.to_dict() for s in rows])


def check_clash(theater_id, start_time, duration_min=120, ignore_id=None):
    """Ensures theater doesn't have an overlapping show."""
    end_time = start_time + timedelta(minutes=duration_min)
    q = Showtime.query.filter(Showtime.theater_id == theater_id)
    if ignore_id:
        q = q.filter(Showtime.id != ignore_id)

    # Check for shows starting within 2 hours of this show
    nearby_shows = q.filter(
        Showtime.start_time >= start_time - timedelta(minutes=180),
        Showtime.start_time <= end_time + timedelta(minutes=15),
    ).all()

    for s in nearby_shows:
        s_dur = s.movie.duration_min if s.movie else 120
        s_end = s.start_time + timedelta(minutes=s_dur)
        if not (end_time <= s.start_time or start_time >= s_end):
            return s
    return None


@bp.post("/showtimes")
def add_showtime():
    data = get_body()
    movie_id = validate_num(data, "movie_id", "Movie", 1, 10**9, int)
    theater_id = validate_num(data, "theater_id", "Theater", 1, 10**9, int)
    movie = db.session.get(Movie, movie_id)
    theater = db.session.get(Theater, theater_id)
    if not movie or not theater:
        raise ValidationError("Invalid movie or theater selection.")

    raw_time = validate_text(data, "start_time", "Start Time", 30, required=True)
    try:
        start_time = datetime.fromisoformat(raw_time).replace(tzinfo=None)
    except ValueError:
        raise ValidationError("Invalid date and time format.")

    if start_time <= datetime.now():
        raise ValidationError("Showtime must be scheduled in the future.")

    clashing_show = check_clash(theater.id, start_time, movie.duration_min)
    if clashing_show:
        raise ValidationError(
            f"Showtime conflicts with '{clashing_show.movie.title}' playing at {clashing_show.start_time.strftime('%I:%M %p')} in the same theater."
        )

    price = validate_num(data, "price", "Ticket Price", 1, 10000, Decimal).quantize(Decimal("0.01"))
    st = Showtime(movie_id=movie.id, theater_id=theater.id, start_time=start_time, price=price)
    db.session.add(st)
    db.session.commit()
    return jsonify(showtime=st.to_dict()), 201


@bp.put("/showtimes/<int:showtime_id>")
def edit_showtime(showtime_id):
    st = db.get_or_404(Showtime, showtime_id)
    data = get_body()

    movie_id = validate_num(data, "movie_id", "Movie", 1, 10**9, int, st.movie_id)
    theater_id = validate_num(data, "theater_id", "Theater", 1, 10**9, int, st.theater_id)
    movie = db.session.get(Movie, movie_id)
    theater = db.session.get(Theater, theater_id)
    if not movie or not theater:
        raise ValidationError("Invalid movie or theater selection.")

    # If show already has bookings, movie and theater cannot be switched
    if has_bookings_for(showtime_id=st.id) and (movie_id != st.movie_id or theater_id != st.theater_id):
        raise ValidationError("This show already has customer bookings. Movie and theater cannot be changed.")

    raw_time = validate_text(data, "start_time", "Start Time", 30, required=True)
    try:
        start_time = datetime.fromisoformat(raw_time).replace(tzinfo=None)
    except ValueError:
        raise ValidationError("Invalid date and time format.")

    clashing_show = check_clash(theater.id, start_time, movie.duration_min, ignore_id=st.id)
    if clashing_show:
        raise ValidationError(
            f"Showtime conflicts with '{clashing_show.movie.title}' playing at {clashing_show.start_time.strftime('%I:%M %p')} in the same theater."
        )

    price = validate_num(data, "price", "Ticket Price", 1, 10000, Decimal).quantize(Decimal("0.01"))

    st.movie_id = movie.id
    st.theater_id = theater.id
    st.start_time = start_time
    st.price = price
    db.session.commit()
    return jsonify(showtime=st.to_dict())


@bp.delete("/showtimes/<int:showtime_id>")
def delete_showtime(showtime_id):
    st = db.get_or_404(Showtime, showtime_id)
    if has_bookings_for(showtime_id=st.id):
        return jsonify(error="This show has confirmed bookings and cannot be deleted."), 409
    db.session.delete(st)
    db.session.commit()
    return jsonify(ok=True)


# ==============================================================================
# 6. VIEW & MANAGE BOOKINGS
# ==============================================================================
@bp.get("/bookings")
def list_bookings():
    q = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()

    query = Booking.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if q:
        like_term = f"%{q}%"
        query = query.join(Booking.user).join(Booking.showtime).join(Showtime.movie).filter(
            (Booking.reference.ilike(like_term)) |
            (Booking.seat_list.ilike(like_term)) |
            (Movie.title.ilike(like_term))
        )

    items = query.order_by(Booking.created_at.desc()).limit(300).all()
    return jsonify(bookings=[b.to_dict() for b in items])


@bp.post("/bookings/<int:booking_id>/cancel")
def admin_cancel_booking(booking_id):
    booking = db.get_or_404(Booking, booking_id)
    if booking.status != "Confirmed":
        return jsonify(error="This booking is already cancelled."), 400

    BookingSeat.query.filter_by(booking_id=booking.id).delete()
    booking.status = "Cancelled"
    db.session.commit()
    return jsonify(booking=booking.to_dict())
