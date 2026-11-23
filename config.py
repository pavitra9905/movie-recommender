import os

from dotenv import load_dotenv

load_dotenv()


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    # Render supplies "postgres://" or "postgresql://"; always use the psycopg2 driver
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


class Config:
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OMDB_API_KEY = os.getenv("OMDB_API_KEY")