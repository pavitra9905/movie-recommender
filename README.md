# Movie Finder

A content-based movie recommendation web app. Pick a movie you like, narrow things down by genre, rating, release years and runtime, and get similar movies with posters, plots and cast details.

**Live demo:** https://movie-recommender-susi.onrender.com
*(Hosted on a free tier, so the first load after a quiet period can take about a minute.)*

![Movie Finder screenshot](docs/screenshot.png)

## Features

- Recommendations similar to any movie in the database, with a similarity percentage
- Preference filters: genres, minimum rating, release years, maximum length
- "Top picks" mode when no title is given, based only on your filters
- Poster wall with a detail view (plot, director, cast) and a "Find movies like this" button to chain searches
- Title suggestions while typing
- Shareable result links (the search is stored in the URL)
- Responsive layout, keyboard accessible, respects reduced-motion settings

## Tech stack

| Area | Tools |
|---|---|
| Backend | Python, Flask, Flask-SQLAlchemy |
| Database | PostgreSQL |
| Data cleaning | Pandas, NumPy |
| Recommendation | scikit-learn (TF-IDF, cosine similarity), SciPy |
| Data sources | OMDb API, IMDb non-commercial datasets (movie id list) |
| Frontend | HTML, CSS, vanilla JavaScript |
| Hosting | Render (web service and Postgres), Gunicorn |

## How the recommender works

Each movie becomes one feature vector:

1. **Genres** are one-hot encoded (multi-label) and normalised.
2. **Plot, director and cast** are converted to TF-IDF vectors. Names are joined into single tokens (for example `christophernolan`) so they match as whole names.
3. The two blocks are concatenated, and **cosine similarity** against the chosen movie gives a similarity score.

The final ranking blends three signals:

```
score = 0.70 * similarity + 0.20 * (rating / 10) + 0.10 * log-scaled vote count
```

The weights are constants at the top of `app/recommender.py`. User preferences (genres, rating, years, runtime) are applied as filters before ranking. With no title, the similarity term is the share of selected genres a movie matches.

## Project structure

```
movie-recommender/
├── app/
│   ├── __init__.py        # Flask app factory
│   ├── models.py          # Movie table
│   ├── routes.py          # Pages and JSON API
│   ├── recommender.py     # Feature building, filtering, ranking
│   ├── templates/index.html
│   └── static/            # style.css, app.js
├── scripts/
│   ├── build_seed.py      # Builds the list of movie ids to fetch
│   └── fetch_omdb.py      # Fetches from OMDb, cleans with Pandas, loads into Postgres
├── config.py
├── run.py
├── requirements.txt
└── verify_setup.py        # Checks packages, keys and database connection
```

## Run it locally

**Requirements:** Python 3.10 to 3.12, PostgreSQL 14+, Git, and a free [OMDb API key](https://www.omdbapi.com/apikey.aspx).

```powershell
git clone https://github.com/YOUR_USERNAME/movie-recommender.git
cd movie-recommender
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

On macOS or Linux, use `python3` and `source venv/bin/activate`.

Create the database:

```powershell
psql -U postgres -c "CREATE DATABASE movie_db;"
```

Create a `.env` file in the project root:

```text
OMDB_API_KEY=your_omdb_key
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/movie_db
```

Create the table and load the data:

```powershell
flask --app run init-db
python -m scripts.build_seed
python -m scripts.fetch_omdb
```

Start the app:

```powershell
python run.py
```

Open http://127.0.0.1:5000.

### About the data pipeline

OMDb can look up a movie by IMDb id but cannot list movies, so the pipeline has two stages:

1. `build_seed.py` picks the 2,000 most-voted movies from the free IMDb ratings and titles datasets and saves their ids to `data/seed_ids.csv`.
2. `fetch_omdb.py` requests each movie from the OMDb API, stores the raw responses in `data/omdb_raw.jsonl`, cleans them with Pandas (type conversion, missing values, duplicates, genre lists) and upserts them into PostgreSQL.

A free OMDb key allows 1,000 requests per day, so each run fetches up to 950 movies. The script remembers what it has already fetched. Run it again the next day to add more. Restart the Flask server after loading new data, because the model is built on the first request.

## API

| Endpoint | Description |
|---|---|
| `GET /health` | Health check |
| `GET /movies/count` | Number of movies in the database |
| `GET /movies/search?q=incep` | Title search (up to 10 matches) |
| `GET /genres` | Available genres |
| `GET /recommend` | Recommendations (see below) |

`/recommend` query parameters (all optional):

| Parameter | Example | Meaning |
|---|---|---|
| `title` | `Inception` | Movie to find similar titles for |
| `genre` | `genre=Action&genre=Drama` or `genre=Action,Drama` | Keep only these genres |
| `min_rating` | `7.5` | Minimum IMDb rating |
| `min_year`, `max_year` | `2000`, `2024` | Release year range |
| `max_runtime` | `120` | Maximum length in minutes |
| `limit` | `12` | Number of results (1 to 50) |

Example:

```
/recommend?title=Inception&genre=Sci-Fi&min_rating=7.5&min_year=2005&limit=5
```

## Deploying to Render

1. Push the repository to GitHub.
2. Create a Render Postgres database (free plan) and copy its Internal and External database URLs.
3. Copy your local data into it:
   ```powershell
   pg_dump -U postgres -d movie_db --table=movies --no-owner --no-acl --encoding=UTF8 -f data/movies.sql
   psql "EXTERNAL_DATABASE_URL" -f data/movies.sql
   ```
4. Create a Render web service from the repository:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn run:app --workers 1 --threads 2 --timeout 120 --bind 0.0.0.0:$PORT`
   - Environment variables: `DATABASE_URL` (the Internal URL) and `PYTHON_VERSION` (`3.12.7`)
   - Health check path: `/health`

Free-tier notes: free Render Postgres databases expire after 30 days, and free web services sleep after 15 minutes without traffic. Keep `data/movies.sql` as a backup so a new database can be restored in a few minutes.

## Limitations

- Recommendations are content-based only, so they do not learn from user behaviour.
- The catalogue is limited to the movies fetched within OMDb's daily request quota.
- Plot text is English-only, so non-English plots are handled less well.

## Credits and licensing

- Movie details and posters come from the [OMDb API](https://www.omdbapi.com/).
- Movie id lists come from the [IMDb non-commercial datasets](https://developer.imdb.com/non-commercial-datasets/), which are for personal and non-commercial use. This project is for learning and portfolio purposes only.