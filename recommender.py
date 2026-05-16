# recommender.py
import pandas as pd
from database import get_all_movies

def load_movies():
    movies = get_all_movies()
    df = pd.DataFrame(movies)
    return df

def clean_data(df):
    # Drop rows where genre or rating is missing
    df = df.dropna(subset=["genre", "imdb_rating"])

    # Convert imdb_rating to float (it comes out of SQLite as string sometimes)
    df["imdb_rating"] = pd.to_numeric(df["imdb_rating"], errors="coerce")

    # Drop rows where conversion failed (became NaN)
    df = df.dropna(subset=["imdb_rating"])

    # Remove movies with 0.0 rating
    df = df[df["imdb_rating"] > 0]

    # Clean up genre strings
    df["genre"] = df["genre"].str.strip()

    return df

def get_recommendations(movie_title, df, top_n=5):
    # Find the movie the user is asking about
    movie = df[df["title"].str.lower() == movie_title.lower()]

    if movie.empty:
        return f"Movie '{movie_title}' not found in database."

    # Get genres of that movie as a list
    # e.g. "Action, Crime, Drama" → ["Action", "Crime", "Drama"]
    target_genres = set(movie.iloc[0]["genre"].split(", "))
    target_rating = movie.iloc[0]["imdb_rating"]

    # Score every other movie by how many genres match
    def score_movie(row):
        if row["title"].lower() == movie_title.lower():
            return -1  # exclude the input movie itself

        row_genres = set(row["genre"].split(", "))

        # Count matching genres
        genre_overlap = len(target_genres & row_genres)

        # Small boost if rating is close (within 0.5)
        rating_boost = 1 if abs(row["imdb_rating"] - target_rating) <= 0.5 else 0

        return genre_overlap + rating_boost

    df = df.copy()
    df["score"] = df.apply(score_movie, axis=1)

    # Sort by score descending, take top N
    recommendations = df[df["score"] > 0].sort_values("score", ascending=False).head(top_n)

    return recommendations[["title", "genre", "imdb_rating", "score"]].to_dict(orient="records")


# Test it
if __name__ == "__main__":
    df = load_movies()
    df = clean_data(df)

    print("All movies loaded:", len(df))
    print()

    results = get_recommendations("Inception", df)
    print("Recommendations for Inception:")
    for r in results:
        print(f"  {r['title']} | {r['genre']} | Rating: {r['imdb_rating']} | Score: {r['score']}")