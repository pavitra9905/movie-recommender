import sqlite3
DB_Path = "data/movies.db"

def get_connection():

    conn = sqlite3.connect(DB_Path)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
                create table if not exists movies(
                   id               INTEGER PRIMARY KEY AUTOINCREMENT,
                   imdb_id          TEXT UNIQUE,
                   title            TEXT,
                   year             TEXT,
                   genre            TEXT,
                   director         TEXT,
                   plot             TEXT,
                   imdb_rating      TEXT,
                   language         TEXT,
                   country          TEXT
                )  
    """)
    conn.commit()
    conn.close()
    print("Tables created successfully.")

if __name__ == "__main__":
    import os
    os.makedirs("data",exist_ok = True)
    create_tables()

def insert_movie(movie_data):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT OR IGNORE INTO movies 
            (imdb_id, title, year, genre, director, plot, imdb_rating, language, country)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            movie_data.get("imdbID"),
            movie_data.get("Title"),
            movie_data.get("Year"),
            movie_data.get("Genre"),
            movie_data.get("Director"),
            movie_data.get("Plot"),
            float(movie_data.get("imdbRating", 0)) if movie_data.get("imdbRating") != "N/A" else 0.0,
            movie_data.get("Language"),
            movie_data.get("Country")
        ))
        conn.commit()
        print(f"Saved: {movie_data.get('Title')}")

    except Exception as e:
        print(f"Error inserting movie: {e}")

    finally:
        conn.close()


def get_all_movies():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM movies")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]