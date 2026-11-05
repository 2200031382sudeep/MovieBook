"""Theater search for logged-in users: search by theater name and/or location (city or area)."""
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request
from sqlalchemy import or_

from extensions import db
from models import Movie, Showtime, Theater
from utils import api_login_required, page_login_required

bp = Blueprint("theater_search", __name__)


def _like(text):
    """Turns user text into a safe 'contains' pattern (so % and _ are treated as normal letters)."""
    text = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{text}%"


@bp.get("/theaters")
@page_login_required
def theaters_page():
    return render_template("theaters.html")


@bp.get("/api/theater-cities")
@api_login_required
def theater_cities():
    rows = db.session.query(Theater.city).distinct().order_by(Theater.city).all()
    return jsonify(cities=[r[0] for r in rows if r[0]])


@bp.get("/api/theater-search")
@api_login_required
def theater_search():
    name = request.args.get("q", "").strip()[:100]
    location = request.args.get("location", "").strip()[:100]

    query = Theater.query
    if name:
        query = query.filter(Theater.name.ilike(_like(name), escape="\\"))
    if location:
        pattern = _like(location)
        query = query.filter(or_(
            Theater.city.ilike(pattern, escape="\\"),
            Theater.location.ilike(pattern, escape="\\"),
        ))

    now = datetime.now()
    results = []
    for theater in query.order_by(Theater.city, Theater.name).limit(50).all():
        movies = (
            db.session.query(Movie.id, Movie.title)
            .join(Showtime, Showtime.movie_id == Movie.id)
            .filter(Showtime.theater_id == theater.id, Showtime.start_time > now,
                    Movie.is_active.is_(True))
            .distinct().order_by(Movie.title).all()
        )
        item = theater.to_dict()
        item["movies"] = [{"id": m.id, "title": m.title} for m in movies]
        results.append(item)

    return jsonify(theaters=results)
