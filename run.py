from app import create_app, db

app = create_app()


@app.cli.command("init-db")
def init_db():
    """Create all database tables."""
    db.create_all()
    print("Tables created.")


if __name__ == "__main__":
    app.run(debug=True)