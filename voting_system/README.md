# ⛓️ BlockVote — Blockchain-Based Voting System
**Final Year Project | Tilak Maharashtra Vidyapeeth University, Pune**
*Bhargav Sunil Kalbhor (PRN: 04423000726) & Komal Umesh Teli (PRN: 04423000835)*

---

## 🚀 Setup & Run

### Step 1 — Install Python
Make sure Python 3.8+ is installed. Download from: https://python.org

### Step 2 — Install Flask
Open terminal/command prompt in this folder and run:
```
pip install flask
```

### Step 3 — Run the App
```
python app.py
```

### Step 4 — Open in Browser
Visit: http://localhost:5000

---

## 🔑 Default Login Credentials

| Role           | Username       | Password      |
|----------------|----------------|---------------|
| Main Admin     | mainadmin      | admin@123     |
| College Admin  | collegeadmin   | college@123   |

> ⚠️ Change these passwords in `database.py` before deploying.

---

## 📋 How to Run an Election (Step-by-Step)

### Phase 1 — Setup (Main Admin)
1. Login as Main Admin → http://localhost:5000/main-admin/login
2. Add at least 2 candidates (name only)
3. Click **Start Election**

### Phase 2 — Voting (College Admin + Voter)
1. Login as College Admin → http://localhost:5000/college-admin/login
2. Student presents ID card
3. Enter student's PRN number → Click **Verify & Unlock Terminal**
4. Voting terminal opens automatically
5. Student selects candidate → Clicks **Submit Vote**
6. Success screen shown → Terminal resets after 5 seconds
7. Repeat for next student

### Phase 3 — Results (Main Admin)
1. Click **Stop Election** when voting is complete
2. Click **Declare Results** to officially announce winner
3. View **Blockchain** tab to validate all votes are intact

---

## 🗂️ Project Structure

```
voting_system/
│
├── app.py              ← Main Flask application (all routes)
├── blockchain.py       ← SHA-256 blockchain logic
├── database.py         ← SQLite database setup & helpers
├── requirements.txt    ← Python dependencies
├── voting.db           ← SQLite database (auto-created on first run)
│
├── static/
│   └── css/
│       └── style.css   ← All styling
│
└── templates/
    ├── index.html                    ← Home / portal selection
    ├── main_admin/
    │   ├── login.html                ← Main admin login
    │   ├── dashboard.html            ← Manage candidates & election
    │   ├── results.html              ← Live vote tally & winner
    │   └── blockchain.html           ← Blockchain ledger viewer
    ├── college_admin/
    │   ├── login.html                ← College admin login
    │   └── dashboard.html            ← PRN verification terminal
    └── voting/
        └── terminal.html             ← Student voting screen
```

---

## ⛓️ Blockchain Implementation

Each vote creates a new **block** with:
- **Block Index** — position in the chain
- **Timestamp** — exact time of vote
- **Voter PRN Hash** — SHA-256 hash of PRN (privacy preserved)
- **Candidate ID & Name** — who was voted for
- **Previous Hash** — links to previous block
- **Current Hash** — SHA-256 of all above fields

**Tamper Detection:** The admin can validate the entire chain at any time. If any block is modified, the hash comparison will fail and the tampering is detected.

---

## 💾 Database Backup

The entire database is a single file: `voting.db`
- Copy this file anywhere to take a backup
- Restore by replacing the file and restarting the app

---

## 🔒 Security Features

- Voter PRN is never stored directly — only its SHA-256 hash
- Each student can vote **only once** (enforced at DB level)
- Voting terminal session clears immediately after vote
- College admin cannot start/stop elections (only Main Admin can)
- Blockchain integrity can be verified at any time
