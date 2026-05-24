"""
Sports Society Management System
=================================
A professional Flask web application for managing sports societies,
teams, players, and payments. Features admin and user (view-only) access.

Run:
    python init_db.py   (first time only)
    python app.py
"""

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, jsonify
)
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
import mysql.connector
from db_config import DB_CONFIG

# ── App setup ──────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = 'sports_society_ultra_secret_key_2026_!@#'


# ── Auto-create users table if it doesn't exist ────────────────
def ensure_users_table():
    """Automatically creates the users table and default user if missing."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(100) NOT NULL DEFAULT 'User',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB
        ''')
        # Insert default user if not already there
        default_hash = generate_password_hash('user123')
        cursor.execute(
            "INSERT IGNORE INTO users (username, password_hash, full_name) VALUES (%s, %s, %s)",
            ('user', default_hash, 'General User')
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[Warning] Could not ensure users table: {e}")

ensure_users_table()


# ── Custom Jinja2 filter for MySQL TIME (timedelta) columns ──
import datetime

@app.template_filter('format_time')
def format_time_filter(td):
    """Convert a datetime.timedelta (MySQL TIME) to a formatted 12-hour string."""
    if td is None:
        return ''
    if isinstance(td, datetime.timedelta):
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        period = 'AM' if hours < 12 else 'PM'
        display_hours = hours % 12 or 12
        return f'{display_hours:02d}:{minutes:02d} {period}'
    return td.strftime('%I:%M %p')


# ── Database helper ────────────────────────────────────────────
def get_db():
    conn = mysql.connector.connect(**DB_CONFIG)
    return conn


def query_db(sql, args=(), one=False, commit=False):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, args)
    if commit:
        conn.commit()
        last_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return last_id
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return (rows[0] if rows else None) if one else rows


# ── Session helpers ────────────────────────────────────────────
def is_logged_in():
    return 'admin_id' in session or 'user_id' in session

def is_admin():
    return 'admin_id' in session

def is_user():
    return 'user_id' in session and 'admin_id' not in session


# ── Auth decorators ────────────────────────────────────────────
def login_required(f):
    """Allow both admins and regular users (view-only)."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not is_logged_in():
            flash('Please login to access the system.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    """Restrict to admins only — blocks regular users."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not is_logged_in():
            flash('Please login to access the system.', 'error')
            return redirect(url_for('login'))
        if not is_admin():
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrapper


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   AUTH ROUTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        role     = request.form.get('role', 'user')  # 'admin' or 'user'

        if role == 'admin':
            admin = query_db(
                'SELECT * FROM admins WHERE username = %s', (username,), one=True
            )
            if admin and check_password_hash(admin['password_hash'], password):
                session['admin_id']   = admin['id']
                session['admin_name'] = admin['full_name']
                session['admin_user'] = admin['username']
                flash(f'Welcome back, {admin["full_name"]}! (Admin)', 'success')
                return redirect(url_for('index'))
            flash('Invalid admin username or password.', 'error')

        else:  # user role
            user = query_db(
                'SELECT * FROM users WHERE username = %s', (username,), one=True
            )
            if user and check_password_hash(user['password_hash'], password):
                session['user_id']   = user['id']
                session['user_name'] = user['full_name']
                session['user_user'] = user['username']
                flash(f'Welcome, {user["full_name"]}! (View-Only Access)', 'success')
                return redirect(url_for('index'))
            flash('Invalid user username or password.', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if is_logged_in():
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        full_name = request.form.get('full_name', '').strip() or 'User'
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not username or not password or not confirm_password:
            flash('Please fill in all the registration fields.', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')

        existing_user = query_db(
            'SELECT id FROM users WHERE username = %s',
            (username,), one=True
        )
        if existing_user:
            flash('That username is already taken. Please choose another.', 'error')
            return render_template('register.html')

        password_hash = generate_password_hash(password)
        query_db(
            'INSERT INTO users (username, password_hash, full_name) VALUES (%s, %s, %s)',
            (username, password_hash, full_name),
            commit=True
        )

        flash('Registration successful! You can now log in with your new account.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   DASHBOARD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/')
@login_required
def index():
    sports = query_db('SELECT * FROM sports ORDER BY name')
    stats = {}
    for sport in sports:
        tc = query_db(
            'SELECT COUNT(*) AS c FROM teams WHERE sport_id=%s',
            (sport['id'],), one=True
        )['c']
        pc = query_db('''
            SELECT COUNT(*) AS c FROM players p
            JOIN teams t ON p.team_id = t.id
            WHERE t.sport_id = %s
        ''', (sport['id'],), one=True)['c']
        stats[sport['id']] = {'teams': tc, 'players': pc}

    total_teams    = query_db('SELECT COUNT(*) AS c FROM teams', one=True)['c']
    total_players  = query_db('SELECT COUNT(*) AS c FROM players', one=True)['c']
    total_payments = query_db(
        "SELECT COALESCE(SUM(amount),0) AS total FROM payments WHERE status='Completed'",
        one=True
    )['total']
    pending_payments = query_db(
        "SELECT COUNT(*) AS c FROM payments WHERE status='Pending'",
        one=True
    )['c']

    recent_players = query_db('''
        SELECT p.name AS player_name, t.name AS team_name,
               s.name AS sport_name, s.icon, p.joined_at
        FROM players p
        JOIN teams t ON p.team_id = t.id
        JOIN sports s ON t.sport_id = s.id
        ORDER BY p.joined_at DESC LIMIT 5
    ''')

    recent_payments = query_db('''
        SELECT py.player_name, py.amount, py.payment_type,
               py.status, py.payment_date, t.name AS team_name
        FROM payments py
        JOIN teams t ON py.team_id = t.id
        ORDER BY py.payment_date DESC LIMIT 5
    ''')

    upcoming_events = query_db('''
        SELECT e.*, s.name AS sport_name, s.icon AS sport_icon,
               th.name AS home_team_name, ta.name AS away_team_name
        FROM events e
        LEFT JOIN sports s ON e.sport_id = s.id
        LEFT JOIN teams th ON e.team_home_id = th.id
        LEFT JOIN teams ta ON e.team_away_id = ta.id
        WHERE e.status IN ('Upcoming','Live')
        ORDER BY e.event_date ASC LIMIT 4
    ''')

    latest_announcements = query_db('''
        SELECT * FROM announcements
        ORDER BY is_pinned DESC, created_at DESC LIMIT 3
    ''')

    return render_template('index.html',
        sports=sports, stats=stats,
        total_teams=total_teams,
        total_players=total_players,
        total_payments=total_payments,
        pending_payments=pending_payments,
        recent_players=recent_players,
        recent_payments=recent_payments,
        upcoming_events=upcoming_events,
        latest_announcements=latest_announcements,
        is_admin=is_admin()
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   SPORTS MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/sports')
@login_required
def sports():
    all_sports = query_db('SELECT * FROM sports ORDER BY name')
    sport_stats = {}
    for s in all_sports:
        tc = query_db('SELECT COUNT(*) AS c FROM teams WHERE sport_id=%s', (s['id'],), one=True)['c']
        pc = query_db('''
            SELECT COUNT(*) AS c FROM players p
            JOIN teams t ON p.team_id = t.id WHERE t.sport_id = %s
        ''', (s['id'],), one=True)['c']
        sport_stats[s['id']] = {'teams': tc, 'players': pc}
    return render_template('sports.html', sports=all_sports, sport_stats=sport_stats, is_admin=is_admin())


@app.route('/sports/add', methods=['GET', 'POST'])
@admin_required
def add_sport():
    if request.method == 'POST':
        name        = request.form.get('name', '').strip()
        icon        = request.form.get('icon', '').strip()
        max_players = request.form.get('max_players', type=int)
        color       = request.form.get('color', '#3b82f6').strip()
        description = request.form.get('description', '').strip()

        if not name or not icon or not max_players:
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('add_sport'))

        existing = query_db('SELECT id FROM sports WHERE name=%s', (name,), one=True)
        if existing:
            flash(f'Sport "{name}" already exists.', 'error')
            return redirect(url_for('add_sport'))

        query_db(
            'INSERT INTO sports (name, icon, max_players, color, description) VALUES (%s,%s,%s,%s,%s)',
            (name, icon, max_players, color, description), commit=True
        )
        flash(f'Sport "{name}" added successfully!', 'success')
        return redirect(url_for('sports'))

    return render_template('add_sport.html')


@app.route('/sports/<int:id>/delete', methods=['POST'])
@admin_required
def delete_sport(id):
    sport = query_db('SELECT * FROM sports WHERE id=%s', (id,), one=True)
    if not sport:
        flash('Sport not found.', 'error')
        return redirect(url_for('sports'))
    query_db('DELETE FROM sports WHERE id=%s', (id,), commit=True)
    flash(f'Sport "{sport["name"]}" deleted.', 'success')
    return redirect(url_for('sports'))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   TEAMS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/teams')
@login_required
def teams():
    all_sports = query_db('SELECT * FROM sports ORDER BY name')
    teams_by_sport = {}
    for sport in all_sports:
        t_list = query_db(
            'SELECT * FROM teams WHERE sport_id=%s ORDER BY created_at DESC',
            (sport['id'],)
        )
        enriched = []
        for t in t_list:
            count = query_db(
                'SELECT COUNT(*) AS c FROM players WHERE team_id=%s',
                (t['id'],), one=True
            )['c']
            t['player_count'] = count
            t['max_players']  = sport['max_players']
            enriched.append(t)
        teams_by_sport[sport['id']] = enriched
    return render_template('teams.html', sports=all_sports, teams_by_sport=teams_by_sport, is_admin=is_admin())


@app.route('/teams/create', methods=['GET', 'POST'])
@admin_required
def create_team():
    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        sport_id = request.form.get('sport_id')
        if not name or not sport_id:
            flash('Please fill in all fields.', 'error')
            return redirect(url_for('create_team'))
        query_db(
            'INSERT INTO teams (name, sport_id) VALUES (%s, %s)',
            (name, sport_id), commit=True
        )
        flash(f'Team "{name}" created successfully!', 'success')
        return redirect(url_for('teams'))
    all_sports = query_db('SELECT * FROM sports ORDER BY name')
    return render_template('create_team.html', sports=all_sports)


@app.route('/teams/<int:id>')
@login_required
def team_detail(id):
    team = query_db('''
        SELECT t.*, s.name AS sport_name, s.icon, s.max_players, s.color
        FROM teams t JOIN sports s ON t.sport_id = s.id
        WHERE t.id = %s
    ''', (id,), one=True)
    if not team:
        flash('Team not found.', 'error')
        return redirect(url_for('teams'))
    players      = query_db('SELECT * FROM players WHERE team_id=%s ORDER BY joined_at DESC', (id,))
    player_count = len(players)
    team_payments = query_db('SELECT * FROM payments WHERE team_id=%s ORDER BY payment_date DESC', (id,))
    return render_template('team_detail.html',
        team=team, players=players,
        player_count=player_count, team_payments=team_payments,
        is_admin=is_admin()
    )


@app.route('/teams/<int:id>/add_player', methods=['POST'])
@admin_required
def add_player(id):
    team = query_db('''
        SELECT t.*, s.max_players, s.name AS sport_name
        FROM teams t JOIN sports s ON t.sport_id = s.id
        WHERE t.id = %s
    ''', (id,), one=True)
    if not team:
        flash('Team not found.', 'error')
        return redirect(url_for('teams'))

    count = query_db('SELECT COUNT(*) AS c FROM players WHERE team_id=%s', (id,), one=True)['c']
    if count >= team['max_players']:
        flash(f'Team is full! {team["sport_name"]} allows max {team["max_players"]} players.', 'error')
        return redirect(url_for('team_detail', id=id))

    name     = request.form.get('name', '').strip()
    position = request.form.get('position', '').strip()
    if not name:
        flash('Player name is required.', 'error')
        return redirect(url_for('team_detail', id=id))

    query_db(
        'INSERT INTO players (name, team_id, position) VALUES (%s,%s,%s)',
        (name, id, position), commit=True
    )
    flash(f'Player "{name}" added successfully!', 'success')
    return redirect(url_for('team_detail', id=id))


@app.route('/players/<int:id>/delete', methods=['POST'])
@admin_required
def delete_player(id):
    player = query_db('SELECT * FROM players WHERE id=%s', (id,), one=True)
    if not player:
        flash('Player not found.', 'error')
        return redirect(url_for('teams'))
    team_id = player['team_id']
    query_db('DELETE FROM players WHERE id=%s', (id,), commit=True)
    flash('Player removed successfully.', 'success')
    return redirect(url_for('team_detail', id=team_id))


@app.route('/teams/<int:id>/delete', methods=['POST'])
@admin_required
def delete_team(id):
    query_db('DELETE FROM teams WHERE id=%s', (id,), commit=True)
    flash('Team deleted successfully.', 'success')
    return redirect(url_for('teams'))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   PAYMENTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/payments')
@login_required
def payments():
    all_payments = query_db('''
        SELECT py.*, t.name AS team_name, s.name AS sport_name, s.icon
        FROM payments py
        JOIN teams t ON py.team_id = t.id
        JOIN sports s ON t.sport_id = s.id
        ORDER BY py.payment_date DESC
    ''')
    total_revenue  = query_db("SELECT COALESCE(SUM(amount),0) AS total FROM payments WHERE status='Completed'", one=True)['total']
    pending_amount = query_db("SELECT COALESCE(SUM(amount),0) AS total FROM payments WHERE status='Pending'", one=True)['total']
    total_count    = query_db('SELECT COUNT(*) AS c FROM payments', one=True)['c']
    return render_template('payments.html',
        payments=all_payments,
        total_revenue=total_revenue,
        pending_amount=pending_amount,
        total_count=total_count,
        is_admin=is_admin()
    )


@app.route('/payments/add', methods=['GET', 'POST'])
@admin_required
def add_payment():
    if request.method == 'POST':
        player_name  = request.form.get('player_name', '').strip()
        team_id      = request.form.get('team_id', type=int)
        amount       = request.form.get('amount', type=float)
        payment_type = request.form.get('payment_type', '').strip()
        description  = request.form.get('description', '').strip()
        status       = request.form.get('status', 'Completed').strip()

        if not player_name or not team_id or not amount or not payment_type:
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('add_payment'))

        query_db(
            '''INSERT INTO payments
               (player_name, team_id, amount, payment_type, description, status)
               VALUES (%s,%s,%s,%s,%s,%s)''',
            (player_name, team_id, amount, payment_type, description, status),
            commit=True
        )
        flash(f'Payment of Rs.{amount:.2f} recorded successfully!', 'success')
        return redirect(url_for('payments'))

    all_teams = query_db('''
        SELECT t.*, s.name AS sport_name, s.icon
        FROM teams t JOIN sports s ON t.sport_id = s.id
        ORDER BY s.name, t.name
    ''')
    return render_template('add_payment.html', teams=all_teams)


@app.route('/payments/<int:id>/delete', methods=['POST'])
@admin_required
def delete_payment(id):
    query_db('DELETE FROM payments WHERE id=%s', (id,), commit=True)
    flash('Payment record deleted.', 'success')
    return redirect(url_for('payments'))


@app.route('/payments/<int:id>/toggle_status', methods=['POST'])
@admin_required
def toggle_payment_status(id):
    payment = query_db('SELECT * FROM payments WHERE id=%s', (id,), one=True)
    if payment:
        new_status = 'Completed' if payment['status'] == 'Pending' else 'Pending'
        query_db('UPDATE payments SET status=%s WHERE id=%s', (new_status, id), commit=True)
        flash(f'Payment status updated to {new_status}.', 'success')
    return redirect(url_for('payments'))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   EVENTS & TOURNAMENTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/events')
@login_required
def events():
    all_events = query_db('''
        SELECT e.*, s.name AS sport_name, s.icon AS sport_icon, s.color AS sport_color,
               th.name AS home_team_name, ta.name AS away_team_name
        FROM events e
        LEFT JOIN sports s ON e.sport_id = s.id
        LEFT JOIN teams th ON e.team_home_id = th.id
        LEFT JOIN teams ta ON e.team_away_id = ta.id
        ORDER BY e.event_date DESC, e.event_time DESC
    ''')
    upcoming   = [e for e in all_events if e['status'] == 'Upcoming']
    completed  = [e for e in all_events if e['status'] == 'Completed']
    live       = [e for e in all_events if e['status'] == 'Live']
    cancelled  = [e for e in all_events if e['status'] == 'Cancelled']
    tournaments = [e for e in all_events if e['event_type'] == 'Tournament']
    return render_template('events.html',
        all_events=all_events, upcoming=upcoming, completed=completed,
        live=live, cancelled=cancelled, tournaments=tournaments,
        is_admin=is_admin()
    )


@app.route('/events/add', methods=['GET', 'POST'])
@admin_required
def add_event():
    if request.method == 'POST':
        title         = request.form.get('title', '').strip()
        event_type    = request.form.get('event_type', 'Match')
        sport_id      = request.form.get('sport_id', type=int) or None
        team_home_id  = request.form.get('team_home_id', type=int) or None
        team_away_id  = request.form.get('team_away_id', type=int) or None
        event_date    = request.form.get('event_date', '').strip()
        event_time    = request.form.get('event_time', '').strip() or None
        venue         = request.form.get('venue', '').strip()
        description   = request.form.get('description', '').strip()
        bracket_round = request.form.get('bracket_round', '').strip() or None

        if not title or not event_date:
            flash('Title and date are required.', 'error')
            return redirect(url_for('add_event'))

        query_db(
            '''INSERT INTO events (title, event_type, sport_id, team_home_id, team_away_id,
               event_date, event_time, venue, description, bracket_round)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
            (title, event_type, sport_id, team_home_id, team_away_id,
             event_date, event_time, venue, description, bracket_round),
            commit=True
        )
        flash(f'Event "{title}" scheduled!', 'success')
        return redirect(url_for('events'))

    all_sports = query_db('SELECT * FROM sports ORDER BY name')
    all_teams  = query_db('''
        SELECT t.*, s.name AS sport_name, s.icon
        FROM teams t JOIN sports s ON t.sport_id = s.id ORDER BY s.name, t.name
    ''')
    return render_template('add_event.html', sports=all_sports, teams=all_teams)


@app.route('/events/<int:id>')
@login_required
def event_detail(id):
    event = query_db('''
        SELECT e.*, s.name AS sport_name, s.icon AS sport_icon, s.color AS sport_color,
               th.name AS home_team_name, ta.name AS away_team_name
        FROM events e
        LEFT JOIN sports s ON e.sport_id = s.id
        LEFT JOIN teams th ON e.team_home_id = th.id
        LEFT JOIN teams ta ON e.team_away_id = ta.id
        WHERE e.id = %s
    ''', (id,), one=True)
    if not event:
        flash('Event not found.', 'error')
        return redirect(url_for('events'))
    related = []
    if event['event_type'] == 'Tournament' and event['sport_id']:
        related = query_db('''
            SELECT e.*, th.name AS home_team_name, ta.name AS away_team_name
            FROM events e
            LEFT JOIN teams th ON e.team_home_id = th.id
            LEFT JOIN teams ta ON e.team_away_id = ta.id
            WHERE e.sport_id = %s AND e.event_type = 'Tournament' AND e.id != %s
            ORDER BY e.event_date
        ''', (event['sport_id'], id))
    return render_template('event_detail.html', event=event, related=related, is_admin=is_admin())


@app.route('/events/<int:id>/update_score', methods=['POST'])
@admin_required
def update_score(id):
    score_home = request.form.get('score_home', type=int)
    score_away = request.form.get('score_away', type=int)
    status     = request.form.get('status', 'Completed')
    query_db('UPDATE events SET score_home=%s, score_away=%s, status=%s WHERE id=%s',
             (score_home, score_away, status, id), commit=True)
    flash('Score updated successfully!', 'success')
    return redirect(url_for('event_detail', id=id))


@app.route('/events/<int:id>/delete', methods=['POST'])
@admin_required
def delete_event(id):
    query_db('DELETE FROM events WHERE id=%s', (id,), commit=True)
    flash('Event deleted.', 'success')
    return redirect(url_for('events'))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   ANNOUNCEMENTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/announcements')
@login_required
def announcements():
    all_announcements = query_db('''
        SELECT * FROM announcements
        ORDER BY is_pinned DESC, created_at DESC
    ''')
    return render_template('announcements.html', announcements=all_announcements, is_admin=is_admin())


@app.route('/announcements/add', methods=['GET', 'POST'])
@admin_required
def add_announcement():
    if request.method == 'POST':
        title     = request.form.get('title', '').strip()
        content   = request.form.get('content', '').strip()
        priority  = request.form.get('priority', 'Normal')
        category  = request.form.get('category', 'General')
        is_pinned = 1 if request.form.get('is_pinned') else 0

        if not title or not content:
            flash('Title and content are required.', 'error')
            return redirect(url_for('add_announcement'))

        query_db(
            '''INSERT INTO announcements (title, content, priority, category, is_pinned, created_by)
               VALUES (%s,%s,%s,%s,%s,%s)''',
            (title, content, priority, category, is_pinned, session.get('admin_name', 'Admin')),
            commit=True
        )
        flash(f'Announcement "{title}" published!', 'success')
        return redirect(url_for('announcements'))

    return render_template('add_announcement.html')


@app.route('/announcements/<int:id>/pin', methods=['POST'])
@admin_required
def toggle_pin(id):
    ann = query_db('SELECT * FROM announcements WHERE id=%s', (id,), one=True)
    if ann:
        new_pin = 0 if ann['is_pinned'] else 1
        query_db('UPDATE announcements SET is_pinned=%s WHERE id=%s', (new_pin, id), commit=True)
        flash('Announcement ' + ('pinned' if new_pin else 'unpinned') + '.', 'success')
    return redirect(url_for('announcements'))


@app.route('/announcements/<int:id>/delete', methods=['POST'])
@admin_required
def delete_announcement(id):
    query_db('DELETE FROM announcements WHERE id=%s', (id,), commit=True)
    flash('Announcement deleted.', 'success')
    return redirect(url_for('announcements'))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   RUN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == '__main__':
    app.run(debug=True)
