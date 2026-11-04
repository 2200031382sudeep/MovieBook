# MovieBook – Movie Ticket Booking Website

HTML + CSS + JavaScript frontend, Python Flask backend (JSON API), MySQL database.

## Run it (Windows, VS Code)

1. Open this folder in VS Code (File > Open Folder), then Terminal > New Terminal.
2. `python -m venv venv`
3. `open cmd activate the virtual environment in scripts'
4. `pip install -r requirements.txt`
5. In MySQL (`mysql -u root -p`): `CREATE DATABASE moviebook_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;` then `exit`
6. `copy .env.example .env`, open `.env`, put your MySQL password in `DB_PASSWORD`
7. `python create_admin.py`  (creates your admin login)
8. `python seed_sample.py`   (optional: sample movies, theaters, showtimes)
9. `python app.py` and open http://localhost:5000

The tables are created automatically the first time the app starts.
