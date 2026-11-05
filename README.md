# BookMyShow – Movie Ticket Booking System

A clean, modern, responsive Movie Ticket Booking System designed after the BookMyShow interface.

Built with **HTML5, CSS3, JavaScript (Vanilla ES6+), Python Flask, SQLAlchemy, and MySQL**.

---

## 🌟 Key Features

### 👤 User Portal
1. **Home Page**: Hero banner carousel with trending blockbusters, city selector, and search.
2. **Browse Movies**: Filter movies by City, Language (Telugu, Hindi, English, Tamil) and Genre (Action, Comedy, Drama, Sci-Fi).
3. **View Movie Details**: Cinematic backdrop header with movie poster, rating, format chips (2D, 3D, IMAX), synopsis, and 7-day date selector.
4. **Select Theater & Shows**: Cinema screens with amenities (M-Ticket, 4K Dolby Atmos) and BookMyShow-style green showtime buttons.
5. **Select Seats**: Realistic theater seat grid with screen curve (*"All eyes this way please!"*), categories, real-time total calculation, and double-booking prevention.
6. **Booking Summary**: Review movie, cinema, show date/time, selected seats, ticket price, and total amount before paying.
7. **Confirm Booking**: Instant reservation with unique booking reference (`#BMS-...`).
8. **My Bookings / Digital M-Ticket**: Boarding-pass styled digital ticket with QR code simulation, seat details, and cancel option (before show commences).
9. **Profile Slide-Down**: Smooth slide-down menu with quick access to Bookings, Theaters, City Switcher, and Logout.

### 🛡️ Admin Portal (`/admin`)
1. **Admin Dashboard**: Real-time overview of Total Revenue (₹), Total Bookings, Active Movies, Theaters, and Upcoming Showtimes with recent activity logs.
2. **Manage Movies**: Add, edit, toggle active status, and delete movies with poster URLs and synopses.
3. **Manage Theaters**: Add, edit, and delete cinema halls with custom rows and seats-per-row layouts.
4. **Manage Shows & Timings**: Schedule future showtimes with conflict detection (prevents overlapping shows in the same hall).
5. **Manage Ticket Prices**: Set and edit ticket prices in INR (₹) directly per showtime.
6. **View & Manage Bookings**: Search customer bookings by reference, email, or movie, filter by status, and cancel bookings if requested.
7. **Secure Logout**: Direct sign-out from Admin header and tabs.

---

## 🚀 Quick Start Guide

### 1. Requirements
- Python 3.9+
- MySQL Server (running locally on port 3306)

### 2. Setup
```powershell
# Navigate to project folder
cd "C:\Users\spsud\Downloads\MovieBook\MovieBook"

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Configuration
Ensure your MySQL credentials match `.env`:
```ini
SECRET_KEY=your-secret-key
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=movibook_db
```

### 4. Create Admin Account (One-Time)
```powershell
python create_admin.py
```

### 5. Run the Application
```powershell
python app.py
```
Open your browser at: **http://127.0.0.1:5000**

---

## 📁 Clean Project Architecture

```
MovieBook/
├── app.py                  # Flask Application factory & routing setup
├── config.py               # Environment configuration
├── extensions.py           # SQLAlchemy database instance
├── models.py               # Database models (User, Movie, Theater, Showtime, Booking, BookingSeat)
├── utils.py                # Authentication helpers & decorators
├── create_admin.py         # Admin user creation CLI
├── seed_sample.py          # Sample data population
├── routes/
│   ├── __init__.py         # Blueprint registration
│   ├── pages.py            # User-facing HTML page routes
│   ├── api_public.py       # Public & Customer JSON APIs (auth, movies, seats, bookings)
│   └── api_admin.py        # Admin JSON APIs (dashboard, movies, theaters, showtimes, bookings)
├── static/
│   ├── css/
│   │   └── style.css       # Complete BookMyShow responsive design system
│   └── js/
│       └── common.js       # Core frontend helpers, profile slide-down & city modal
└── templates/
    ├── base.html           # Master layout with BookMyShow header & profile slide-down
    ├── index.html          # Homepage with carousel & recommended movies
    ├── movie.html          # Movie details & showtimes listing
    ├── book.html           # Interactive seat map & booking summary modal
    ├── booking.html        # Digital M-Ticket confirmation pass
    ├── my_bookings.html    # Customer booking history
    ├── theaters.html       # Cinema hall explorer
    ├── login.html          # Sign-in portal
    ├── register.html       # Customer registration
    ├── admin.html          # Admin dashboard & management portal
    └── error.html          # 404, 403 & 500 error page
```
