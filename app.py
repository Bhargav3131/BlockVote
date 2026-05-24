from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from database import init_db, get_db, get_election_state, get_all_blocks, get_last_block
from blockchain import create_block, validate_chain, hash_prn
import os, random, string

app = Flask(__name__)
app.secret_key = "blockchain_voting_secret_2025"

# ── ROOT ──────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

# ── STATUS API ────────────────────────────────────────────────────────────────
@app.route("/api/status")
def api_status():
    conn = get_db()
    state = get_election_state()
    voted = conn.execute("SELECT COUNT(*) as c FROM registered_voters WHERE has_voted=1").fetchone()["c"]
    total = conn.execute("SELECT COUNT(*) as c FROM registered_voters").fetchone()["c"]
    conn.close()
    return jsonify({
        "is_active": state["is_active"],
        "is_declared": state["is_declared"],
        "election_name": state["election_name"],
        "voted_count": voted,
        "voter_count": total
    })

# ── TERMINAL UNLOCK STATUS (polling from /vote) ───────────────────────────────
@app.route("/api/terminal-status")
def api_terminal_status():
    """Called by the /vote kiosk every few seconds to check if a voter has been unlocked."""
    if not session.get("terminal_active"):
        return jsonify({"terminal_active": False})
    state = get_election_state()
    if not state["is_active"]:
        return jsonify({"terminal_active": True, "voter_ready": False, "election_active": False})
    # Check if any voter is currently unlocked (waiting to vote)
    conn = get_db()
    voter = conn.execute(
        "SELECT * FROM registered_voters WHERE unlocked=1 AND has_voted=0 LIMIT 1"
    ).fetchone()
    conn.close()
    if voter:
        return jsonify({"terminal_active": True, "voter_ready": True,
                        "election_active": True, "election_name": state["election_name"]})
    return jsonify({"terminal_active": True, "voter_ready": False,
                    "election_active": True, "election_name": state["election_name"]})

# ── MAIN ADMIN ────────────────────────────────────────────────────────────────
@app.route("/main-admin/login", methods=["GET", "POST"])
def main_admin_login():
    if request.method == "POST":
        u = request.form.get("username","").strip()
        p = request.form.get("password","").strip()
        conn = get_db()
        admin = conn.execute("SELECT * FROM admins WHERE username=? AND password=? AND role='main'",(u,p)).fetchone()
        conn.close()
        if admin:
            session["main_admin"] = u
            return redirect(url_for("main_admin_dashboard"))
        flash("Invalid credentials")
    return render_template("main_admin/login.html")

@app.route("/main-admin/dashboard")
def main_admin_dashboard():
    if "main_admin" not in session:
        return redirect(url_for("main_admin_login"))
    conn = get_db()
    candidates = conn.execute("SELECT * FROM candidates").fetchall()
    total_votes = conn.execute("SELECT SUM(vote_count) as t FROM candidates").fetchone()["t"] or 0
    voter_count = conn.execute("SELECT COUNT(*) as c FROM registered_voters").fetchone()["c"]
    voted_count = conn.execute("SELECT COUNT(*) as c FROM registered_voters WHERE has_voted=1").fetchone()["c"]
    conn.close()
    state = get_election_state()
    return render_template("main_admin/dashboard.html",
        candidates=candidates, state=state,
        total_votes=total_votes, voter_count=voter_count, voted_count=voted_count)

@app.route("/main-admin/add-candidate", methods=["POST"])
def add_candidate():
    if "main_admin" not in session:
        return redirect(url_for("main_admin_login"))
    if get_election_state()["is_active"]:
        flash("Cannot add candidates while election is active.")
        return redirect(url_for("main_admin_dashboard"))
    name = request.form.get("name","").strip()
    tagline = request.form.get("tagline","").strip()
    if name:
        conn = get_db()
        conn.execute("INSERT INTO candidates (name, tagline, position) VALUES (?,?,'Student Council President')",(name,tagline))
        conn.commit(); conn.close()
        flash(f"Candidate '{name}' added.")
    return redirect(url_for("main_admin_dashboard"))

