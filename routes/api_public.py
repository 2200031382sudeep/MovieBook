"""User-facing JSON API: Auth, Cities, Theaters, Movies, Showtimes, and Seat Booking."""
import re
import secrets
from datetime import datetime
from decimal import Decimal

from flask import Blueprint, jsonify, request, session
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Booking, BookingSeat, Movie, Showtime, Theater, User, seat_sort_key
from utils import api_login_required, current_user

bp = Blueprint("api", __name__, url_prefix="/api")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_SEATS_PER_BOOKING = 10


def err(message, status=400):
    return jsonify(error=message), status


def body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


# ==============================================================================
# AUTHENTICATION
# ==============================================================================
@bp.post("/auth/register")
def register():
    data = body()
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not name or len(name) > 100:
        return err("Please enter your name (max 100 characters).")
    if not EMAIL_RE.match(email) or len(email) > 150:
        return err("Please enter a valid email address.")
    if len(password) < 6:
        return err("Password must be at least 6 characters.")
    if User.query.filter_by(email=email).first():
        return err("An account with this email already exists.", 409)

    user = User(name=name, email=email, role="customer")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    session.clear()
    session["user_id"] = user.id
    return jsonify(user=user.to_dict()), 201


@bp.post("/auth/login")
def login():
    data = body()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return err("Invalid email or password.", 401)

    session.clear()
    session["user_id"] = user.id
    return jsonify(user=user.to_dict())


