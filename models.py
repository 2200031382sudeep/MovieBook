import re
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


def seat_sort_key(label):
    """Sorts A1, A2, A10, B1 in natural order."""
    m = re.match(r"([A-Za-z]+)(\d+)", str(label))
    if m:
        return (m.group(1).upper(), int(m.group(2)))
    return (str(label), 0)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="customer")  # customer | admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Movie(db.Model):
    __tablename__ = "movies"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    genre = db.Column(db.String(80))
    language = db.Column(db.String(50))
    duration_min = db.Column(db.Integer, nullable=False, default=120)
    rating = db.Column(db.Float, default=0)
    poster_url = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)

    showtimes = db.relationship("Showtime", backref="movie", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description or "",
            "genre": self.genre or "",
            "language": self.language or "",
            "duration_min": self.duration_min,
            "rating": self.rating or 0.0,
            "poster_url": self.poster_url or "",
            "is_active": bool(self.is_active),
        }


class Theater(db.Model):
    __tablename__ = "theaters"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(80), nullable=False, default="Bengaluru", index=True)
    location = db.Column(db.String(200), nullable=False)
    rows = db.Column(db.Integer, nullable=False, default=8)
    seats_per_row = db.Column(db.Integer, nullable=False, default=10)

    showtimes = db.relationship("Showtime", backref="theater", cascade="all, delete-orphan")

    @property
    def capacity(self):
        return self.rows * self.seats_per_row

    def valid_seat(self, label):
        if not isinstance(label, str):
            return False
        m = re.fullmatch(r"([A-Z])(\d{1,2})", label.strip().upper())
        if not m:
            return False
        row = ord(m.group(1)) - 65
        number = int(m.group(2))
        return 0 <= row < self.rows and 1 <= number <= self.seats_per_row

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "city": self.city,
            "location": self.location,
            "rows": self.rows,
            "seats_per_row": self.seats_per_row,
            "capacity": self.capacity,
        }


class Showtime(db.Model):
    __tablename__ = "showtimes"
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"), nullable=False)
    theater_id = db.Column(db.Integer, db.ForeignKey("theaters.id"), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    price = db.Column(db.Numeric(8, 2), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "movie_id": self.movie_id,
            "theater_id": self.theater_id,
            "movie_title": self.movie.title if self.movie else "",
            "movie_poster": (self.movie.poster_url or "") if self.movie else "",
            "theater_name": self.theater.name if self.theater else "",
            "theater_city": self.theater.city if self.theater else "",
            "theater_location": self.theater.location if self.theater else "",
            "start_time": self.start_time.isoformat(timespec="minutes"),
            "price": float(self.price),
        }


class Booking(db.Model):
    __tablename__ = "bookings"
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(12), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    showtime_id = db.Column(db.Integer, db.ForeignKey("showtimes.id"), nullable=False)
    seat_list = db.Column(db.String(255), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Confirmed")  # Confirmed | Cancelled
    created_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship("User", backref="bookings")
    showtime = db.relationship("Showtime", backref="bookings")
    seats = db.relationship("BookingSeat", backref="booking", cascade="all, delete-orphan")

    def to_dict(self):
        s = self.showtime
        return {
            "id": self.id,
            "reference": self.reference,
            "status": self.status,
            "seats": [x.strip() for x in self.seat_list.split(",") if x.strip()],
            "total": float(self.total),
            "created_at": self.created_at.isoformat(timespec="minutes"),
            "user_name": self.user.name if self.user else "",
            "user_email": self.user.email if self.user else "",
            "showtime": {
                "id": s.id,
                "start_time": s.start_time.isoformat(timespec="minutes"),
                "price": float(s.price),
            } if s else {},
            "movie": {
                "id": s.movie.id,
                "title": s.movie.title,
                "poster_url": s.movie.poster_url or "",
                "language": s.movie.language or "",
                "genre": s.movie.genre or "",
            } if s and s.movie else {},
            "theater": {
                "id": s.theater.id,
                "name": s.theater.name,
                "city": s.theater.city,
                "location": s.theater.location,
            } if s and s.theater else {},
        }


class BookingSeat(db.Model):
    __tablename__ = "booking_seats"
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    showtime_id = db.Column(db.Integer, db.ForeignKey("showtimes.id"), nullable=False)
    seat_label = db.Column(db.String(5), nullable=False)

    __table_args__ = (db.UniqueConstraint("showtime_id", "seat_label", name="uq_showtime_seat"),)
