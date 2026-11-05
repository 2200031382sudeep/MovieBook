"""JSON API used by the website: login, movies, seats, bookings."""
import re
import secrets
from datetime import datetime

from flask import Blueprint, jsonify, request, session
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


# ---------------------------------------------------------------- accounts
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
        return err("Wrong email or password.", 401)

    session.clear()
    session["user_id"] = user.id
    return jsonify(user=user.to_dict())


@bp.post("/auth/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


# ---------------------------------------------------------------- browsing
@bp.get("/cities")
def cities():
    rows = db.session.query(Theater.city).distinct().order_by(Theater.city).all()
    return jsonify(cities=[r[0] for r in rows if r[0]])


@bp.get("/movies")
def movies():
    """Active movies. With ?city=X only movies that have upcoming shows in that city."""
    city = request.args.get("city", "").strip()
    text = request.args.get("q", "").strip()[:100]

    query = Movie.query.filter(Movie.is_active.is_(True))
    if text:
        like = "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        query = query.filter(Movie.title.ilike(like, escape="\\"))
    if city:
        city_theaters = db.session.query(Theater.id).filter(Theater.city == city)
        query = query.filter(Movie.showtimes.any(
            (Showtime.start_time > datetime.now()) & Showtime.theater_id.in_(city_theaters)))

    items = query.order_by(Movie.rating.desc(), Movie.title).all()
    return jsonify(movies=[m.to_dict() for m in items])


@bp.get("/movies/<int:movie_id>")
def movie_detail(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie or not movie.is_active:
        return err("Movie not found.", 404)

    city = request.args.get("city", "").strip()
    query = (db.session.query(Showtime, Theater)
             .join(Theater, Theater.id == Showtime.theater_id)
             .filter(Showtime.movie_id == movie.id, Showtime.start_time > datetime.now()))
    if city:
        query = query.filter(Theater.city == city)

    shows = [{
        "id": s.id,
        "start_time": s.start_time.isoformat(timespec="minutes"),
        "price": float(s.price),
        "theater": {"id": t.id, "name": t.name, "city": t.city, "location": t.location},
    } for s, t in query.order_by(Showtime.start_time).all()]
    return jsonify(movie=movie.to_dict(), showtimes=shows)


@bp.get("/showtimes/<int:showtime_id>")
@api_login_required
def showtime_detail(showtime_id):
    st = db.session.get(Showtime, showtime_id)
    if not st:
        return err("Show not found.", 404)
    taken = [r[0] for r in db.session.query(BookingSeat.seat_label)
             .filter(BookingSeat.showtime_id == st.id).all()]
    return jsonify(
        showtime=st.to_dict(), movie=st.movie.to_dict(), theater=st.theater.to_dict(),
        taken=taken, past=st.start_time <= datetime.now(),
    )


# ---------------------------------------------------------------- bookings
@bp.post("/bookings")
@api_login_required
def create_booking():
    user = current_user()
    data = body()

    try:
        showtime_id = int(data.get("showtime_id"))
    except (TypeError, ValueError):
        return err("Invalid show.")
    st = db.session.get(Showtime, showtime_id)
    if not st:
        return err("Show not found.", 404)
    if st.start_time <= datetime.now():
        return err("This show has already started.")

    seats = data.get("seats")
    if not isinstance(seats, list) or not seats:
        return err("Please select at least one seat.")
    if len(seats) > MAX_SEATS_PER_BOOKING:
        return err(f"You can book at most {MAX_SEATS_PER_BOOKING} seats at a time.")
    if len(set(seats)) != len(seats):
        return err("Duplicate seats selected.")
    if not all(st.theater.valid_seat(s) for s in seats):
        return err("One or more seats are invalid.")
    seats = sorted(seats, key=seat_sort_key)

    reference = secrets.token_hex(4).upper()
    while Booking.query.filter_by(reference=reference).first():
        reference = secrets.token_hex(4).upper()

    booking = Booking(reference=reference, user_id=user.id, showtime_id=st.id,
                      seat_list=",".join(seats), total=st.price * len(seats))
    try:
        db.session.add(booking)
        db.session.flush()
        for label in seats:
            db.session.add(BookingSeat(booking_id=booking.id, showtime_id=st.id, seat_label=label))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return err("Sorry, one or more of those seats were just booked. Please pick other seats.", 409)

    return jsonify(booking=booking.to_dict()), 201


@bp.get("/bookings")
@api_login_required
def my_bookings():
    user = current_user()
    items = Booking.query.filter_by(user_id=user.id).order_by(Booking.created_at.desc()).all()
    return jsonify(bookings=[b.to_dict() for b in items])


@bp.post("/bookings/<int:booking_id>/cancel")
@api_login_required
def cancel_booking(booking_id):
    user = current_user()
    booking = db.session.get(Booking, booking_id)
    if not booking or (booking.user_id != user.id and not user.is_admin):
        return err("Booking not found.", 404)
    if booking.status != "Confirmed":
        return err("This booking is already cancelled.")
    if booking.showtime.start_time <= datetime.now() and not user.is_admin:
        return err("You can't cancel a show that has already started.")

    BookingSeat.query.filter_by(booking_id=booking.id).delete()   # frees the seats
    booking.status = "Cancelled"
    db.session.commit()
    return jsonify(booking=booking.to_dict())
