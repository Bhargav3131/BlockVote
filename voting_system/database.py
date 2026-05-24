import sqlite3
import os
from blockchain import create_genesis_block

DB_PATH = os.path.join(os.path.dirname(__file__), "voting.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        tagline TEXT DEFAULT '',
        position TEXT NOT NULL,
        vote_count INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS election_state (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        election_name TEXT DEFAULT 'Student Council Election',
        is_active INTEGER DEFAULT 0,
        is_declared INTEGER DEFAULT 0,
        terminal_pin TEXT DEFAULT NULL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS registered_voters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prn TEXT UNIQUE NOT NULL,
        prn_hash TEXT UNIQUE NOT NULL,
        has_voted INTEGER DEFAULT 0,
        unlocked INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS blockchain (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        block_index INTEGER NOT NULL,
        previous_hash TEXT NOT NULL,
        timestamp REAL NOT NULL,
        voter_prn_hash TEXT NOT NULL,
        candidate_id INTEGER NOT NULL,
        hash TEXT NOT NULL
    )""")

    c.execute("INSERT OR IGNORE INTO admins (username, password, role) VALUES (?, ?, ?)", ("mainadmin", "admin@123", "main"))
    c.execute("INSERT OR IGNORE INTO admins (username, password, role) VALUES (?, ?, ?)", ("collegeadmin", "college@123", "college"))
    c.execute("INSERT OR IGNORE INTO election_state (id, election_name, is_active, is_declared) VALUES (1, 'Student Council Election', 0, 0)")

    c.execute("SELECT COUNT(*) as cnt FROM blockchain")
    if c.fetchone()["cnt"] == 0:
        g = create_genesis_block()
        c.execute("INSERT INTO blockchain (block_index, previous_hash, timestamp, voter_prn_hash, candidate_id, hash) VALUES (?,?,?,?,?,?)",
            (g["index"], g["previous_hash"], g["timestamp"], g["voter_prn_hash"], g["candidate_id"], g["hash"]))

    conn.commit()
    conn.close()

def get_election_state():
    conn = get_db()
    state = conn.execute("SELECT * FROM election_state WHERE id = 1").fetchone()
    conn.close()
    return dict(state)

def get_all_blocks():
    conn = get_db()
    rows = conn.execute("SELECT * FROM blockchain ORDER BY block_index ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_last_block():
    conn = get_db()
    row = conn.execute("SELECT * FROM blockchain ORDER BY block_index DESC LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else None
