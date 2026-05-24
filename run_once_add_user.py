"""
run_once_add_user.py
====================
Run this script ONCE to add the 'users' table and default user
to your existing sports_society database WITHOUT losing any data.

Usage:
    python run_once_add_user.py

Default User Login:
    Username: user
    Password: user123
"""

import mysql.connector
from werkzeug.security import generate_password_hash
from db_config import DB_CONFIG

def add_users_table():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Create users table if it doesn't already exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100) NOT NULL DEFAULT 'User',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB
    ''')
    print("[OK] 'users' table created (or already existed).")

    # Insert default user safely (won't duplicate if already exists)
    user_hash = generate_password_hash('user123')
    cursor.execute(
        "INSERT IGNORE INTO users (username, password_hash, full_name) VALUES (%s, %s, %s)",
        ('user', user_hash, 'General User')
    )
    conn.commit()

    if cursor.rowcount > 0:
        print("[OK] Default user created  -> username: user | password: user123")
    else:
        print("[INFO] User 'user' already exists, skipped.")

    cursor.close()
    conn.close()

    print("\n==========================================")
    print("  Done! Your database is ready.")
    print("  Admin -> admin / admin123 (full access)")
    print("  User  -> user  / user123  (view-only)")
    print("==========================================")

if __name__ == '__main__':
    add_users_table()
