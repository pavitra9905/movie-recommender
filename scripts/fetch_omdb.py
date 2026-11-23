import json
import socket
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import urllib3.util.connection as urllib3_cn
from requests.adapters import HTTPAdapter
from sqlalchemy.dialects.postgresql import insert
from urllib3.util.retry import Retry

from app import create_app, db
from app.models import Movie
from config import Config

# Force IPv4: some ISPs have broken IPv6 routing
urllib3_cn.allowed_gai_family = lambda: socket.AF_INET

OMDB_URL = "https://www.omdbapi.com/"
DATA_DIR = Path("data")
SEED_FILE = DATA_DIR / "seed_ids.csv"
RAW_FILE = DATA_DIR / "omdb_raw.jsonl"
CLEAN_FILE = DATA_DIR / "movies_clean.csv"

DAILY_LIMIT = 950   # free key allows 1,000/day; keep a safety margin
TIMEOUT = 20
DB_CHUNK = 500

COLUMNS = [
    "id", "title", "year", "runtime_minutes", "genres", "rating",
    "vote_count", "plot", "director", "actors", "language", "poster_url",
]


class LimitReached(Exception):
    """Raised when OMDb says the daily request limit is used up."""


def build_session(api_key: str) -> requests.Session:
    session = requests.Session()
    session.params = {"apikey": api_key}
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_movie(session: requests.Session, imdb_id: str) -> dict:
    response = session.get(
        OMDB_URL, params={"i": imdb_id, "plot": "full"}, timeout=TIMEOUT
    )
    if response.status_code == 401:
        message = response.json().get("Error", "Unauthorized")
        if "limit" in message.lower():
            raise LimitReached(message)
        raise RuntimeError(f"OMDb rejected the key: {message}")

    response.raise_for_status()
    return response.json()


def read_raw_records() -> list[dict]:
    if not RAW_FILE.exists():
        return []
    with open(RAW_FILE, encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def fetch_new_records(session: requests.Session) -> None:
    seed_ids = pd.read_csv(SEED_FILE)["imdb_id"].tolist()
    done_ids = {record["_requested_id"] for record in read_raw_records()}
    pending = [i for i in seed_ids if i not in done_ids][:DAILY_LIMIT]

    print(f"Seed ids: {len(seed_ids)} | already fetched: {len(done_ids)} | "
          f"fetching now: {len(pending)}")

    DATA_DIR.mkdir(exist_ok=True)
    with open(RAW_FILE, "a", encoding="utf-8") as file:
        for count, imdb_id in enumerate(pending, start=1):
            try:
                data = fetch_movie(session, imdb_id)
            except LimitReached as error:
                print(f"Stopped: {error}")
                break

            data["_requested_id"] = imdb_id
            file.write(json.dumps(data, ensure_ascii=False) + "\n")
            file.flush()

            if count % 100 == 0:
                print(f"Progress: {count}/{len(pending)}")
            time.sleep(0.1)


def clean_movies(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    df = df[df["Response"] == "True"]
    df = df[df["Type"] == "movie"]

    keep = ["imdbID", "Title", "Year", "Runtime", "Genre", "Director", "Actors",
            "Plot", "Language", "Poster", "imdbRating", "imdbVotes"]
    df = df[keep].replace("N/A", np.nan)
    df = df.dropna(subset=["Title", "Genre", "imdbRating", "imdbVotes", "Plot"])
    df = df.drop_duplicates(subset="imdbID")

    clean = pd.DataFrame({
        "id": df["imdbID"],
        "title": df["Title"].str.strip(),
        "year": pd.to_numeric(df["Year"].str[:4], errors="coerce").astype("Int64"),
        "runtime_minutes": pd.to_numeric(
            df["Runtime"].str.extract(r"(\d+)")[0], errors="coerce"
        ).astype("Int64"),
        "genres": df["Genre"].apply(lambda g: [x.strip() for x in g.split(",")]),
        "rating": pd.to_numeric(df["imdbRating"], errors="coerce"),
        "vote_count": pd.to_numeric(
            df["imdbVotes"].str.replace(",", ""), errors="coerce"
        ).astype("Int64"),
        "plot": df["Plot"].str.strip(),
        "director": df["Director"],
        "actors": df["Actors"],
        "language": df["Language"],
        "poster_url": df["Poster"],
    })

    clean = clean.dropna(subset=["rating", "vote_count"])
    clean = clean.sort_values("vote_count", ascending=False).reset_index(drop=True)
    clean.to_csv(CLEAN_FILE, index=False)
    return clean.astype(object).where(clean.notna(), None)


def save_to_db(df: pd.DataFrame) -> None:
    records = df.to_dict("records")
    for start in range(0, len(records), DB_CHUNK):
        chunk = records[start:start + DB_CHUNK]
        stmt = insert(Movie).values(chunk)
        update_cols = {c: stmt.excluded[c] for c in COLUMNS if c != "id"}
        stmt = stmt.on_conflict_do_update(index_elements=["id"], set_=update_cols)
        db.session.execute(stmt)
    db.session.commit()


def main() -> None:
    if not Config.OMDB_API_KEY:
        raise RuntimeError("OMDB_API_KEY is missing from .env")
    if not SEED_FILE.exists():
        raise RuntimeError("Run `python -m scripts.build_seed` first")

    session = build_session(Config.OMDB_API_KEY)
    fetch_new_records(session)

    df = clean_movies(read_raw_records())
    print(f"Clean movies: {len(df):,}")

    app = create_app()
    with app.app_context():
        save_to_db(df)
        print(f"Movies in database: {db.session.query(Movie).count():,}")


if __name__ == "__main__":
    main()