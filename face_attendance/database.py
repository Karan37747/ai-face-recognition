"""
database.py - MySQL Database Setup & Helper Functions
Run this file once to initialize the database: python database.py
"""

import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '0780',       # <-- Change to your MySQL password
    'database': 'face_attendance_db'
}

def get_connection():
    """Return a live MySQL connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"[DB ERROR] {e}")
        return None


def init_db():
    """Create the database and all tables."""
    try:
        # Connect without selecting a database first
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = conn.cursor()

        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        cursor.execute(f"USE {DB_CONFIG['database']}")

        # ── users ────────────────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                username    VARCHAR(80)  NOT NULL UNIQUE,
                password    VARCHAR(255) NOT NULL,
                role        ENUM('admin','teacher','student') NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── students ─────────────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id            INT AUTO_INCREMENT PRIMARY KEY,
                user_id       INT,
                roll_number   VARCHAR(20)  NOT NULL UNIQUE,
                full_name     VARCHAR(100) NOT NULL,
                email         VARCHAR(120),
                phone         VARCHAR(20),
                department    VARCHAR(80),
                semester      INT DEFAULT 1,
                face_encoded  TINYINT(1) DEFAULT 0,
                profile_image VARCHAR(255),
                created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """)

        # ── teachers ─────────────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teachers (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                user_id     INT,
                employee_id VARCHAR(20)  NOT NULL UNIQUE,
                full_name   VARCHAR(100) NOT NULL,
                email       VARCHAR(120),
                phone       VARCHAR(20),
                department  VARCHAR(80),
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """)

        # ── subjects ─────────────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id           INT AUTO_INCREMENT PRIMARY KEY,
                subject_code VARCHAR(20)  NOT NULL UNIQUE,
                subject_name VARCHAR(100) NOT NULL,
                department   VARCHAR(80),
                semester     INT,
                teacher_id   INT,
                created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE SET NULL
            )
        """)

        # ── attendance ───────────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                student_id  INT NOT NULL,
                subject_id  INT,
                teacher_id  INT,
                date        DATE NOT NULL,
                time_in     TIME,
                status      ENUM('present','absent','late') DEFAULT 'present',
                marked_by   ENUM('face_recognition','manual') DEFAULT 'face_recognition',
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id)  REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id)  REFERENCES subjects(id) ON DELETE SET NULL,
                FOREIGN KEY (teacher_id)  REFERENCES teachers(id) ON DELETE SET NULL,
                UNIQUE KEY unique_attendance (student_id, subject_id, date)
            )
        """)

        conn.commit()
        print("[✓] Database and tables created successfully.")

        # ── seed default admin ────────────────────────────────────────────────
        from werkzeug.security import generate_password_hash
        cursor.execute("SELECT id FROM users WHERE username='admin'")
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                ('admin', generate_password_hash('admin123'), 'admin')
            )
            conn.commit()
            print("[✓] Default admin created  →  username: admin | password: admin123")

        cursor.close()
        conn.close()

    except Error as e:
        print(f"[DB INIT ERROR] {e}")


if __name__ == '__main__':
    init_db()
