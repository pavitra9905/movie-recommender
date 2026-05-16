# fetch_data.py
import requests
import os
from database import insert_movie

OMDB_API_key = os.environ.get("OMDB_API_key", "")
OMDB_Base_URL = "http://www.omdbapi.com/"

def fetch_movie_by_title(title):
    params = {
        "t": title,
        "apikey": OMDB_API_key,
        "plot": "short"
    }

    try:
        response = requests.get(OMDB_BASE_URL, params=params, timeout=5)
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