@bp.post("/auth/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@bp.get("/auth/me")
def me():
    user = current_user()
    return jsonify(user=user.to_dict() if user else None)


# ==============================================================================
# CITIES & THEATERS BROWSING
# ==============================================================================
@bp.get("/cities")
@bp.get("/theater-cities")
def cities():
    rows = db.session.query(Theater.city).distinct().order_by(Theater.city).all()
    return jsonify(cities=[r[0] for r in rows if r[0]])


@bp.get("/theaters")
@bp.get("/theater-search")
def theaters_list():
    q = request.args.get("q", "").strip()[:100]
    loc = request.args.get("location", "").strip()[:100]
    city = request.args.get("city", "").strip()[:80] or loc

    query = Theater.query
    if q:
        query = query.filter(Theater.name.ilike(f"%{q}%"))
    if city:
        pattern = f"%{city}%"
        query = query.filter(or_(Theater.city.ilike(pattern), Theater.location.ilike(pattern)))

    now = datetime.now()
    results = []
    for t in query.order_by(Theater.city, Theater.name).limit(100).all():
        active_movies = (
            db.session.query(Movie)
            .join(Showtime, Showtime.movie_id == Movie.id)
            .filter(Showtime.theater_id == t.id, Showtime.start_time > now, Movie.is_active.is_(True))
            .distinct()
            .order_by(Movie.title)
            .all()
        )
        d = t.to_dict()
        d["movies"] = [m.to_dict() for m in active_movies]
        results.append(d)

    return jsonify(theaters=results)


# ==============================================================================
# MOVIES & SHOWTIMES BROWSING
# ==============================================================================
@bp.get("/movies")
def movies():
    city = request.args.get("city", "").strip()
    q = request.args.get("q", "").strip()[:100]
    genre = request.args.get("genre", "").strip()
    language = request.args.get("language", "").strip()

    query = Movie.query.filter(Movie.is_active.is_(True))
    if q:
        query = query.filter(Movie.title.ilike(f"%{q}%"))
    if genre:
        query = query.filter(Movie.genre.ilike(f"%{genre}%"))
    if language:
        query = query.filter(Movie.language.ilike(f"%{language}%"))
    if city:
        city_theaters = db.session.query(Theater.id).filter(Theater.city == city)
        query = query.filter(
            Movie.showtimes.any(
                (Showtime.start_time > datetime.now()) & Showtime.theater_id.in_(city_theaters)
            )
        )

    items = query.order_by(Movie.rating.desc(), Movie.title).all()
    return jsonify(movies=[m.to_dict() for m in items])


@bp.get("/movies/<int:movie_id>")
def movie_detail(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie or not movie.is_active:
        return err("Movie not found.", 404)

    city = request.args.get("city", "").strip()
    now = datetime.now()
    query = (
        db.session.query(Showtime, Theater)
        .join(Theater, Theater.id == Showtime.theater_id)
        .filter(Showtime.movie_id == movie.id, Showtime.start_time > now)
    )
    if city:
        query = query.filter(Theater.city == city)

    shows = []
    for s, t in query.order_by(Showtime.start_time).all():
        shows.append({
            "id": s.id,
            "start_time": s.start_time.isoformat(timespec="minutes"),
            "price": float(s.price),
            "theater": t.to_dict(),
        })

    return jsonify(movie=movie.to_dict(), showtimes=shows)


@bp.get("/showtimes/<int:showtime_id>")
@api_login_required
def showtime_detail(showtime_id):
    st = db.session.get(Showtime, showtime_id)
    if not st:
        return err("Showtime not found.", 404)

    taken = [
        r[0]
        for r in db.session.query(BookingSeat.seat_label)
        .filter(BookingSeat.showtime_id == st.id)
        .all()
    ]

    return jsonify(
        showtime=st.to_dict(),
        movie=st.movie.to_dict() if st.movie else {},
        theater=st.theater.to_dict() if st.theater else {},
        taken=taken,
        past=st.start_time <= datetime.now(),
    )


# ==============================================================================
# BOOKINGS & PAYMENTS
# ==============================================================================
@bp.post("/bookings")
@api_login_required
def create_booking():
    user = current_user()
    data = body()

    try:
        showtime_id = int(data.get("showtime_id"))
    except (TypeError, ValueError):
        return err("Invalid showtime.")

    st = db.session.get(Showtime, showtime_id)
    if not st:
        return err("Showtime not found.", 404)
    if st.start_time <= datetime.now():
        return err("This show has already started and cannot be booked.")

    seats = data.get("seats")
    if not isinstance(seats, list) or not seats:
        return err("Please select at least one seat.")
    if len(seats) > MAX_SEATS_PER_BOOKING:
        return err(f"You can book a maximum of {MAX_SEATS_PER_BOOKING} seats at a time.")

    # Clean and uppercase seat labels
    seats = [str(s).strip().upper() for s in seats]

    if len(set(seats)) != len(seats):
        return err("Duplicate seats selected.")
    if not all(st.theater.valid_seat(s) for s in seats):
        return err("One or more chosen seats are invalid for this cinema hall.")

    # Check if already booked
    already_booked = (
        db.session.query(BookingSeat.seat_label)
        .filter(BookingSeat.showtime_id == st.id, BookingSeat.seat_label.in_(seats))
        .all()
    )
    if already_booked:
        booked_labels = ", ".join(r[0] for r in already_booked)
        return err(f"Sorry, seat(s) {booked_labels} were just taken. Please pick other seats.", 409)

    seats = sorted(seats, key=seat_sort_key)
    reference = "BMS-" + secrets.token_hex(4).upper()
    while Booking.query.filter_by(reference=reference).first():
        reference = "BMS-" + secrets.token_hex(4).upper()

    total_amount = Decimal(str(st.price)) * Decimal(len(seats))
    booking = Booking(
        reference=reference,
        user_id=user.id,
        showtime_id=st.id,
        seat_list=",".join(seats),
        total=total_amount,
        status="Confirmed",
    )

    try:
        db.session.add(booking)
        db.session.flush()
        for label in seats:
            db.session.add(BookingSeat(booking_id=booking.id, showtime_id=st.id, seat_label=label))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return err("One or more selected seats were booked simultaneously by another customer. Please choose again.", 409)
    except Exception as exc:
        db.session.rollback()
        return err("An unexpected error occurred while saving your booking. Please try again.", 500)

    return jsonify(booking=booking.to_dict()), 201


@bp.get("/bookings")
@api_login_required
def my_bookings():
    user = current_user()
    items = Booking.query.filter_by(user_id=user.id).order_by(Booking.created_at.desc()).all()
    return jsonify(bookings=[b.to_dict() for b in items])


@bp.get("/bookings/<reference>")
@api_login_required
def get_booking(reference):
    user = current_user()
    booking = Booking.query.filter_by(reference=reference).first_or_404()
    if booking.user_id != user.id and not user.is_admin:
        return err("Access denied.", 403)
    return jsonify(booking=booking.to_dict())


@bp.post("/bookings/<int:booking_id>/cancel")
@api_login_required
def cancel_booking(booking_id):
    user = current_user()
    booking = db.session.get(Booking, booking_id)
    if not booking or (booking.user_id != user.id and not user.is_admin):
        return err("Booking not found.", 404)
    if booking.status != "Confirmed":
        return err("This booking has already been cancelled.")
    if booking.showtime.start_time <= datetime.now() and not user.is_admin:
        return err("Showtime has already commenced. Past bookings cannot be cancelled.")

    BookingSeat.query.filter_by(booking_id=booking.id).delete()
    booking.status = "Cancelled"
    db.session.commit()
    return jsonify(booking=booking.to_dict())
