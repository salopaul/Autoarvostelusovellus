from flask import Flask, render_template, request, redirect, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "secret"  # tarve sessioille, ei poisteta

DB = "database.db"

# funktio tietokannan luomiseen
def init_db():
    if not os.path.exists(DB):
        db = sqlite3.connect(DB)
        with open("schema.sql") as f:
            db.executescript(f.read())
        db.close()

# funktio tietokantayhteyden saamiseen
def get_db():
    return sqlite3.connect(DB)

# rekisteröinti
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
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
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        if user:
            session["user_id"] = user[0]
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
    cars = db.execute(
        "SELECT * FROM cars WHERE brand LIKE ? OR model LIKE ?",
        (f"%{q}%", f"%{q}%")
    ).fetchall()
    return render_template("index.html", cars=cars, query=q)

# lisää auto
@app.route("/add", methods=["GET", "POST"])
def add():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        brand = request.form["brand"]
        model = request.form["model"]
        year = request.form["year"]
        rating = request.form["rating"]
        db = get_db()
        db.execute(
            "INSERT INTO cars (brand, model, year, rating) VALUES (?, ?, ?, ?)",
            (brand, model, year, rating)
        )
        db.commit()
        return redirect("/")
    return render_template("add.html")

# poista auto
@app.route("/delete/<int:id>")
def delete(id):
    if "user_id" not in session:
        return redirect("/login")

    db = get_db()
    db.execute("DELETE FROM cars WHERE id = ?", (id,))
    db.commit()
    return redirect("/")

if __name__ == "__main__":
    init_db()  # tietokanta luodaan tarvittaessa heti
    app.run(debug=True)