@app.route("/main-admin/delete-candidate/<int:cid>", methods=["POST"])
def delete_candidate(cid):
    if "main_admin" not in session:
        return redirect(url_for("main_admin_login"))
    if get_election_state()["is_active"]:
        flash("Cannot delete while election is active.")
        return redirect(url_for("main_admin_dashboard"))
    conn = get_db()
    conn.execute("DELETE FROM candidates WHERE id=?",(cid,))
    conn.commit(); conn.close()
    flash("Candidate removed.")
    return redirect(url_for("main_admin_dashboard"))

# ── VOTER WHITELIST ───────────────────────────────────────────────────────────
@app.route("/main-admin/voters")
def manage_voters():
    if "main_admin" not in session:
        return redirect(url_for("main_admin_login"))
    conn = get_db()
    voters = conn.execute("SELECT * FROM registered_voters ORDER BY id").fetchall()
    conn.close()
    return render_template("main_admin/voters.html", voters=voters, state=get_election_state())

@app.route("/main-admin/add-voter", methods=["POST"])
def add_voter():
    if "main_admin" not in session:
        return redirect(url_for("main_admin_login"))
    if get_election_state()["is_active"]:
        flash("Cannot modify voter list while election is active.")
        return redirect(url_for("manage_voters"))
    raw = request.form.get("prns","").strip()
    prns = [p.strip().upper() for p in raw.replace(","," ").split() if p.strip()]
    conn = get_db()
    added = dupes = 0
    for prn in prns:
        try:
            conn.execute("INSERT INTO registered_voters (prn,prn_hash,has_voted,unlocked) VALUES (?,?,0,0)",(prn,hash_prn(prn)))
            added += 1
        except: dupes += 1
    conn.commit(); conn.close()
    flash(f"{added} voter(s) added." + (f" {dupes} duplicate(s) skipped." if dupes else ""))
    return redirect(url_for("manage_voters"))

@app.route("/main-admin/delete-voter/<int:vid>", methods=["POST"])
def delete_voter(vid):
    if "main_admin" not in session:
        return redirect(url_for("main_admin_login"))
    if get_election_state()["is_active"]:
        flash("Cannot delete voters while election is active.")
        return redirect(url_for("manage_voters"))
    conn = get_db()
    conn.execute("DELETE FROM registered_voters WHERE id=?",(vid,))
    conn.commit(); conn.close()
    flash("Voter removed.")
    return redirect(url_for("manage_voters"))

# ── ELECTION CONTROLS ─────────────────────────────────────────────────────────
@app.route("/main-admin/start-election", methods=["POST"])
def start_election():
    if "main_admin" not in session:
        return redirect(url_for("main_admin_login"))
    election_name = request.form.get("election_name","").strip()
    if not election_name:
        flash("Please provide an election name.")
        return redirect(url_for("main_admin_dashboard"))
    conn = get_db()
    if conn.execute("SELECT COUNT(*) as c FROM candidates").fetchone()["c"] < 2:
        conn.close(); flash("Add at least 2 candidates first.")
        return redirect(url_for("main_admin_dashboard"))
    if conn.execute("SELECT COUNT(*) as c FROM registered_voters").fetchone()["c"] < 1:
        conn.close(); flash("Add at least 1 registered voter first.")
        return redirect(url_for("main_admin_dashboard"))
    # Generate a terminal PIN — shown to admin, entered once on /vote to activate kiosk
    terminal_pin = ''.join(random.choices(string.digits, k=6))
    conn.execute("UPDATE election_state SET is_active=1, is_declared=0, election_name=?, terminal_pin=? WHERE id=1",
                 (election_name, terminal_pin))
    conn.commit(); conn.close()
    flash(f"Election '{election_name}' started! Terminal PIN: {terminal_pin}")
    return redirect(url_for("main_admin_dashboard"))

@app.route("/main-admin/stop-election", methods=["POST"])
def stop_election():
    if "main_admin" not in session:
        return redirect(url_for("main_admin_login"))
    conn = get_db()
    conn.execute("UPDATE election_state SET is_active=0, terminal_pin=NULL WHERE id=1")
    conn.commit(); conn.close()
    flash("Election stopped.")
    return redirect(url_for("main_admin_dashboard"))

@app.route("/main-admin/declare-results", methods=["POST"])
def declare_results():
    if "main_admin" not in session:
        return redirect(url_for("main_admin_login"))
    conn = get_db()
    conn.execute("UPDATE election_state SET is_declared=1, is_active=0, terminal_pin=NULL WHERE id=1")
    conn.commit(); conn.close()
    flash("Results declared!")
    return redirect(url_for("main_admin_results"))

