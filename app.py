# app.py
from flask import Flask, jsonify, request, render_template
from flask import Flask, jsonify, request
from recommender import load_movies, clean_data, get_recommendations
from fetch_data import fetch_movie_by_title

app = Flask(__name__)

# Load and clean data once when server starts
# No need to reload from DB on every request
df = load_movies()
df = clean_data(df)


@app.route("/")
def home():
    return jsonify({
        "message": "Movie Recommendation API is running",
        "endpoints": {
            "all_movies": "/movies",
            "recommend": "/recommend?title=Inception",
            "fetch_new": "/fetch?title=Oppenheimer"
        }
    })

@app.route("/ui")
def ui():
    return render_template("index.html")


@app.route("/movies")
def get_movies():
    movies = df[["title", "genre", "imdb_rating"]].to_dict(orient="records")
    return jsonify({
        "count": len(movies),
        "movies": movies
    })


@app.route("/recommend")
def recommend():
    title = request.args.get("title")

    if not title:
        return jsonify({"error": "Please provide a title. Example: /recommend?title=Inception"}), 400

    results = get_recommendations(title, df)

    if isinstance(results, str):
        return jsonify({"error": results}), 404

    return jsonify({
        "query": title,
        "recommendations": results
    })


@app.route("/fetch")
def fetch_new():
    global df

    title = request.args.get("title")

    if not title:
        return jsonify({"error": "Please provide a title. Example: /fetch?title=Oppenheimer"}), 400

    result = fetch_movie_by_title(title)

    if result is None:
        return jsonify({"error": f"Could not fetch '{title}' from OMDB"}), 404

    # Reload dataframe so new movie is available for recommendations
    df = load_movies()
    df = clean_data(df)

    return jsonify({
        "message": f"Successfully fetched and saved '{title}'",
        "movie": {
            "title": result.get("Title"),
            "genre": result.get("Genre"),
            "rating": result.get("imdbRating")
        }
    })


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)