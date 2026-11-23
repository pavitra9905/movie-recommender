import time

import pandas as pd
import requests
from sqlalchemy.dialects.postgresql import insert

from app import create_app, db
from app.models import Movie
from config import Config

BASE_URL = "https://api.themoviedb.org/3"
MOVIE_LISTS = ["top_rated", "popular"]
PAGES_PER_LIST = 50  # 20 movies per page
CHUNK_SIZE = 500

COLUMNS = [
    "id", "title", "overview", "release_date", "genres", "rating",
    "vote_count", "popularity", "original_language", "poster_path",
]


def build_session() -> requests.Session:
    session = requests.Session()
    key = Config.TMDB_API_KEY
    if not key:
        raise RuntimeError("TMDB_API_KEY is missing from .env")
    if len(key) > 40:  # v4 Read Access Token
        session.headers["Authorization"] = f"Bearer {key}"
    else:  # v3 API key
        session.params = {"api_key": key}
    return session


def fetch_genre_map(session: requests.Session) -> dict[int, str]:
    response = session.get(f"{BASE_URL}/genre/movie/list", timeout=10)
    response.raise_for_status()
    return {g["id"]: g["name"] for g in response.json()["genres"]}


def fetch_movies(session: requests.Session) -> list[dict]:
    rows = []
    for list_name in MOVIE_LISTS:
        for page in range(1, PAGES_PER_LIST + 1):
            response = session.get(
                f"{BASE_URL}/movie/{list_name}",
                params={"page": page, "language": "en-US"},
                timeout=10,
            )
            response.raise_for_status()
            rows.extend(response.json()["results"])
            time.sleep(0.1)
        print(f"Fetched list: {list_name}")
    return rows


def clean_movies(raw: list[dict], genre_map: dict[int, str]) -> pd.DataFrame:
    df = pd.DataFrame(raw)

    df = df.drop_duplicates(subset="id")
    df["title"] = df["title"].str.strip()
    df["overview"] = df["overview"].fillna("").str.strip()
    df = df[(df["title"] != "") & (df["overview"] != "")]

    df["genres"] = df["genre_ids"].apply(
        lambda ids: [genre_map[i] for i in ids if i in genre_map]
    )
    df = df[df["genres"].str.len() > 0]

    df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce").dt.date
    df = df.rename(columns={"vote_average": "rating"})

    df = df[COLUMNS].reset_index(drop=True)
    return df.astype(object).where(df.notna(), None)


def load_movies(df: pd.DataFrame) -> None:
    records = df.to_dict("records")
    for start in range(0, len(records), CHUNK_SIZE):
        chunk = records[start:start + CHUNK_SIZE]
        stmt = insert(Movie).values(chunk)
        update_cols = {c: stmt.excluded[c] for c in COLUMNS if c != "id"}
        stmt = stmt.on_conflict_do_update(index_elements=["id"], set_=update_cols)
        db.session.execute(stmt)
    db.session.commit()


def main() -> None:
    session = build_session()
    genre_map = fetch_genre_map(session)
    raw = fetch_movies(session)
    print(f"Raw rows fetched: {len(raw)}")

    df = clean_movies(raw, genre_map)
    df.to_csv("data/movies_clean.csv", index=False)
    print(f"Clean unique movies: {len(df)}")

    app = create_app()
    with app.app_context():
        load_movies(df)
        print(f"Movies in database: {db.session.query(Movie).count()}")


if __name__ == "__main__":
    main()