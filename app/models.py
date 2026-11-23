from sqlalchemy.dialects.postgresql import ARRAY

from . import db


class Movie(db.Model):
    __tablename__ = "movies"

    id = db.Column(db.String(12), primary_key=True)  # IMDb id, e.g. tt0111161
    title = db.Column(db.String(500), nullable=False)
    year = db.Column(db.Integer)
    runtime_minutes = db.Column(db.Integer)
    genres = db.Column(ARRAY(db.String(50)), nullable=False, default=list)
    rating = db.Column(db.Float)
    vote_count = db.Column(db.Integer)
    plot = db.Column(db.Text)
    director = db.Column(db.String(255))
    actors = db.Column(db.String(500))
    language = db.Column(db.String(255))
    poster_url = db.Column(db.String(500))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "year": self.year,
            "runtime_minutes": self.runtime_minutes,
            "genres": self.genres,
            "rating": self.rating,
            "vote_count": self.vote_count,
            "plot": self.plot,
            "director": self.director,
            "actors": self.actors,
            "poster_url": self.poster_url,
        }