import csv
import socket
from pathlib import Path

import pandas as pd
import requests
import urllib3.util.connection as urllib3_cn

# Force IPv4: some ISPs have broken IPv6 routing
urllib3_cn.allowed_gai_family = lambda: socket.AF_INET

DATA_DIR = Path("data")
BASE_URL = "https://datasets.imdbws.com"
BASICS_FILE = "title.basics.tsv.gz"
RATINGS_FILE = "title.ratings.tsv.gz"
SEED_FILE = DATA_DIR / "seed_ids.csv"

MIN_VOTES = 10_000
SEED_SIZE = 5_000
READ_CHUNK = 500_000


def download(name: str) -> Path:
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / name
    if path.exists():
        print(f"Using existing file: {name}")
        return path

    print(f"Downloading {name} ...")
    with requests.get(f"{BASE_URL}/{name}", stream=True, timeout=60) as response:
        response.raise_for_status()
        with open(path, "wb") as file:
            for block in response.iter_content(chunk_size=1024 * 1024):
                file.write(block)
    return path


def load_ratings(path: Path) -> pd.DataFrame:
    ratings = pd.read_csv(path, sep="\t", na_values="\\N")
    return ratings[ratings["numVotes"] >= MIN_VOTES]


def load_movie_ids(path: Path, wanted_ids: set[str]) -> set[str]:
    reader = pd.read_csv(
        path,
        sep="\t",
        na_values="\\N",
        quoting=csv.QUOTE_NONE,
        dtype=str,
        usecols=["tconst", "titleType", "isAdult"],
        chunksize=READ_CHUNK,
    )
    found: set[str] = set()
    for chunk in reader:
        mask = (
            (chunk["titleType"] == "movie")
            & (chunk["isAdult"] == "0")
            & (chunk["tconst"].isin(wanted_ids))
        )
        found.update(chunk.loc[mask, "tconst"])
    return found


def main() -> None:
    basics_path = download(BASICS_FILE)
    ratings_path = download(RATINGS_FILE)

    ratings = load_ratings(ratings_path)
    movie_ids = load_movie_ids(basics_path, set(ratings["tconst"]))

    seed = ratings[ratings["tconst"].isin(movie_ids)]
    seed = seed.sort_values("numVotes", ascending=False).head(SEED_SIZE)
    seed = seed.rename(columns={"tconst": "imdb_id", "numVotes": "vote_count"})
    seed[["imdb_id", "vote_count"]].to_csv(SEED_FILE, index=False)

    print(f"Seed list saved: {len(seed):,} movie ids -> {SEED_FILE}")


if __name__ == "__main__":
    main()