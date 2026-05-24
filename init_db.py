"""
Sports Society Management System - Database Initialization
===========================================================
Run this script ONCE to create the MySQL database, tables,
and the default admin + user accounts.

Default Admin Credentials:
    Username: admin
    Password: admin123

Default User Credentials:
    Username: user
    Password: user123

Usage:
    python init_db.py
"""

import mysql.connector
from werkzeug.security import generate_password_hash
from db_config import DB_CONFIG, DB_NAME


def init_database():
    # ── 1. Connect to MySQL server (no database selected) ──
    server_config = {k: v for k, v in DB_CONFIG.items() if k != 'database'}
    server_config['autocommit'] = True
    conn = mysql.connector.connect(**server_config)
    cursor = conn.cursor()

    # ── 2. Create database ──
    cursor.execute(f"DROP DATABASE IF EXISTS `{DB_NAME}`")
    cursor.execute(f"CREATE DATABASE `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cursor.execute(f"USE `{DB_NAME}`")
    print(f"[OK] Database '{DB_NAME}' created.")

    # ── 3. Create tables ──
    cursor.execute('''
        CREATE TABLE admins (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100) NOT NULL DEFAULT 'Administrator',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB
    ''')

    # NEW: users table (view-only role)
    cursor.execute('''
        CREATE TABLE users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100) NOT NULL DEFAULT 'User',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB
    ''')

    cursor.execute('''
        CREATE TABLE sports (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            icon VARCHAR(10) NOT NULL,
            max_players INT NOT NULL,
            color VARCHAR(20) NOT NULL,
            description TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB
    ''')

    cursor.execute('''
        CREATE TABLE teams (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            sport_id INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sport_id) REFERENCES sports(id) ON DELETE CASCADE
        ) ENGINE=InnoDB
    ''')

    cursor.execute('''
        CREATE TABLE players (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            team_id INT NOT NULL,
            position VARCHAR(100) DEFAULT '',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
        ) ENGINE=InnoDB
    ''')

    cursor.execute('''
        CREATE TABLE payments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            player_name VARCHAR(100) NOT NULL,
            team_id INT NOT NULL,
            amount DECIMAL(10, 2) NOT NULL,
            payment_type VARCHAR(50) NOT NULL,
            description TEXT DEFAULT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'Completed',
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
        ) ENGINE=InnoDB
    ''')

    cursor.execute('''
        CREATE TABLE events (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            event_type ENUM('Match','Tournament','Practice','Meeting','Other') NOT NULL DEFAULT 'Match',
            sport_id INT DEFAULT NULL,
            team_home_id INT DEFAULT NULL,
            team_away_id INT DEFAULT NULL,
            event_date DATE NOT NULL,
            event_time TIME DEFAULT NULL,
            venue VARCHAR(200) DEFAULT '',
            description TEXT DEFAULT NULL,
            status ENUM('Upcoming','Live','Completed','Cancelled') NOT NULL DEFAULT 'Upcoming',
            score_home INT DEFAULT NULL,
            score_away INT DEFAULT NULL,
            bracket_round VARCHAR(50) DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sport_id) REFERENCES sports(id) ON DELETE SET NULL,
            FOREIGN KEY (team_home_id) REFERENCES teams(id) ON DELETE SET NULL,
            FOREIGN KEY (team_away_id) REFERENCES teams(id) ON DELETE SET NULL
        ) ENGINE=InnoDB
    ''')

    cursor.execute('''
        CREATE TABLE announcements (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            content TEXT NOT NULL,
            priority ENUM('Normal','Important','Urgent') NOT NULL DEFAULT 'Normal',
            category ENUM('General','Event','Result','Schedule','Other') NOT NULL DEFAULT 'General',
            is_pinned TINYINT(1) NOT NULL DEFAULT 0,
            created_by VARCHAR(100) DEFAULT 'Admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB
    ''')
    print("[OK] All tables created.")

    # ── 4. Seed default admin ──
    admin_hash = generate_password_hash('admin123')
    cursor.execute(
        "INSERT INTO admins (username, password_hash, full_name) VALUES (%s, %s, %s)",
        ('admin', admin_hash, 'System Administrator')
    )
    print("[OK] Default admin created  -> username: admin | password: admin123")

    # ── 5. Seed default user (view-only) ──
    user_hash = generate_password_hash('user123')
    cursor.execute(
        "INSERT INTO users (username, password_hash, full_name) VALUES (%s, %s, %s)",
        ('user', user_hash, 'General User')
    )
    print("[OK] Default user created   -> username: user  | password: user123")

    # ── 6. Seed default sports ──
    sports = [
        ('Cricket',    '🏏', 11, '#22c55e', 'A bat-and-ball game played between two teams of eleven players.'),
        ('Football',   '⚽', 11, '#3b82f6', 'The world\'s most popular sport, played with a spherical ball.'),
        ('Basketball', '🏀',  5, '#f97316', 'A team sport in which two teams of five players score by shooting a ball through a hoop.'),
        ('Chess',      '♟️',  2, '#f59e0b', 'A two-player strategy board game played on a checkered board.'),
        ('Ludo',       '🎲',  4, '#a855f7', 'A classic board game for two to four players.'),
        ('Tennis',     '🎾',  2, '#06b6d4', 'A racket sport that can be played individually or in doubles.'),
        ('Badminton',  '🏸',  2, '#ec4899', 'A racquet sport played using racquets to hit a shuttlecock.'),
        ('Volleyball', '🏐',  6, '#14b8a6', 'A team sport in which two teams of six players are separated by a net.'),
    ]
    cursor.executemany(
        "INSERT INTO sports (name, icon, max_players, color, description) VALUES (%s, %s, %s, %s, %s)",
        sports
    )
    print(f"[OK] {len(sports)} sports seeded.")

    # ── 7. Seed sample teams ──
    sample_teams = [
        ('Thunder Strikers', 1),
        ('Royal Warriors',   1),
        ('Blue Eagles',      2),
        ('Red Devils',       2),
        ('Court Kings',      3),
        ('Checkmate Masters', 4),
    ]
    cursor.executemany("INSERT INTO teams (name, sport_id) VALUES (%s, %s)", sample_teams)
    print(f"[OK] {len(sample_teams)} sample teams created.")

    # ── 8. Seed sample players ──
    sample_players = [
        ('Ahmed Khan',    1, 'Batsman'),
        ('Ali Raza',      1, 'Bowler'),
        ('Usman Tariq',   1, 'All-rounder'),
        ('Hassan Ali',    2, 'Wicketkeeper'),
        ('Ronaldo Jr',    3, 'Forward'),
        ('Messi Clone',   3, 'Midfielder'),
        ('David Beckham', 3, 'Midfielder'),
        ('LeBron James',  5, 'Power Forward'),
        ('Magnus C.',     6, 'Grandmaster'),
    ]
    cursor.executemany("INSERT INTO players (name, team_id, position) VALUES (%s, %s, %s)", sample_players)
    print(f"[OK] {len(sample_players)} sample players added.")

    # ── 9. Seed sample payments ──
    sample_payments = [
        ('Ahmed Khan',   1, 500.00,  'Registration', 'Annual registration fee',  'Completed'),
        ('Ali Raza',     1, 500.00,  'Registration', 'Annual registration fee',  'Completed'),
        ('Ronaldo Jr',   3, 750.00,  'Registration', 'Football club membership', 'Completed'),
        ('Messi Clone',  3, 750.00,  'Registration', 'Football club membership', 'Pending'),
        ('LeBron James', 5, 1000.00, 'Tournament',   'Inter-university tourney', 'Completed'),
        ('Magnus C.',    6, 250.00,  'Monthly',       'Monthly coaching fee',     'Completed'),
    ]
    cursor.executemany(
        "INSERT INTO payments (player_name, team_id, amount, payment_type, description, status) VALUES (%s, %s, %s, %s, %s, %s)",
        sample_payments
    )
    print(f"[OK] {len(sample_payments)} sample payments recorded.")

    # ── 10. Seed sample events ──
    sample_events = [
        ('Cricket League Final',       'Tournament', 1, 1, 2, '2026-06-15', '14:00:00', 'University Ground',  'The grand final of the inter-department cricket league.',     'Upcoming',  None, None, 'Final'),
        ('Football Friendly Match',    'Match',      2, 3, 4, '2026-05-25', '16:00:00', 'Main Stadium',       'Friendly match between Blue Eagles and Red Devils.',          'Upcoming',  None, None, None),
        ('Basketball Practice Session','Practice',   3, 5, None,'2026-05-22','10:00:00','Indoor Court',        'Regular practice session for Court Kings.',                   'Upcoming',  None, None, None),
        ('Chess Championship Round 1', 'Tournament', 4, 6, None,'2026-05-20','09:00:00','Chess Hall',          'Opening round of the annual chess championship.',             'Upcoming',  None, None, 'Round 1'),
        ('Cricket Semi-Final',         'Tournament', 1, 1, 2, '2026-05-10', '14:00:00', 'University Ground',  'Semi-final match of the cricket tournament.',                 'Completed', 185, 160, 'Semi-Final'),
        ('Football Season Opener',     'Match',      2, 3, 4, '2026-05-05', '17:00:00', 'Main Stadium',       'The first match of the football season.',                     'Completed', 3,   1,   None),
        ('Annual Sports Meeting',      'Meeting',    None,None,None,'2026-05-28','11:00:00','Conference Room', 'Annual meeting to discuss sports society plans and budget.',   'Upcoming',  None, None, None),
    ]
    cursor.executemany(
        '''INSERT INTO events (title, event_type, sport_id, team_home_id, team_away_id,
           event_date, event_time, venue, description, status, score_home, score_away, bracket_round)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
        sample_events
    )
    print(f"[OK] {len(sample_events)} sample events created.")

    # ── 11. Seed sample announcements ──
    sample_announcements = [
        ('Cricket League Registration Open',  'Registration for the Annual Cricket League is now open! All teams must register by May 30th. Contact the sports office for details.', 'Important', 'Event',    1, 'System Administrator'),
        ('New Basketball Court Available',     'The new indoor basketball court is now ready for use. Booking slots are available from Monday to Saturday, 8 AM to 8 PM.',           'Normal',    'General',  0, 'System Administrator'),
        ('Football Match Rescheduled',         'The football match between Blue Eagles and Red Devils has been rescheduled to May 25th due to weather conditions.',                  'Urgent',    'Schedule', 1, 'System Administrator'),
        ('Congratulations Chess Champions!',   'Checkmate Masters won the inter-university chess tournament! Great performance by all players.',                                      'Normal',    'Result',   0, 'System Administrator'),
        ('Sports Society Budget Approved',     'The annual budget for the sports society has been approved. New equipment will be purchased for all departments.',                    'Important', 'General',  0, 'System Administrator'),
        ('Mandatory Safety Briefing',          'All team captains must attend the safety briefing on May 28th at 11 AM in the Conference Room. Attendance is mandatory.',             'Urgent',    'General',  1, 'System Administrator'),
    ]
    cursor.executemany(
        '''INSERT INTO announcements (title, content, priority, category, is_pinned, created_by)
           VALUES (%s,%s,%s,%s,%s,%s)''',
        sample_announcements
    )
    print(f"[OK] {len(sample_announcements)} sample announcements created.")

    cursor.close()
    conn.close()
    print("\n==============================================")
    print("  Database initialization complete!")
    print("  Login  -> http://127.0.0.1:5000")
    print("  Admin  -> admin / admin123  (full access)")
    print("  User   -> user  / user123   (view-only)")
    print("==============================================")


if __name__ == '__main__':
    init_database()
