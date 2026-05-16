import requests
from config import OMDB_API_key,OMDB_Base_URL

params = {
    "t": "Inception",
    "apiKey": OMDB_API_key
}
response = requests.get(OMDB_Base_URL,params = params)

print(f"Status Code:{response.status_code}")
data = response.json()

print(f"Title:{data['Title']}")
print(f"Year:{data['Year']}")
print(f"Genre:{data['Genre']}")
print(f"IMDB Rating:{data['imdbRating']}")
print(f"Plot:{data['Plot']}")