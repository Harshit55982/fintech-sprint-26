# RainShield — Simplified FS-2604 Prototype

Beginner-friendly Flask + HTML + CSS + JavaScript demo.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

Farmer accounts and their policy state are stored in the local `rainshield.db` SQLite database. The SQL schema is in `schema.sql`, and the database is created automatically on first run.

## Demo order
1. Home → Policy
2. Tick comprehension → Activate for ₹300
3. Rainfall → Normal drought → Evaluate
4. Try Compromised source (2, 3, 85): median remains 3 mm, so payout triggers
5. Wallet → show ₹8,000
6. Why? → explain the reconstruction
7. Reset demo to repeat

This is intentionally simplified for beginner presentation. It is a prototype, not a production insurance system.
