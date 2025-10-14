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
    return render_template("index.html", current_year=datetime.now().year)

@app.route("/contacts")
def contacts():
    return render_template("index.html", current_year=datetime.now().year)

@app.route("/resetdb")
def resetdb():
    """
    Delete the SQLite database file (if present), rebuild the schema,
    insert example data, run a few test queries and write their results
    to DEBUG_PATH (debug.txt), then redirect to home.
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

        # Insert example rows
        cur.execute("INSERT INTO Instrumentation (name) VALUES (?);", ("Solo Flute",))
        cur.execute("INSERT INTO Instrumentation (name) VALUES (?);", ("String Quartet",))
        cur.execute("INSERT INTO Instrument (name) VALUES (?);", ("Flute",))
        cur.execute("INSERT INTO Instrument (name) VALUES (?);", ("Violin",))
        cur.execute("INSERT INTO Instrument (name) VALUES (?);", ("Viola",))
        cur.execute("INSERT INTO Instrument (name) VALUES (?);", ("Cello",))

        # link instruments to instrumentations
        cur.execute("INSERT INTO HasInstrument (instrumentation_id, instrument_id, instrument_count) VALUES (?, ?, ?);", (1, 1, 1))
        cur.execute("INSERT INTO HasInstrument (instrumentation_id, instrument_id, instrument_count) VALUES (?, ?, ?);", (2, 2, 2))
        cur.execute("INSERT INTO HasInstrument (instrumentation_id, instrument_id, instrument_count) VALUES (?, ?, ?);", (2, 3, 1))
        cur.execute("INSERT INTO HasInstrument (instrumentation_id, instrument_id, instrument_count) VALUES (?, ?, ?);", (2, 4, 1))

        # example pieces using allowed difficulty_rating values; use None for NULL
        cur.execute(
            "INSERT INTO Piece (name, instrumentation, duration_seconds, year_of_composition, difficulty_rating) VALUES (?, ?, ?, ?, ?);",
            ("Meditation for Flute", 1, 210, 2018, 3.5)
        )
        cur.execute(
            "INSERT INTO Piece (name, instrumentation, duration_seconds, year_of_composition, difficulty_rating) VALUES (?, ?, ?, ?, ?);",
            ("Quartet in A", 2, 1260, 1799, 4)
        )
        cur.execute(
            "INSERT INTO Piece (name, instrumentation, duration_seconds, year_of_composition, difficulty_rating) VALUES (?, ?, ?, ?, ?);",
            ("Beginner Etude", 1, 90, 2021, 0.5)
        )
        cur.execute(
            "INSERT INTO Piece (name, instrumentation, duration_seconds, year_of_composition, difficulty_rating) VALUES (?, ?, ?, ?, ?);",
            ("Advanced Sonata", None, 1800, 2005, 6)
        )

        conn.commit()

        # Run test queries and write results to debug.txt
        with open(DEBUG_PATH, "w", encoding="utf-8") as dbg:
            # 1) Count pieces
            cur.execute("SELECT COUNT(*) AS cnt FROM Piece;")
            row = cur.fetchone()
            dbg.write(f"Total pieces: {row['cnt']}\n")

            # 2) List piece names with instrumentation name (NULL becomes 'None')
            cur.execute("""
                SELECT p.name AS piece, i.name AS instrumentation
                FROM Piece p
                LEFT JOIN Instrumentation i ON p.instrumentation = i.id
                ORDER BY p.id;
            """)
            dbg.write("\nPieces and instrumentations:\n")
            for r in cur.fetchall():
                instr = r["instrumentation"] if r["instrumentation"] is not None else "NULL"
                dbg.write(f"- {r['piece']}  |  {instr}\n")

            # 3) Aggregate instruments per instrumentation
            cur.execute("""
                SELECT ins.name AS instrumentation, COUNT(h.instrument_id) AS distinct_instruments, SUM(h.instrument_count) AS total_count
                FROM Instrumentation ins
                LEFT JOIN HasInstrument h ON ins.id = h.instrumentation_id
                GROUP BY ins.id
                ORDER BY ins.id;
            """)
            dbg.write("\nInstrumentation instrument counts:\n")
            for r in cur.fetchall():
                dbg.write(f"- {r['instrumentation']}  |  distinct_instruments={r['distinct_instruments']}  total_count={r['total_count']}\n")

            # 4) Pieces by difficulty rating (ordered)
            cur.execute("""
                SELECT difficulty_rating, COUNT(*) AS cnt
                FROM Piece
                GROUP BY difficulty_rating
                ORDER BY difficulty_rating;
            """)
            dbg.write("\nPieces by difficulty_rating:\n")
            for r in cur.fetchall():
                dbg.write(f"- difficulty={r['difficulty_rating']}  count={r['cnt']}\n")

            # 5) Example join: instruments used by 'String Quartet'
            cur.execute("""
                SELECT insr.name AS instrument, h.instrument_count
                FROM Instrumentation ins
                JOIN HasInstrument h ON ins.id = h.instrumentation_id
                JOIN Instrument insr ON h.instrument_id = insr.id
                WHERE ins.name = ?;
            """, ("String Quartet",))
            dbg.write("\nInstruments for String Quartet:\n")
            rows = cur.fetchall()
            if not rows:
                dbg.write("- (none)\n")
            else:
                for r in rows:
                    dbg.write(f"- {r['instrument']}  |  count={r['instrument_count']}\n")

        conn.close()
    except Exception as e:
        return f"Failed to (re)build database schema: {e}", 500

    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
