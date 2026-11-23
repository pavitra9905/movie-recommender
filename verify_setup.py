import os
import sys

from dotenv import load_dotenv

load_dotenv()

print(f"Python version : {sys.version.split()[0]}")

for pkg in ["flask", "flask_sqlalchemy", "psycopg2", "pandas", "requests", "sklearn"]:
    try:
        module = __import__(pkg)
        print(f"{pkg:<17}: OK ({getattr(module, '__version__', 'n/a')})")
    except ImportError:
        print(f"{pkg:<17}: MISSING")

print(f"OMDb key set   : {bool(os.getenv('OMDB_API_KEY'))}")

try:
    import psycopg2
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    conn.close()
    print("PostgreSQL     : connected")
except Exception as e:
    print(f"PostgreSQL     : FAILED ({e})")