from flask import Flask, render_template, jsonify, request, session
from statistics import median
from datetime import datetime
import json
import re
import sqlite3
from pathlib import Path
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = 'rainshield-demo-secret'
DATABASE = Path(app.root_path) / 'rainshield.db'

PASSWORD_RULE = re.compile(r'^(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$')
POLICY = {
    'name': 'RainShield', 'crop': 'Groundnut', 'premium': 300,
    'coverage': 20000, 'threshold': 20, 'payout_percent': 40,
    'season': 'Kharif 2026'
}

state = {
    'farmer': {'name': 'Ravi Kumar', 'id': 'F001'},
    'balance': 0,
    'policy_active': False,
    'oracles': [18, 19, 17],
    'payout': None,
    'last_decision': None,
    'history': []
}

def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection

def init_db():
    with get_db() as connection:
        connection.executescript((Path(app.root_path) / 'schema.sql').read_text())

def default_state():
    return {
        'farmer': {'name': 'Ravi Kumar', 'id': 'F001'},
        'balance': 0, 'policy_active': False,
        'oracles': [18, 19, 17], 'payout': None,
        'last_decision': None, 'history': []
    }

def state_for_session():
    user = session.get('user')
    if not user:
        return state
    with get_db() as connection:
        farmer = connection.execute('SELECT * FROM farmers WHERE email = ?', (user['email'],)).fetchone()
        saved = connection.execute('SELECT * FROM farmer_state WHERE farmer_id = ?', (farmer['id'],)).fetchone()
    if not saved:
        return default_state() | {'farmer': {'name': farmer['name'], 'id': f"F{farmer['id']:03d}"}}
    return {
        'farmer': {'name': farmer['name'], 'id': f"F{farmer['id']:03d}"},
        'balance': saved['balance'], 'policy_active': bool(saved['policy_active']),
        'oracles': json.loads(saved['oracles']), 'payout': saved['payout'],
        'last_decision': json.loads(saved['last_decision']) if saved['last_decision'] else None,
        'history': json.loads(saved['history'])
    }

def save_state(current):
    user = session.get('user')
    if not user:
        return
    with get_db() as connection:
        farmer = connection.execute('SELECT id FROM farmers WHERE email = ?', (user['email'],)).fetchone()
        connection.execute('''
            INSERT INTO farmer_state (farmer_id, balance, policy_active, oracles, payout, last_decision, history)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(farmer_id) DO UPDATE SET
                balance=excluded.balance, policy_active=excluded.policy_active,
                oracles=excluded.oracles, payout=excluded.payout,
                last_decision=excluded.last_decision, history=excluded.history
        ''', (farmer['id'], current['balance'], int(current['policy_active']),
              json.dumps(current['oracles']), current['payout'],
              json.dumps(current['last_decision']) if current['last_decision'] else None,
              json.dumps(current['history'])))

init_db()

def evaluate(current):
    values = current['oracles']
    result = median(values)
    triggered = result < POLICY['threshold']
    payout = int(POLICY['coverage'] * POLICY['payout_percent'] / 100) if triggered else 0
    current['last_decision'] = {
        'readings': values[:], 'median': result, 'triggered': triggered,
        'payout': payout, 'time': datetime.now().strftime('%H:%M:%S')
    }
    if triggered and current['policy_active'] and current['payout'] != payout:
        current['balance'] = payout
        current['payout'] = payout
        current['history'].append({'type':'Payout', 'amount':payout, 'reason':f'Median rainfall {result} mm < {POLICY["threshold"]} mm'})
    save_state(current)
    return current['last_decision']

@app.route('/')
def index():
    return render_template('index.html')

@app.get('/api/auth/session')
def auth_session():
    return jsonify(user=session.get('user'))

@app.post('/api/auth/signup')
def signup():
    data = request.get_json(force=True)
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    if not name or not email or not password:
        return jsonify(ok=False, error='Name, email, and password are required.'), 400
    if not PASSWORD_RULE.match(password):
        return jsonify(ok=False, error='Password must be 8+ characters with 1 capital letter, 1 number, and 1 special character.'), 400
    with get_db() as connection:
        existing = connection.execute('SELECT id FROM farmers WHERE email = ?', (email,)).fetchone()
    if existing:
        return jsonify(ok=False, error='An account with this email already exists.'), 409
    with get_db() as connection:
        connection.execute('INSERT INTO farmers (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)',
                           (name, email, generate_password_hash(password), datetime.now().isoformat()))
    session['user'] = {'name': name, 'email': email}
    return jsonify(ok=True, user=session['user'])

@app.post('/api/auth/login')
def login():
    data = request.get_json(force=True)
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    with get_db() as connection:
        user = connection.execute('SELECT * FROM farmers WHERE email = ?', (email,)).fetchone()
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify(ok=False, error='Email or password is incorrect.'), 401
    session['user'] = {'name': user['name'], 'email': email}
    return jsonify(ok=True, user=session['user'])

@app.post('/api/auth/logout')
def logout():
    session.pop('user', None)
    return jsonify(ok=True)

@app.route('/api/state')
def api_state():
    return jsonify({**state_for_session(), 'policy': POLICY})

@app.post('/api/bind')
def bind():
    current = state_for_session()
    current['policy_active'] = True
    current['history'].append({'type':'Premium paid', 'amount':-POLICY['premium'], 'reason':'Policy activated'})
    save_state(current)
    return jsonify(ok=True)

@app.post('/api/evaluate')
def api_evaluate():
    return jsonify(evaluate(state_for_session()))

@app.post('/api/oracles')
def api_oracles():
    data = request.get_json(force=True)
    current = state_for_session()
    current['oracles'] = [float(x) for x in data['values']]
    return jsonify(evaluate(current))

@app.post('/api/reset')
def reset():
    current = state_for_session()
    current.update({'balance':0,'policy_active':False,'oracles':[18,19,17],'payout':None,'last_decision':None,'history':[]})
    save_state(current)
    return jsonify(ok=True)

@app.get('/healthz')
def health(): return jsonify(status='ok')

@app.get('/metrics')
def metrics(): return 'policies_active 1\npayouts_total 1\n'

if __name__ == '__main__':
    app.run(debug=True)
