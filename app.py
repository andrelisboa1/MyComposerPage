from flask import Flask, render_template, redirect, url_for
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)
DB_PATH = "music.db"
DEBUG_PATH = "debug.txt"

def get_db_connection(path=DB_PATH):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@app.route("/")
def home():
    return render_template("index.html", current_year=datetime.now().year)

@app.route("/about")
def about():
    return render_template("about.html", current_year=datetime.now().year)

@app.route("/works")
def works():
    return render_template("works.html", current_year=datetime.now().year, compositions=get_piece_list())

@app.route("/contacts")
def contacts():
    return render_template("index.html", current_year=datetime.now().year)

@app.route("/resetdb")
def resetdb():
    """
    Delete the SQLite database file (if present), rebuild the schema,
    then insert demo data and redirect to home.
    """
    # remove existing database file
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except OSError:
            return "Failed to remove existing database file.", 500

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Instrumentation table
        cur.execute("""
        CREATE TABLE Instrumentation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
        """)

        # Instrument table
        cur.execute("""
        CREATE TABLE Instrument (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
        """)

        # HasInstrument associative table linking Instrumentation <-> Instrument
        cur.execute("""
        CREATE TABLE HasInstrument (
            instrumentation_id INTEGER NOT NULL,
            instrument_id INTEGER NOT NULL,
            instrument_count INTEGER NOT NULL DEFAULT 1 CHECK(instrument_count >= 0),
            PRIMARY KEY (instrumentation_id, instrument_id),
            FOREIGN KEY (instrumentation_id) REFERENCES Instrumentation(id) ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (instrument_id) REFERENCES Instrument(id) ON DELETE RESTRICT ON UPDATE CASCADE
        );
        """)

        # Piece table referencing Instrumentation
        cur.execute("""
        CREATE TABLE Piece (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            instrumentation INTEGER,
            duration_seconds INTEGER,
            year_of_composition INTEGER,
            difficulty_rating REAL NOT NULL CHECK(difficulty_rating IN (0.5,1,1.5,2,2.5,3,3.5,4,4.5,5,5.5,6)),
            FOREIGN KEY (instrumentation) REFERENCES Instrumentation(id) ON DELETE SET NULL ON UPDATE CASCADE
        );
        """)

        conn.commit()
        conn.close()
    except Exception as e:
        return f"Failed to (re)build database schema: {e}", 500

    # Some inserts to test stuff out!
    add_instrument("Flute")
    add_instrument("Violin")
    add_instrument("Viola")
    add_instrument("Cello")

    add_instrumentation("Solo Flute", [("Flute", 1)])
    add_instrumentation("String Quartet", [("Violin", 2), ("Viola", 1), ("Cello", 1)])

    add_piece("Meditation for Flute", "Solo Flute", 210, 2018, 3.5)
    add_piece("Quartet in A", "String Quartet", 1260, 1799, 4)
    add_piece("Beginner Etude", "Solo Flute", 90, 2021, 0.5)
    add_piece("Advanced Sonata", None, 1800, 2005, 6)

    return redirect(url_for("home"))

# Adds an instrument entry.
def add_instrument(name):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO Instrument (name) VALUES (?);", (name,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        print(f"Error adding instrument: {e}")
        return False

# Adds an instrumentation entry. Also does the association.
# 'instruments' is a list of tuples (instrument_name, instrument_count)
def add_instrumentation(name, instruments):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO Instrumentation (name) VALUES (?);", (name,))
        instrumentation_id = cur.lastrowid

        for instrument_name, instrument_count in instruments:
            cur.execute("SELECT id FROM Instrument WHERE name = ?;", (instrument_name,))
            row = cur.fetchone()
            if row:
                instrument_id = row["id"]
                cur.execute("""
                    INSERT INTO HasInstrument (instrumentation_id, instrument_id, instrument_count)
                    VALUES (?, ?, ?);
                """, (instrumentation_id, instrument_id, instrument_count))
            else:
                print(f"Instrument '{instrument_name}' not found. Skipping association.")

        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        print(f"Error adding instrumentation: {e}")
        return False

# Adds a new piece. Does all needed associations.
def add_piece(name, instrumentation_name, duration_seconds, year_of_composition, difficulty_rating):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        instrumentation_id = None
        if instrumentation_name:
            cur.execute("SELECT id FROM Instrumentation WHERE name = ?;", (instrumentation_name,))
            row = cur.fetchone()
            if row:
                instrumentation_id = row["id"]
            else:
                print(f"Instrumentation '{instrumentation_name}' not found. Setting to NULL.")

        cur.execute("""
            INSERT INTO Piece (name, instrumentation, duration_seconds, year_of_composition, difficulty_rating)
            VALUES (?, ?, ?, ?, ?);
        """, (name, instrumentation_id, duration_seconds, year_of_composition, difficulty_rating))

        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        print(f"Error adding piece: {e}")
        return False
    
def get_piece_list():
    """
    Return a list of pieces as plain dicts suitable for templates.
    If the database file or table does not exist, return an empty list
    and log a helpful message.
    """
    pieces = []
    if not os.path.exists(DB_PATH):
        print("get_piece_list: database file not found; returning empty list.")
        return pieces

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT name, year_of_composition, difficulty_rating FROM Piece ORDER BY id;")
        rows = cur.fetchall()
        for r in rows:
            pieces.append({
                "name": r["name"],
                "year_of_composition": r["year_of_composition"],
                "difficulty_rating": r["difficulty_rating"]
            })
        conn.close()
        print(f"get_piece_list: retrieved {len(pieces)} pieces.")
    except Exception as e:
        print(f"Error retrieving piece list: {e}")

    return pieces



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
