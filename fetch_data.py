# fetch_data.py
import requests
from config import OMDB_API_key, OMDB_Base_URL
from database import insert_movie

def fetch_movie_by_title(title):
    params = {
        "t": title,
        "apikey": OMDB_API_key,
        "plot": "short"
    }

    try:
        response = requests.get(OMDB_Base_URL, params=params, timeout=5)
        data = response.json()

        if data.get("Response") == "True":
            insert_movie(data)
            return data
        else:
            print(f"Movie not found: {title} — {data.get('Error')}")
            return None

    except requests.exceptions.Timeout:
        print(f"Timeout fetching: {title}")
        return None

    except requests.exceptions.ConnectionError:
        print(f"Connection error fetching: {title}")
        return None


# Test: fetch a small batch of movies
if __name__ == "__main__":
    movies_to_fetch = [
        "Inception", "The Dark Knight", "Interstellar",
        "The Matrix", "Fight Club", "Forrest Gump",
        "The Godfather", "Pulp Fiction", "Goodfellas", "The Shawshank Redemption"
    ]

    for title in movies_to_fetch:
        fetch_movie_by_title(title)