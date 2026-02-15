CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
);

CREATE TABLE cars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    brand TEXT,
    model TEXT,
    year INTEGER,
    rating INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
);

CREATE TABLE car_categories (
    car_id INTEGER,
    category_id INTEGER,
    PRIMARY KEY (car_id, category_id),
    FOREIGN KEY (car_id) REFERENCES cars(id),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE TABLE comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    car_id INTEGER,
    user_id INTEGER,
    content TEXT,
    created_at TEXT,
    FOREIGN KEY (car_id) REFERENCES cars(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

INSERT INTO categories (name) VALUES ('Sähköauto');
INSERT INTO categories (name) VALUES ('Urheiluauto');
INSERT INTO categories (name) VALUES ('Perheauto');
INSERT INTO categories (name) VALUES ('Maastoauto');