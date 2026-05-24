# Sports Society Management System

## Group Information

**Group Number:** 3

| Name | Roll Number |
|------|-------------|
| Adeel Ahmed | 24P-0526 |
| Yasir Sultan | 24P-0515 |

---

## Project Title & Description

**Sports Society Management System**

A Flask-based web application for managing a university sports society. It supports two roles — **Admin** (full access) and **User** (view-only). Features include managing sports, teams, players, events, announcements, and payments through a clean web interface.

---

## GitHub Repository

[https://github.com/AdeelAhmed1122/Sports_society_management_system](https://github.com/AdeelAhmed1122/Sports_society_management_system)

---

## Technologies Used

- **Python 3** — Core programming language
- **Flask** — Web framework
- **MySQL** — Relational database
- **mysql-connector-python** — MySQL driver for Python
- **Werkzeug** — Password hashing and security utilities
- **HTML / CSS / Jinja2** — Frontend templates and styling

---

## Installation & Setup

### Prerequisites

- Python 3.8 or higher
- MySQL Server (running locally)

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/AdeelAhmed1122/Sports_society_management_system.git
   cd Sports_society_management_system
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the database**

   Open `db_config.py` and update the credentials to match your MySQL setup:
   ```python
   DB_CONFIG = {
       'host': 'localhost',
       'user': 'root',
       'password': 'your_mysql_password',
       'database': 'sports_society',
       'autocommit': True,
   }
   ```

4. **Initialize the database** *(run once only)*
   ```bash
   python init_db.py
   ```

5. **Add a default user** *(optional, run once)*
   ```bash
   python run_once_add_user.py
   ```

6. **Run the application**
   ```bash
   python app.py
   ```

7. **Open in browser**
   ```
   http://localhost:5000
   ```
