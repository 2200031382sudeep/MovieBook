"""Adds sample movies, theaters and showtimes so you can try the website straight away.
Run once:  python seed_sample.py   (skips if movies already exist)"""
from datetime import datetime, timedelta
from decimal import Decimal
from app import app
from extensions import db
from models import Movie, Theater, Showtime

MOVIES = [
    ("Galaxy Rangers", "Action, Sci-Fi", "English", 142, 8.4, "A crew of misfits must save a distant colony from a rogue AI."),
    ("Monsoon Melodies", "Romance, Drama", "Hindi", 128, 7.9, "Two musicians meet during one rainy season in Mumbai."),
    ("The Last Heist", "Thriller", "English", 118, 8.1, "One final job, one broken rule, and a crew that can't trust each other."),
    ("Laugh Riot", "Comedy", "Hindi", 110, 7.2, "A wedding planner's worst weekend turns into the funniest one."),
    ("Dragon Realm", "Fantasy, Adventure", "English", 150, 8.6, "A young explorer discovers a hidden world ruled by dragons."),
]
THEATERS = [
    ("Star Cinemas", "MG Road, Bengaluru", 8, 10),
    ("Galaxy Multiplex", "Indiranagar, Bengaluru", 6, 12),
]
TIMES = [(12, 0), (15, 30), (19, 0), (22, 0)]

with app.app_context():
    if Movie.query.count():
        raise SystemExit("Movies already exist - nothing added.")

    movies = [Movie(title=t, genre=g, language=l, duration_min=d, rating=r, description=desc, is_active=True)
              for t, g, l, d, r, desc in MOVIES]
    theaters = [Theater(name=n, location=loc, rows=r, seats_per_row=s) for n, loc, r, s in THEATERS]
    db.session.add_all(movies + theaters)
    db.session.flush()

    now = datetime.now()
    count = 0
    for day in range(0, 4):
        for i, movie in enumerate(movies):
            theater = theaters[i % len(theaters)]
            hour, minute = TIMES[(i + day) % len(TIMES)]
            start = (now + timedelta(days=day)).replace(hour=hour, minute=minute, second=0, microsecond=0)
            if start > now:
                db.session.add(Showtime(movie_id=movie.id, theater_id=theater.id, start_time=start,
                                        price=Decimal("250") if hour < 19 else Decimal("320")))
                count += 1
    db.session.commit()
    print(f"Added {len(movies)} movies, {len(theaters)} theaters and {count} showtimes.")
