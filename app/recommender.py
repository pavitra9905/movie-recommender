import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MultiLabelBinarizer, normalize

from . import db
from .models import Movie

# How the final score is blended (should add up to 1.0)
SIMILARITY_WEIGHT = 0.70
RATING_WEIGHT = 0.20
POPULARITY_WEIGHT = 0.10

_recommender = None


class MovieNotFound(Exception):
    """Raised when the requested title is not in the database."""


class EmptyDatabase(Exception):
    """Raised when there are no movies to recommend from."""


def _name_tokens(names: str | None) -> str:
    """'Christopher Nolan, Emma Thomas' -> 'christophernolan emmathomas'"""
    if not names:
        return ""
    return " ".join(name.strip().replace(" ", "").lower() for name in names.split(","))


def _scalar(value):
    """Convert numpy/NaN values into plain JSON-safe Python values."""
    if pd.isna(value):
        return None
    return value.item() if hasattr(value, "item") else value


class Recommender:
    def __init__(self, movies: pd.DataFrame):
        self.movies = movies.reset_index(drop=True)
        self.genre_sets = [{g.lower() for g in genres} for genres in self.movies["genres"]]
        self.features, self.genre_names = self._build_features()

        ratings = self.movies["rating"].fillna(0).to_numpy(dtype=float)
        votes = self.movies["vote_count"].fillna(0).to_numpy(dtype=float)
        self.rating_score = ratings / 10
        self.popularity_score = np.log1p(votes) / np.log1p(max(votes.max(), 1))

    def _build_features(self):
        binarizer = MultiLabelBinarizer(sparse_output=True)
        genre_matrix = normalize(
            binarizer.fit_transform(self.movies["genres"]).astype(float)
        )

        text = (
            self.movies["plot"].fillna("")
            + " "
            + self.movies["director"].map(_name_tokens)
            + " "
            + self.movies["actors"].map(_name_tokens)
        )
        text_matrix = TfidfVectorizer(
            stop_words="english", min_df=2, sublinear_tf=True
        ).fit_transform(text)

        # Genres and text count equally in the similarity
        features = hstack([genre_matrix, text_matrix]).tocsr()
        return features, list(binarizer.classes_)

    def _filter_mask(self, genres, min_rating, min_year, max_year, max_runtime):
        mask = np.ones(len(self.movies), dtype=bool)

        if genres:
            wanted = {g.lower() for g in genres}
            mask &= np.array([bool(s & wanted) for s in self.genre_sets])
        if min_rating is not None:
            mask &= (self.movies["rating"] >= min_rating).to_numpy()
        if min_year is not None:
            mask &= (self.movies["year"] >= min_year).to_numpy()
        if max_year is not None:
            mask &= (self.movies["year"] <= max_year).to_numpy()
        if max_runtime is not None:
            mask &= (self.movies["runtime_minutes"] <= max_runtime).to_numpy()
        return mask

    def _find_index(self, title: str) -> int | None:
        query = title.lower()
        titles = self.movies["title"].str.lower()

        exact = titles == query
        if exact.any():
            return int(exact.idxmax())

        partial = titles.str.contains(query, regex=False)
        if partial.any():
            return int(self.movies.loc[partial, "vote_count"].idxmax())
        return None

    def recommend(
        self,
        title=None,
        genres=None,
        min_rating=None,
        min_year=None,
        max_year=None,
        max_runtime=None,
        limit=10,
    ) -> list[dict]:
        mask = self._filter_mask(genres, min_rating, min_year, max_year, max_runtime)

        if title:
            index = self._find_index(title)
            if index is None:
                raise MovieNotFound(title)
            similarity = cosine_similarity(self.features[index], self.features).ravel()
            mask[index] = False  # never recommend the movie itself
        elif genres:
            wanted = {g.lower() for g in genres}
            similarity = np.array(
                [len(s & wanted) / len(wanted) for s in self.genre_sets]
            )
        else:
            similarity = np.zeros(len(self.movies))

        score = (
            SIMILARITY_WEIGHT * similarity
            + RATING_WEIGHT * self.rating_score
            + POPULARITY_WEIGHT * self.popularity_score
        )
        score = np.where(mask, score, -np.inf)

        order = np.argsort(score)[::-1][:limit]
        return [
            self._to_result(i, score[i], similarity[i])
            for i in order
            if np.isfinite(score[i])
        ]

    def _to_result(self, index: int, score: float, similarity: float) -> dict:
        row = self.movies.iloc[index]
        return {
            "id": _scalar(row["id"]),
            "title": _scalar(row["title"]),
            "year": _scalar(row["year"]),
            "genres": list(row["genres"]),
            "rating": _scalar(row["rating"]),
            "director": _scalar(row["director"]),
            "poster_url": _scalar(row["poster_url"]),
            "similarity": round(float(similarity), 3),
            "score": round(float(score), 3),
        }


def load_movies() -> pd.DataFrame:
    rows = db.session.execute(db.select(Movie)).scalars().all()
    if not rows:
        raise EmptyDatabase("No movies in the database. Run the data scripts first.")

    df = pd.DataFrame([movie.to_dict() for movie in rows])
    for column in ["year", "runtime_minutes", "rating", "vote_count"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def get_recommender() -> Recommender:
    """Build the model on first use, then reuse it."""
    global _recommender
    if _recommender is None:
        _recommender = Recommender(load_movies())
    return _recommender