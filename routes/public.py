"""User-facing JSON API: movies, showtimes, seat booking."""
import secrets
import string
from datetime import datetime
from flask import Blueprint, jsonify, request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from extensions import db
from models import Movie, Showtime, Booking, BookingSeat, seat_sort_key
from utils import current_user, api_login_required

public_bp = Blueprint("public", __name__, url_prefix="/api")

MAX_SEATS_PER_BOOKING = 10


def booked_counts(showtime_ids):
    """{showtime_id: number of booked seats}"""
    if not showtime_ids:
        return {}
    rows = (db.session.query(BookingSeat.showtime_id, func.count(BookingSeat.id))
            .filter(BookingSeat.showtime_id.in_(showtime_ids))
            .group_by(BookingSeat.showtime_id).all())
    return dict(rows)


def new_reference():
    alphabet = string.ascii_uppercase + string.digits
    while True:
        ref = "MB" + "".join(secrets.choice(alphabet) for _ in range(8))
        if not Booking.query.filter_by(reference=ref).first():
            return ref


# ---------- movies and showtimes ----------
@public_bp.get("/movies")
def movies():
    q = request.args.get("q", "").strip()
    query = Movie.query.filter_by(is_active=True)
    if q:
        query = query.filter(Movie.title.ilike(f"%{q}%"))
    return jsonify(movies=[m.to_dict() for m in query.order_by(Movie.title).all()])


@public_bp.get("/movies/<int:movie_id>")
def movie_detail(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie or not movie.is_active:
        return jsonify(error="Movie not found."), 404
    shows = (Showtime.query
             .filter(Showtime.movie_id == movie.id, Showtime.start_time > datetime.now())
             .order_by(Showtime.start_time).all())
    counts = booked_counts([s.id for s in shows])
    out = []
    for s in shows:
        d = s.to_dict()
        d["seats_left"] = s.theater.capacity - counts.get(s.id, 0)
        d["theater"] = s.theater.to_dict()
        out.append(d)
    return jsonify(movie=movie.to_dict(), showtimes=out)


@public_bp.get("/showtimes/<int:showtime_id>")
def showtime_detail(showtime_id):
    s = db.session.get(Showtime, showtime_id)
    if not s:
        return jsonify(error="Showtime not found."), 404
    booked = [b.seat_label for b in BookingSeat.query.filter_by(showtime_id=s.id).all()]
    return jsonify(
        showtime=s.to_dict(), movie=s.movie.to_dict(), theater=s.theater.to_dict(),
        booked=booked, started=s.start_time <= datetime.now(),
    )


# ---------- bookings ----------
@public_bp.post("/bookings")
@api_login_required
def create_booking():
    data = request.get_json(silent=True) or {}
    showtime_id = data.get("showtime_id")
    seats = data.get("seats")

    if not isinstance(showtime_id, int) or not isinstance(seats, list):
        return jsonify(error="Invalid booking request."), 400
    showtime = db.session.get(Showtime, showtime_id)
    if not showtime:
        return jsonify(error="Showtime not found."), 404
    if showtime.start_time <= datetime.now():
        return jsonify(error="This show has already started."), 400
    if not 1 <= len(seats) <= MAX_SEATS_PER_BOOKING:
        return jsonify(error=f"Please choose 1 to {MAX_SEATS_PER_BOOKING} seats."), 400
    if len(set(seats)) != len(seats) or not all(showtime.theater.valid_seat(s) for s in seats):
        return jsonify(error="One or more seats are not valid."), 400

    seats = sorted(seats, key=seat_sort_key)
    total = showtime.price * len(seats)  # price is always calculated on the server

    booking = Booking(
        reference=new_reference(), user_id=current_user().id, showtime_id=showtime.id,
        seat_list=",".join(seats), total=total, status="Confirmed",
    )
    db.session.add(booking)
    db.session.flush()
    for label in seats:
        db.session.add(BookingSeat(booking_id=booking.id, showtime_id=showtime.id, seat_label=label))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="Sorry, some of those seats were just booked by someone else. Please pick again."), 409
    return jsonify(booking=booking.to_dict()), 201


@public_bp.get("/bookings")
@api_login_required
def my_bookings():
    rows = (Booking.query.filter_by(user_id=current_user().id)
            .order_by(Booking.created_at.desc()).all())
    return jsonify(bookings=[b.to_dict() for b in rows])


@public_bp.get("/bookings/<int:booking_id>")
@api_login_required
def booking_detail(booking_id):
    b = db.session.get(Booking, booking_id)
    user = current_user()
    if not b or (b.user_id != user.id and not user.is_admin):
        return jsonify(error="Booking not found."), 404
    return jsonify(booking=b.to_dict())


@public_bp.post("/bookings/<int:booking_id>/cancel")
@api_login_required
def cancel_booking(booking_id):
    b = db.session.get(Booking, booking_id)
    if not b or b.user_id != current_user().id:
        return jsonify(error="Booking not found."), 404
    if b.status != "Confirmed":
        return jsonify(error="This booking is already cancelled."), 400
    if b.showtime.start_time <= datetime.now():
        return jsonify(error="You can't cancel a show that has already started."), 400
    BookingSeat.query.filter_by(booking_id=b.id).delete()  # frees the seats
    b.status = "Cancelled"
    db.session.commit()
    return jsonify(booking=b.to_dict())