@app.route("/main-admin/results")
def main_admin_results():
    if "main_admin" not in session:
        return redirect(url_for("main_admin_login"))
    conn = get_db()
    candidates = conn.execute("SELECT * FROM candidates ORDER BY vote_count DESC").fetchall()
    total = conn.execute("SELECT SUM(vote_count) as t FROM candidates").fetchone()["t"] or 0
    conn.close()
    return render_template("main_admin/results.html", candidates=candidates, total=total, state=get_election_state())

@app.route("/main-admin/verify-blockchain")
def verify_blockchain():
    if "main_admin" not in session:
        return jsonify({"error":"Unauthorized"}),401
    blocks = get_all_blocks()
    is_valid, message = validate_chain(blocks)
    return jsonify({"is_valid":is_valid,"message":message,"block_count":len(blocks)})

@app.route("/main-admin/blockchain")
def main_admin_blockchain():
    if "main_admin" not in session:
        return redirect(url_for("main_admin_login"))
    return render_template("main_admin/blockchain.html", blocks=get_all_blocks())

@app.route("/main-admin/reset-votes", methods=["POST"])
def reset_votes():
    if "main_admin" not in session:
        return redirect(url_for("main_admin_login"))
    conn = get_db()
    conn.execute("UPDATE candidates SET vote_count=0")
    conn.execute("UPDATE registered_voters SET has_voted=0, unlocked=0")
    conn.execute("DELETE FROM blockchain")
    conn.execute("UPDATE election_state SET is_active=0, is_declared=0, terminal_pin=NULL WHERE id=1")
    from blockchain import create_genesis_block
    g = create_genesis_block()
    conn.execute("INSERT INTO blockchain (block_index,previous_hash,timestamp,voter_prn_hash,candidate_id,hash) VALUES (?,?,?,?,?,?)",
        (g["index"],g["previous_hash"],g["timestamp"],g["voter_prn_hash"],g["candidate_id"],g["hash"]))
    conn.commit(); conn.close()
    flash("Votes reset. Candidates and voters preserved.")
    return redirect(url_for("main_admin_dashboard"))

@app.route("/main-admin/reset-full", methods=["POST"])
def reset_full():
    if "main_admin" not in session:
        return redirect(url_for("main_admin_login"))
    conn = get_db()
    conn.execute("DELETE FROM candidates")
    conn.execute("DELETE FROM registered_voters")
    conn.execute("DELETE FROM blockchain")
    conn.execute("UPDATE election_state SET is_active=0,is_declared=0,election_name='Student Council Election',terminal_pin=NULL WHERE id=1")
    from blockchain import create_genesis_block
    g = create_genesis_block()
    conn.execute("INSERT INTO blockchain (block_index,previous_hash,timestamp,voter_prn_hash,candidate_id,hash) VALUES (?,?,?,?,?,?)",
        (g["index"],g["previous_hash"],g["timestamp"],g["voter_prn_hash"],g["candidate_id"],g["hash"]))
    conn.commit(); conn.close()
    flash("Full system reset. All data cleared.")
    return redirect(url_for("main_admin_dashboard"))

@app.route("/main-admin/logout")
def main_admin_logout():
    session.pop("main_admin",None)
    return redirect(url_for("index"))

# ── COLLEGE ADMIN ─────────────────────────────────────────────────────────────
@app.route("/college-admin/login", methods=["GET","POST"])
def college_admin_login():
    if request.method == "POST":
        u = request.form.get("username","").strip()
        p = request.form.get("password","").strip()
        conn = get_db()
        admin = conn.execute("SELECT * FROM admins WHERE username=? AND password=? AND role='college'",(u,p)).fetchone()
        conn.close()
        if admin:
            session["college_admin"] = u
            return redirect(url_for("college_admin_dashboard"))
        flash("Invalid credentials")
    return render_template("college_admin/login.html")

@app.route("/college-admin/dashboard")
def college_admin_dashboard():
    if "college_admin" not in session:
        return redirect(url_for("college_admin_login"))
    return render_template("college_admin/dashboard.html", state=get_election_state())

