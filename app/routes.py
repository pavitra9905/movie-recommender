from flask import Blueprint, abort, jsonify, render_template, request
from . import db
from .models import Movie
from .recommender import EmptyDatabase, MovieNotFound, get_recommender

main = Blueprint("main", __name__)

DEFAULT_LIMIT = 10
MAX_LIMIT = 50


@main.app_errorhandler(400)
def bad_request(error):
    return jsonify(error=error.description), 400


@main.app_errorhandler(MovieNotFound)
def movie_not_found(error):
    return jsonify(error=f"No movie found matching '{error}'. "
                         "Try /movies/search?q=..."), 404


@main.app_errorhandler(EmptyDatabase)
def empty_database(error):
    return jsonify(error=str(error)), 503

@main.get("/")
def index():
    return render_template("index.html")


def _number(name: str, cast):
    raw = request.args.get(name)
    if raw is None or raw == "":
        return None
    try:
        return cast(raw)
    except ValueError:
        abort(400, description=f"'{name}' must be a valid number")


def _genres_arg() -> list[str]:
    """Accepts ?genre=Action&genre=Drama and ?genre=Action,Drama."""
    values = request.args.getlist("genre")
    return [g.strip() for value in values for g in value.split(",") if g.strip()]


@main.get("/health")
def health():
    return jsonify(status="ok")


@main.get("/movies/count")
def movie_count():
    return jsonify(total_movies=db.session.query(Movie).count())


@main.get("/movies/search")
def search_movies():
    query = request.args.get("q", "").strip()
    if not query:
        abort(400, description="Query parameter 'q' is required")

    movies = (
        db.session.query(Movie)
        .filter(Movie.title.ilike(f"%{query}%"))
        .order_by(Movie.vote_count.desc())
        .limit(10)
        .all()
    )
    return jsonify(results=[movie.to_dict() for movie in movies])


@main.get("/genres")
def genres():
    return jsonify(genres=get_recommender().genre_names)


@main.get("/recommend")
def recommend():
    title = request.args.get("title", "").strip() or None
    limit = _number("limit", int) or DEFAULT_LIMIT
    limit = max(1, min(limit, MAX_LIMIT))

    preferences = {
        "genres": _genres_arg(),
        "min_rating": _number("min_rating", float),
        "min_year": _number("min_year", int),
        "max_year": _number("max_year", int),
        "max_runtime": _number("max_runtime", int),
    }

    results = get_recommender().recommend(title=title, limit=limit, **preferences)
    return jsonify(
        query={"title": title, "limit": limit, **preferences},
        count=len(results),
        results=results,
    )