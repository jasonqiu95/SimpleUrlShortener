import os
import string
import random
import redis
import psycopg2
from psycopg2 import sql
from flask import Flask, request, jsonify, redirect
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

# Environment variables for database and cache connection details
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://jasonqiu:password@postgres:5432/urldb")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
print(REDIS_URL)
print(DATABASE_URL)

# Connect to Redis and PostgreSQL
cache_conn = None
db_conn = None

def get_cache_connection():
    global cache_conn
    if cache_conn is None:
        cache_conn = redis.StrictRedis.from_url(REDIS_URL)
    return  cache_conn

def get_db_connection():
    global db_conn
    if db_conn is None:
        db_conn = psycopg2.connect(DATABASE_URL)
    return db_conn


# Base62 characters for shortening
BASE62 = string.ascii_letters + string.digits

def generate_short_code(length=6):
    """Generates a random short code."""
    return ''.join(random.choices(BASE62, k=length))

def save_url_mapping(short_url, original_url):
    """Saves the URL mapping in PostgreSQL and retries if a duplicate short_url is generated."""
    conn = get_db_connection()
    with conn.cursor() as cursor:
        retries = 5
        while retries > 0:
            try:
                cursor.execute(
                    sql.SQL("INSERT INTO urls (short_url, original_url) VALUES (%s, %s)"),
                    (short_url, original_url)
                )
                conn.commit()
                return short_url
            except psycopg2.IntegrityError:
                # Rollback the transaction if there's a duplicate
                conn.rollback()
                short_url = generate_short_code()  # Generate a new code
                retries -= 1
        raise Exception("Failed to generate a unique short URL after several attempts")

def get_original_url(short_url):
    """Retrieves the original URL from PostgreSQL."""
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT original_url FROM urls WHERE short_url = %s", (short_url,))
        result = cursor.fetchone()
        return result[0] if result else None

def get_short_url(original_url):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT short_url FROM urls WHERE original_url = %s", (original_url,))
        result = cursor.fetchone()
        return result[0] if result else None


@app.route('/shorten', methods=['POST'])
def shorten_url():
    """Shortens a given URL and stores it in cache and database."""
    data = request.get_json()
    original_url = data.get("url")
    cache = get_cache_connection()

    # Check if the URL is already cached
    cached_short_url = cache.get(original_url)
    if cached_short_url:
        return jsonify({'short_url': cached_short_url.decode()})

    potential_short_url = get_short_url(original_url)
    if potential_short_url:
        cache.set(original_url, potential_short_url)
        return jsonify({'short_url': potential_short_url})

    # Generate a unique short code and save it
    short_url = generate_short_code()
    save_url_mapping(short_url, original_url)
    cache.set(original_url, short_url)  # Cache the mapping

    return jsonify({'short_url': short_url})

@app.route('/<short_url>', methods=['GET'])
def redirect_to_original(short_url):
    """Redirects to the original URL when given a shortened URL code."""
    # Check if the short_url is cached
    cache = get_cache_connection()
    cached_url = cache.get(short_url)
    if cached_url:
        return redirect(cached_url.decode())

    # Fetch from database if not in cache
    original_url = get_original_url(short_url)
    if original_url:
        cache.set(short_url, original_url)  # Cache the result
        return redirect(original_url)

    return jsonify({'error': 'URL not found'}), 404

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify(status="ok"), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)