@app.route("/college-admin/unlock-voter", methods=["POST"])
def unlock_voter():
    if "college_admin" not in session:
        return jsonify({"success":False,"message":"Unauthorized"}),401
    state = get_election_state()
    if not state["is_active"]:
        return jsonify({"success":False,"message":"Election is not currently active."})
    prn = request.form.get("prn","").strip().upper()
    if not prn:
        return jsonify({"success":False,"message":"Please enter a PRN."})
    prn_hash = hash_prn(prn)
    conn = get_db()
    voter = conn.execute("SELECT * FROM registered_voters WHERE prn_hash=?",(prn_hash,)).fetchone()
    if not voter:
        conn.close()
        return jsonify({"success":False,"message":f"PRN {prn} is not registered."})
    if voter["has_voted"]:
        conn.close()
        return jsonify({"success":False,"message":f"PRN {prn} has already voted."})
    # Unlock this voter — terminal will detect it automatically via polling
    conn.execute("UPDATE registered_voters SET unlocked=1 WHERE prn_hash=?",(prn_hash,))
    conn.commit(); conn.close()
    return jsonify({"success":True,"message":f"PRN {prn} verified. Ballot is now live on the voting terminal."})

@app.route("/college-admin/logout")
def college_admin_logout():
    session.pop("college_admin",None)
    return redirect(url_for("index"))

# ── VOTING TERMINAL (kiosk) ───────────────────────────────────────────────────
@app.route("/vote")
def voting_terminal():
    state = get_election_state()
    conn = get_db()
    candidates = conn.execute("SELECT * FROM candidates").fetchall()
    conn.close()
    terminal_active = session.get("terminal_active", False)
    return render_template("voting/terminal.html",
        candidates=candidates,
        election_name=state.get("election_name","Student Council Election"),
        terminal_active=terminal_active,
        is_active=state["is_active"])

@app.route("/vote/activate", methods=["POST"])
def activate_terminal():
    """One-time PIN entry to activate this browser as a trusted voting terminal."""
    pin = request.form.get("pin","").strip()
    state = get_election_state()
    if not state["is_active"]:
        return jsonify({"success":False,"message":"Election is not active."})
    if not state["terminal_pin"] or pin != state["terminal_pin"]:
        return jsonify({"success":False,"message":"Invalid PIN."})
    session["terminal_active"] = True
    session.permanent = True
    return jsonify({"success":True,"election_name":state["election_name"]})

@app.route("/vote/submit", methods=["POST"])
def submit_vote():
    if not session.get("terminal_active"):
        return jsonify({"success":False,"message":"Terminal not activated."})
    state = get_election_state()
    if not state["is_active"]:
        return jsonify({"success":False,"message":"Election is not active."})
    candidate_id = request.form.get("candidate_id")
    if not candidate_id:
        return jsonify({"success":False,"message":"Please select a candidate."})
    # Find the currently unlocked voter
    conn = get_db()
    voter = conn.execute("SELECT * FROM registered_voters WHERE unlocked=1 AND has_voted=0 LIMIT 1").fetchone()
    if not voter:
        conn.close()
        return jsonify({"success":False,"message":"No voter is currently unlocked."})
    candidate = conn.execute("SELECT * FROM candidates WHERE id=?",(candidate_id,)).fetchone()
    if not candidate:
        conn.close()
        return jsonify({"success":False,"message":"Invalid candidate."})
    last_block = get_last_block()
    new_block = create_block(last_block["block_index"]+1, last_block["hash"], voter["prn_hash"], candidate["id"])
    conn.execute("INSERT INTO blockchain (block_index,previous_hash,timestamp,voter_prn_hash,candidate_id,hash) VALUES (?,?,?,?,?,?)",
        (new_block["index"],new_block["previous_hash"],new_block["timestamp"],
         new_block["voter_prn_hash"],new_block["candidate_id"],new_block["hash"]))
    conn.execute("UPDATE registered_voters SET has_voted=1, unlocked=0 WHERE prn_hash=?",(voter["prn_hash"],))
    conn.execute("UPDATE candidates SET vote_count=vote_count+1 WHERE id=?",(candidate_id,))
    conn.commit(); conn.close()
    return jsonify({"success":True,"candidate_name":candidate["name"]})

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
