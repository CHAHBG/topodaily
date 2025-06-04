import os
import psycopg2
from sqlalchemy import create_engine
from urllib.parse import quote_plus

DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'topodb')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'password')

def get_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, database=DB_NAME,
            user=DB_USER, password=DB_PASSWORD
        )
        return conn
    except Exception:
        return None

def get_engine():
    try:
        password = quote_plus(DB_PASSWORD)
        engine = create_engine(
            f'postgresql://{DB_USER}:{password}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
        )
        return engine
    except Exception:
        return None

def init_db():
    conn = get_connection()
    if not conn:
        return
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(100) UNIQUE NOT NULL,
        password VARCHAR(100) NOT NULL,
        email VARCHAR(100) UNIQUE,
        phone VARCHAR(20),
        role VARCHAR(20) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS leves (
        id SERIAL PRIMARY KEY,
        date DATE NOT NULL,
        village VARCHAR(100) NOT NULL,
        region VARCHAR(100),
        commune VARCHAR(100),
        type VARCHAR(50) NOT NULL,
        quantite INTEGER NOT NULL,
        appareil VARCHAR(100),
        topographe VARCHAR(100) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        import hashlib
        admin_password = hashlib.sha256("admin".encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                  ("admin", admin_password, "administrateur"))
    conn.commit()
    conn.close()