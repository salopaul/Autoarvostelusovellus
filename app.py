from flask import Flask, render_template, request, redirect, session, abort
import sqlite3
import os
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret"

DB = "database.db"



# funktio tietokannan luomiseen
def init_db():
    if not os.path.exists(DB):
        db = sqlite3.connect(DB)
        with open("schema.sql") as f:
            db.executescript(f.read())
        db.close()


def get_db():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db

# CSRF-suojaus
def check_csrf():
    if request.form.get("csrf_token") != session.get("csrf_token"):
        abort(403)

# rekisteröinti
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

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

# kirjautuminen
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["csrf_token"] = secrets.token_hex(16)
            return redirect("/")
        else:
            return "Virheellinen käyttäjänimi tai salasana"

    return render_template("login.html")

# uloskirjautuminen
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# etusivu ja haku
@app.route("/")
def index():
    if "user_id" not in session:
        return redirect("/login")

    q = request.args.get("q", "")
    db = get_db()

    cars = db.execute("""
        SELECT cars.*, users.username
        FROM cars
        JOIN users ON cars.user_id = users.id
        WHERE brand LIKE ? OR model LIKE ?
    """, (f"%{q}%", f"%{q}%")).fetchall()

    return render_template("index.html", cars=cars, query=q)

# lisää auto
@app.route("/add", methods=["GET", "POST"])
def add():
    if "user_id" not in session:
        return redirect("/login")

    db = get_db()

    if request.method == "POST":
        check_csrf()

        brand = request.form["brand"]
        model = request.form["model"]
        year = request.form["year"]
        rating = request.form["rating"]
        categories = request.form.getlist("categories")

        cursor = db.execute(
            "INSERT INTO cars (user_id, brand, model, year, rating) VALUES (?, ?, ?, ?, ?)",
            (session["user_id"], brand, model, year, rating)
        )

        car_id = cursor.lastrowid

        for cat_id in categories:
            db.execute(
                "INSERT INTO car_categories (car_id, category_id) VALUES (?, ?)",
                (car_id, cat_id)
            )

        db.commit()
        return redirect("/")

    categories = db.execute("SELECT * FROM categories").fetchall()
    return render_template("add.html", categories=categories)

# muokkaa autoa 
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):    
    if "user_id" not in session:
        return redirect("/login")

    db = get_db()
    car = db.execute(
        "SELECT * FROM cars WHERE id=? AND user_id=?",
        (id, session["user_id"])
    ).fetchone()

    if not car:
        abort(404)

    if request.method == "POST":
        check_csrf()

        brand = request.form["brand"]
        model = request.form["model"]
        year = request.form["year"]
        rating = request.form["rating"]
        categories = request.form.getlist("categories")

        db.execute(
            "UPDATE cars SET brand=?, model=?, year=?, rating=? WHERE id=? AND user_id=?",
            (brand, model, year, rating, id, session["user_id"])
        )

        db.execute("DELETE FROM car_categories WHERE car_id=?", (id,))
        for cat_id in categories:
            db.execute(
                "INSERT INTO car_categories (car_id, category_id) VALUES (?, ?)",
                (id, cat_id)
            )

        db.commit()
        return redirect("/")

    categories = db.execute("SELECT * FROM categories").fetchall()
    selected_cats = db.execute(
        "SELECT category_id FROM car_categories WHERE car_id=?",
        (id,)
    ).fetchall()
    selected_cats = {c["category_id"] for c in selected_cats}

    return render_template("edit.html", car=car, categories=categories, selected_cats=selected_cats)

# poista auto
@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    if "user_id" not in session:
        return redirect("/login")

    check_csrf()

    db = get_db()
    db.execute(
        "DELETE FROM cars WHERE id=? AND user_id=?",
        (id, session["user_id"])
    )
    db.commit()
    return redirect("/")

if __name__ == "__main__":
    init_db()  # tietokanta luodaan tarvittaessa heti
    app.run(debug=True)
