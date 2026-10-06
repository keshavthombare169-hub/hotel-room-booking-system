from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path

from flask import Flask, jsonify, render_template, request


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "library.db"

app = Flask(__name__)


def get_db() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def book_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def init_db() -> None:
    with closing(get_db()) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                isbn TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                availability_status TEXT NOT NULL DEFAULT 'Available'
                    CHECK (availability_status IN ('Available', 'Issued')),
                member_id INTEGER,
                issued_on TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE SET NULL
            );
            """
        )
        if db.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 0:
            db.executemany(
                "INSERT INTO books (title, author, isbn, category) VALUES (?, ?, ?, ?)",
                [
                    ("The Alchemist", "Paulo Coelho", "9780061122415", "Fiction"),
                    ("Atomic Habits", "James Clear", "9780735211292", "Self Help"),
                    ("Clean Code", "Robert C. Martin", "9780132350884", "Technology"),
                    ("Wings of Fire", "A. P. J. Abdul Kalam", "9788173711466", "Biography"),
                ],
            )
        db.commit()


def error(message: str, status: int = 400):
    return jsonify({"error": message}), status


def valid_email(value: str) -> bool:
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value))


def book_with_member(db: sqlite3.Connection, book_id: int):
    return db.execute(
        """
        SELECT b.id, b.title, b.author, b.isbn, b.category, b.availability_status,
               b.issued_on, m.id AS member_id, m.name AS member_name, m.email AS member_email
        FROM books b
        LEFT JOIN members m ON m.id = b.member_id
        WHERE b.id = ?
        """,
        (book_id,),
    ).fetchone()


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/books")
def list_books():
    query = request.args.get("q", "").strip()
    status = request.args.get("status", "All")
    sql = """
        SELECT b.id, b.title, b.author, b.isbn, b.category, b.availability_status,
               b.issued_on, m.id AS member_id, m.name AS member_name, m.email AS member_email
        FROM books b LEFT JOIN members m ON m.id = b.member_id
    """
    conditions, params = [], []
    if query:
        conditions.append("(b.title LIKE ? OR b.author LIKE ? OR b.isbn LIKE ? OR b.category LIKE ?)")
        params.extend([f"%{query}%"] * 4)
    if status in {"Available", "Issued"}:
        conditions.append("b.availability_status = ?")
        params.append(status)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY b.title COLLATE NOCASE"
    with closing(get_db()) as db:
        books = [book_to_dict(row) for row in db.execute(sql, params).fetchall()]
    return jsonify(books)


@app.get("/api/stats")
def stats():
    with closing(get_db()) as db:
        total = db.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        available = db.execute("SELECT COUNT(*) FROM books WHERE availability_status = 'Available'").fetchone()[0]
        members = db.execute("SELECT COUNT(*) FROM members").fetchone()[0]
    return jsonify({"total": total, "available": available, "issued": total - available, "members": members})


@app.post("/api/books")
def add_book():
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    author = str(data.get("author", "")).strip()
    isbn = str(data.get("isbn", "")).strip()
    category = str(data.get("category", "")).strip()
    if not all([title, author, isbn, category]):
        return error("Please complete all book details.")
    if len(isbn) < 6:
        return error("Enter a valid ISBN (at least 6 characters).")
    with closing(get_db()) as db:
        try:
            cursor = db.execute(
                "INSERT INTO books (title, author, isbn, category) VALUES (?, ?, ?, ?)",
                (title, author, isbn, category),
            )
            db.commit()
            row = book_with_member(db, cursor.lastrowid)
        except sqlite3.IntegrityError:
            return error("A book with that ISBN already exists.")
    return jsonify(book_to_dict(row)), 201


@app.post("/api/books/<int:book_id>/issue")
def issue_book(book_id: int):
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    if not name or not email:
        return error("Member name and email are required.")
    if not valid_email(email):
        return error("Enter a valid member email address.")
    with closing(get_db()) as db:
        book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if not book:
            return error("Book not found.", 404)
        if book["availability_status"] != "Available":
            return error("This book has already been issued.")
        member = db.execute("SELECT id FROM members WHERE email = ?", (email,)).fetchone()
        if member:
            member_id = member["id"]
            db.execute("UPDATE members SET name = ? WHERE id = ?", (name, member_id))
        else:
            member_id = db.execute("INSERT INTO members (name, email) VALUES (?, ?)", (name, email)).lastrowid
        db.execute(
            "UPDATE books SET availability_status = 'Issued', member_id = ?, issued_on = ? WHERE id = ?",
            (member_id, date.today().isoformat(), book_id),
        )
        db.commit()
        row = book_with_member(db, book_id)
    return jsonify(book_to_dict(row))


@app.post("/api/books/<int:book_id>/return")
def return_book(book_id: int):
    with closing(get_db()) as db:
        book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if not book:
            return error("Book not found.", 404)
        if book["availability_status"] != "Issued":
            return error("This book has not been issued.")
        db.execute(
            "UPDATE books SET availability_status = 'Available', member_id = NULL, issued_on = NULL WHERE id = ?",
            (book_id,),
        )
        db.commit()
        row = book_with_member(db, book_id)
    return jsonify(book_to_dict(row))


@app.delete("/api/books/<int:book_id>")
def delete_book(book_id: int):
    with closing(get_db()) as db:
        result = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
    if result.rowcount == 0:
        return error("Book not found.", 404)
    return "", 204


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
