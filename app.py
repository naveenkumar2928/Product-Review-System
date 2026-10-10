
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change-this-to-a-random-secret-key"

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "reviews.db"


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                review_text TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("Please fill in all fields.", "error")
            return redirect(url_for("register"))

        try:
            with get_db() as conn:
                conn.execute("""
                    INSERT INTO users (username, email, password)
                    VALUES (?, ?, ?)
                """, (
                    username,
                    email,
                    generate_password_hash(password)
                ))

            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("Username or email already exists.", "error")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        with get_db() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            ).fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Welcome back!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out.", "success")
    return redirect(url_for("index"))


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))

    with get_db() as conn:
        total_reviews = conn.execute(
            "SELECT COUNT(*) FROM reviews"
        ).fetchone()[0]

        total_products = conn.execute(
            "SELECT COUNT(DISTINCT product_name) FROM reviews"
        ).fetchone()[0]

        average_rating = conn.execute(
            "SELECT AVG(rating) FROM reviews"
        ).fetchone()[0] or 0

        product_stats = conn.execute("""
            SELECT product_name,
                   COUNT(*) AS review_count,
                   ROUND(AVG(rating), 1) AS average_rating
            FROM reviews
            GROUP BY product_name
            ORDER BY review_count DESC
        """).fetchall()

        recent_reviews = conn.execute("""
            SELECT reviews.*, users.username
            FROM reviews
            JOIN users ON reviews.user_id = users.id
            ORDER BY reviews.id DESC
            LIMIT 5
        """).fetchall()

        rating_counts = conn.execute("""
            SELECT rating, COUNT(*) AS total
            FROM reviews
            GROUP BY rating
        """).fetchall()

    return render_template(
        "dashboard.html",
        total_reviews=total_reviews,
        total_products=total_products,
        average_rating=round(average_rating, 1),
        product_stats=product_stats,
        recent_reviews=recent_reviews,
        rating_counts=rating_counts
    )


@app.route("/add_review", methods=["GET", "POST"])
def add_review():
    if "user_id" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        product_name = request.form.get("product_name", "").strip()
        review_text = request.form.get("review_text", "").strip()

        try:
            rating = int(request.form.get("rating", "0"))
        except ValueError:
            rating = 0

        allowed_products = [
            "Wireless Headphones",
            "Smart Watch",
            "Bluetooth Speaker"
        ]

        if product_name not in allowed_products:
            flash("Please select a valid product.", "error")
        elif rating not in range(1, 6):
            flash("Please select a rating from 1 to 5.", "error")
        elif not review_text:
            flash("Please write your review.", "error")
        else:
            with get_db() as conn:
                conn.execute("""
                    INSERT INTO reviews
                    (user_id, product_name, rating, review_text)
                    VALUES (?, ?, ?, ?)
                """, (
                    session["user_id"],
                    product_name,
                    rating,
                    review_text
                ))

            flash("Your review has been added!", "success")
            return redirect(url_for("reviews"))

    return render_template("add_review.html")


@app.route("/reviews")
def reviews():
    if "user_id" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))

    with get_db() as conn:
        all_reviews = conn.execute("""
            SELECT reviews.*, users.username
            FROM reviews
            JOIN users ON reviews.user_id = users.id
            ORDER BY reviews.id DESC
        """).fetchall()

    return render_template("reviews.html", reviews=all_reviews)

print("Database file:", DB_PATH)

init_db()

if __name__ == "__main__":
    app.run(debug=True)