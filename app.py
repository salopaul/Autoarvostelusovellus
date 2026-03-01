from flask import Flask, render_template, request, redirect, session, abort
import sqlite3
import os
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(16))

DB = "database.db"


def init_db():
    if not os.path.exists(DB):
        db = sqlite3.connect(DB)
        with open("schema.sql") as f:
            db.executescript(f.read())
        db.close()


def get_db():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def check_csrf():
    if request.form.get("csrf_token") != session.get("csrf_token"):
        abort(403)


def require_login():
    if "user_id" not in session:
        return redirect("/login")


@app.route("/")
def index():
    if "user_id" not in session:
        return redirect("/login")

    q = request.args.get("q", "")
    db = get_db()

    cars = db.execute("""
        SELECT cars.id, cars.brand, cars.model, cars.year,
               cars.rating, cars.user_id, users.username
        FROM cars
        JOIN users ON cars.user_id = users.id
        WHERE cars.brand LIKE ? OR cars.model LIKE ?
        ORDER BY cars.id DESC
    """, (f"%{q}%", f"%{q}%")).fetchall()

    return render_template("index.html", cars=cars, query=q)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        if not username or not password:
            return "Kaikki kentät vaaditaan"

        hashed = generate_password_hash(password)
        db = get_db()

        try:
            db.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed)
            )
            db.commit()
            return redirect("/login")
        except sqlite3.IntegrityError:
            return "Käyttäjänimi on jo käytössä"

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        user = db.execute(
            "SELECT id, password FROM users WHERE username=?",
            (username,)
        ).fetchone()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["csrf_token"] = secrets.token_hex(16)
            return redirect("/")
        return "Virheellinen käyttäjänimi tai salasana"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/add", methods=["GET", "POST"])
def add():
    if "user_id" not in session:
        return redirect("/login")

    db = get_db()

    if request.method == "POST":
        check_csrf()

        brand = request.form["brand"].strip()
        model = request.form["model"].strip()
        year = request.form["year"]
        rating = request.form["rating"]
        categories = request.form.getlist("categories")

        if not brand or not model:
            return "Merkki ja malli vaaditaan"

        cursor = db.execute("""
            INSERT INTO cars (user_id, brand, model, year, rating)
            VALUES (?, ?, ?, ?, ?)
        """, (session["user_id"], brand, model, year, rating))

        car_id = cursor.lastrowid

        for cat_id in categories:
            db.execute("""
                INSERT INTO car_categories (car_id, category_id)
                VALUES (?, ?)
            """, (car_id, cat_id))

        db.commit()
        return redirect("/")

    categories = db.execute("SELECT id, name FROM categories").fetchall()
    return render_template("add.html", categories=categories)


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    if "user_id" not in session:
        return redirect("/login")

    db = get_db()

    car = db.execute("""
        SELECT id, brand, model, year, rating
        FROM cars
        WHERE id=? AND user_id=?
    """, (id, session["user_id"])).fetchone()

    if not car:
        abort(404)

    if request.method == "POST":
        check_csrf()

        brand = request.form["brand"]
        model = request.form["model"]
        year = request.form["year"]
        rating = request.form["rating"]
        categories = request.form.getlist("categories")

        db.execute("""
            UPDATE cars
            SET brand=?, model=?, year=?, rating=?
            WHERE id=? AND user_id=?
        """, (brand, model, year, rating, id, session["user_id"]))

        db.execute("DELETE FROM car_categories WHERE car_id=?", (id,))

        for cat_id in categories:
            db.execute("""
                INSERT INTO car_categories (car_id, category_id)
                VALUES (?, ?)
            """, (id, cat_id))

        db.commit()
        return redirect("/")

    categories = db.execute("SELECT id, name FROM categories").fetchall()
    selected = db.execute("""
        SELECT category_id FROM car_categories WHERE car_id=?
    """, (id,)).fetchall()

    selected_ids = {c["category_id"] for c in selected}

    return render_template("edit.html", car=car,
                           categories=categories,
                           selected_ids=selected_ids)


@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    if "user_id" not in session:
        return redirect("/login")

    check_csrf()
    db = get_db()

    db.execute("""
        DELETE FROM cars WHERE id=? AND user_id=?
    """, (id, session["user_id"]))

    db.commit()
    return redirect("/")


@app.route("/car/<int:car_id>", methods=["GET", "POST"])
def car_page(car_id):
    db = get_db()

    car = db.execute("""
        SELECT cars.id, cars.brand, cars.model, cars.year,
               cars.rating, cars.user_id, users.username
        FROM cars
        JOIN users ON cars.user_id = users.id
        WHERE cars.id=?
    """, (car_id,)).fetchone()

    if not car:
        abort(404)

    # Kommentin lisäys
    if request.method == "POST":
        if "user_id" not in session:
            return redirect("/login")

        check_csrf()

        content = request.form["content"].strip()

        if content:
            db.execute("""
                INSERT INTO comments (car_id, user_id, content, created_at)
                VALUES (?, ?, ?, datetime('now'))
            """, (car_id, session["user_id"], content))
            db.commit()

        return redirect(f"/car/{car_id}")

    comments = db.execute("""
        SELECT comments.content,
               comments.created_at,
               users.username
        FROM comments
        JOIN users ON comments.user_id = users.id
        WHERE comments.car_id=?
        ORDER BY comments.created_at DESC
    """, (car_id,)).fetchall()

    return render_template("car.html", car=car, comments=comments)


@app.route("/user/<int:user_id>")
def user_page(user_id):
    db = get_db()

    user = db.execute("""
        SELECT id, username FROM users WHERE id=?
    """, (user_id,)).fetchone()

    if not user:
        abort(404)

    cars = db.execute("""
        SELECT id, brand, model, rating
        FROM cars WHERE user_id=?
    """, (user_id,)).fetchall()

    count = db.execute("""
        SELECT COUNT(id) FROM cars WHERE user_id=?
    """, (user_id,)).fetchone()[0]

    avg = db.execute("""
        SELECT AVG(rating) FROM cars WHERE user_id=?
    """, (user_id,)).fetchone()[0]

    return render_template("user.html",
                           user=user,
                           cars=cars,
                           count=count,
                           avg=avg)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)