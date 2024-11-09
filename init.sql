CREATE TABLE public.urls (
    id SERIAL PRIMARY KEY,
    short_url  VARCHAR(10) UNIQUE NOT NULL,
    original_url text NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);