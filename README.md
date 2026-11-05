# MovieBook – Movie Ticket Booking Website

HTML + CSS + JavaScript frontend, Python Flask backend (JSON API), MySQL database.

## Features
- **Users:** register / login, then land on **Find theaters** – a search bar for the theater name plus a **Location** box (city or area). Type a location and only the theaters there are shown (with the movies they are playing).
- **Movies page:** pick a **location** from the dropdown; only movies with upcoming shows in that city are listed. Your choice is remembered in the browser.
- **Booking:** choose seats on a seat map, book, view / cancel in *My bookings*. Double-booking is impossible (database rule).
- **Admin panel** (`/admin`): add / hide / delete movies, add theaters **with a city**, add showtimes, see all bookings.

## Run it (Windows, VS Code)

1. Open this folder in VS Code (File > Open Folder), then Terminal > New Terminal.
2. `python -m venv venv`
3. `open cmd activate the virtual environment in scripts'
4. `pip install -r requirements.txt`
5. In MySQL (`mysql -u root -p`): `CREATE DATABASE moviebook_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;` then `exit`
6. `copy .env.example .env`, open `.env`, put your MySQL password in `DB_PASSWORD`
7. `python create_admin.py`  (creates your admin login)
8. `python seed_sample.py`   (optional: sample movies, theaters in Bengaluru / Hyderabad / Mumbai, showtimes)
9. `python app.py` and open http://localhost:5000

The tables are created automatically the first time the app starts.

## Already had a database from before the location feature?

Run this **once** to add the new `city` column to the theaters table:

```
python migrate_add_city.py
```

All your existing theaters get the city "Bengaluru". Change them in MySQL, e.g.
`UPDATE theaters SET city='Hyderabad' WHERE id=3;` (or delete and re-add them in the Admin panel).
If you want fresh sample data instead, drop and re-create the database (step 5) and run steps 7-8 again.

## Where things are

| File / folder | What it does |
|---|---|
| `app.py` | Starts the website |
| `models.py` | Database tables (users, movies, theaters with `city`, showtimes, bookings) |
| `routes/pages.py` | The HTML pages |
| `routes/api_public.py` | Login, movies (`?city=`), cities, seats, bookings |
| `routes/api_admin.py` | Admin API |
| `theater_search.py` | The **Find theaters** page and its search API |
| `templates/`, `static/` | Page layouts, CSS and JavaScript |
| `migrate_add_city.py` | One-time upgrade for an older database |

Never commit your real `.env` (it is already in `.gitignore`).
