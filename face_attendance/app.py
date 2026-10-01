"""
app.py  –  Face Recognition Attendance System
Run:  python app.py
"""
# venv\Scripts\python.exe face_attendance\app.py

import os
import csv
import io
import json
from datetime import date, datetime, timedelta

from flask import (Flask, render_template, request, redirect, url_for,
                   flash, session, jsonify, Response, send_file)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from database import get_connection, init_db
from face_recognition_helper import (
    capture_face_images, train_model, generate_recognition_stream
)

app = Flask(__name__)
app.secret_key = 'face_attendance_secret_key_2024'

UPLOAD_FOLDER  = os.path.join('static', 'images', 'profiles')
ALLOWED_EXT    = {'png', 'jpg', 'jpeg'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def login_required(role=None):
    """Decorator-like check used at the top of each view."""
    def check():
        if 'user_id' not in session:
            return False
        if role and session.get('role') != role:
            return False
        return True
    return check

# ─── Auth ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        role     = request.form['role']

        conn = get_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username=%s AND role=%s", (username, role))
        user = cur.fetchone()
        cur.close(); conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id']  = user['id']
            session['username'] = user['username']
            session['role']     = user['role']
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for(f'{role}_dashboard'))

        flash('Invalid credentials. Please try again.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/admin')
def admin_dashboard():
    if not login_required('admin')():
        return redirect(url_for('login'))

    conn = get_connection()
    cur  = conn.cursor(dictionary=True)

    cur.execute("SELECT COUNT(*) AS c FROM students")
    total_students = cur.fetchone()['c']

    cur.execute("SELECT COUNT(*) AS c FROM teachers")
    total_teachers = cur.fetchone()['c']

    cur.execute("SELECT COUNT(*) AS c FROM attendance WHERE date=%s", (date.today(),))
    today_attendance = cur.fetchone()['c']

    cur.execute("SELECT COUNT(*) AS c FROM subjects")
    total_subjects = cur.fetchone()['c']

    # Last 7 days attendance chart data
    labels, counts = [], []
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        cur.execute("SELECT COUNT(*) AS c FROM attendance WHERE date=%s", (d,))
        labels.append(d.strftime('%b %d'))
        counts.append(cur.fetchone()['c'])

    # Recent attendance
    cur.execute("""
        SELECT a.*, s.full_name, s.roll_number, sub.subject_name
        FROM attendance a
        JOIN students s    ON a.student_id = s.id
        LEFT JOIN subjects sub ON a.subject_id = sub.id
        ORDER BY a.created_at DESC LIMIT 10
    """)
    recent = cur.fetchall()

    cur.close(); conn.close()
    return render_template('admin_dashboard.html',
        total_students=total_students,
        total_teachers=total_teachers,
        today_attendance=today_attendance,
        total_subjects=total_subjects,
        chart_labels=json.dumps(labels),
        chart_counts=json.dumps(counts),
        recent_attendance=recent,
        now_hour=datetime.now().hour
    )

# Students CRUD ────────────────────────────────────────────────────────────────

@app.route('/admin/students')
def admin_students():
    if not login_required('admin')():
        return redirect(url_for('login'))
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM students ORDER BY created_at DESC")
    students = cur.fetchall()
    cur.close(); conn.close()
    return render_template('admin_students.html', students=students)

@app.route('/admin/students/add', methods=['GET', 'POST'])
def add_student():
    if not login_required('admin')():
        return redirect(url_for('login'))

    if request.method == 'POST':
        data = request.form
        conn = get_connection()
        cur  = conn.cursor()

        # Create user account
        hashed = generate_password_hash(data['password'])
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (%s,%s,'student')",
            (data['username'], hashed)
        )
        user_id = cur.lastrowid

        # Student record
        cur.execute("""
            INSERT INTO students (user_id, roll_number, full_name, email, phone, department, semester)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (user_id, data['roll_number'], data['full_name'],
              data['email'], data['phone'], data['department'], data['semester']))

        conn.commit()
        cur.close(); conn.close()
        flash('Student added successfully!', 'success')
        return redirect(url_for('admin_students'))

    return render_template('add_student.html')

@app.route('/admin/students/edit/<int:sid>', methods=['GET', 'POST'])
def edit_student(sid):
    if not login_required('admin')():
        return redirect(url_for('login'))
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)

    if request.method == 'POST':
        data = request.form
        cur.execute("""
            UPDATE students SET full_name=%s, email=%s, phone=%s,
            department=%s, semester=%s WHERE id=%s
        """, (data['full_name'], data['email'], data['phone'],
              data['department'], data['semester'], sid))
        conn.commit()
        flash('Student updated.', 'success')
        cur.close(); conn.close()
        return redirect(url_for('admin_students'))

    cur.execute("SELECT * FROM students WHERE id=%s", (sid,))
    student = cur.fetchone()
    cur.close(); conn.close()
    return render_template('edit_student.html', student=student)

@app.route('/admin/students/delete/<int:sid>')
def delete_student(sid):
    if not login_required('admin')():
        return redirect(url_for('login'))
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT user_id FROM students WHERE id=%s", (sid,))
    row = cur.fetchone()
    cur.execute("DELETE FROM students WHERE id=%s", (sid,))
    if row and row['user_id']:
        cur.execute("DELETE FROM users WHERE id=%s", (row['user_id'],))
    conn.commit()
    cur.close(); conn.close()
    flash('Student deleted.', 'warning')
    return redirect(url_for('admin_students'))

# Teachers CRUD ────────────────────────────────────────────────────────────────

@app.route('/admin/teachers')
def admin_teachers():
    if not login_required('admin')():
        return redirect(url_for('login'))
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM teachers ORDER BY created_at DESC")
    teachers = cur.fetchall()
    cur.close(); conn.close()
    return render_template('admin_teachers.html', teachers=teachers)

@app.route('/admin/teachers/add', methods=['GET', 'POST'])
def add_teacher():
    if not login_required('admin')():
        return redirect(url_for('login'))

    if request.method == 'POST':
        data = request.form
        conn = get_connection()
        cur  = conn.cursor()
        hashed = generate_password_hash(data['password'])
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (%s,%s,'teacher')",
            (data['username'], hashed)
        )
        user_id = cur.lastrowid
        cur.execute("""
            INSERT INTO teachers (user_id, employee_id, full_name, email, phone, department)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (user_id, data['employee_id'], data['full_name'],
              data['email'], data['phone'], data['department']))
        conn.commit()
        cur.close(); conn.close()
        flash('Teacher added successfully!', 'success')
        return redirect(url_for('admin_teachers'))

    return render_template('add_teacher.html')

@app.route('/admin/teachers/delete/<int:tid>')
def delete_teacher(tid):
    if not login_required('admin')():
        return redirect(url_for('login'))
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT user_id FROM teachers WHERE id=%s", (tid,))
    row = cur.fetchone()
    cur.execute("DELETE FROM teachers WHERE id=%s", (tid,))
    if row and row['user_id']:
        cur.execute("DELETE FROM users WHERE id=%s", (row['user_id'],))
    conn.commit()
    cur.close(); conn.close()
    flash('Teacher deleted.', 'warning')
    return redirect(url_for('admin_teachers'))

# Face Registration ────────────────────────────────────────────────────────────

@app.route('/admin/register_face/<int:sid>')
def register_face(sid):
    if not login_required('admin')():
        return redirect(url_for('login'))
    result = capture_face_images(str(sid), num_images=30)
    if result['success']:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("UPDATE students SET face_encoded=1 WHERE id=%s", (sid,))
        conn.commit()
        cur.close(); conn.close()
        # Retrain automatically
        train_model()
        flash(f"Face registered: {result['message']}", 'success')
    else:
        flash(f"Face registration failed: {result['message']}", 'danger')
    return redirect(url_for('admin_students'))

@app.route('/admin/train')
def admin_train():
    if not login_required('admin')():
        return redirect(url_for('login'))
    result = train_model()
    flash(result['message'], 'success' if result['success'] else 'danger')
    return redirect(url_for('admin_dashboard'))

# Subjects ─────────────────────────────────────────────────────────────────────

@app.route('/admin/subjects')
def admin_subjects():
    if not login_required('admin')():
        return redirect(url_for('login'))
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT sub.*, t.full_name AS teacher_name
        FROM subjects sub
        LEFT JOIN teachers t ON sub.teacher_id = t.id
        ORDER BY sub.created_at DESC
    """)
    subjects = cur.fetchall()
    cur.execute("SELECT id, full_name FROM teachers")
    teachers = cur.fetchall()
    cur.close(); conn.close()
    return render_template('admin_subjects.html', subjects=subjects, teachers=teachers)

@app.route('/admin/subjects/add', methods=['POST'])
def add_subject():
    if not login_required('admin')():
        return redirect(url_for('login'))
    data = request.form
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO subjects (subject_code, subject_name, department, semester, teacher_id)
        VALUES (%s,%s,%s,%s,%s)
    """, (data['subject_code'], data['subject_name'],
          data['department'], data['semester'],
          data['teacher_id'] or None))
    conn.commit()
    cur.close(); conn.close()
    flash('Subject added!', 'success')
    return redirect(url_for('admin_subjects'))

@app.route('/admin/subjects/delete/<int:sub_id>')
def delete_subject(sub_id):
    if not login_required('admin')():
        return redirect(url_for('login'))
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("DELETE FROM subjects WHERE id=%s", (sub_id,))
    conn.commit()
    cur.close(); conn.close()
    flash('Subject deleted.', 'warning')
    return redirect(url_for('admin_subjects'))

# Attendance Reports ───────────────────────────────────────────────────────────

@app.route('/admin/attendance')
def admin_attendance():
    if not login_required('admin')():
        return redirect(url_for('login'))
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)

    filters = []
    params  = []
    if request.args.get('date'):
        filters.append("a.date=%s"); params.append(request.args['date'])
    if request.args.get('student'):
        filters.append("s.roll_number LIKE %s"); params.append(f"%{request.args['student']}%")
    if request.args.get('subject'):
        filters.append("a.subject_id=%s"); params.append(request.args['subject'])

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    cur.execute(f"""
        SELECT a.*, s.full_name, s.roll_number, sub.subject_name, t.full_name AS teacher_name
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        LEFT JOIN subjects sub ON a.subject_id = sub.id
        LEFT JOIN teachers t   ON a.teacher_id  = t.id
        {where}
        ORDER BY a.date DESC, a.time_in DESC
        LIMIT 200
    """, params)
    records = cur.fetchall()

    cur.execute("SELECT id, subject_name FROM subjects")
    subjects = cur.fetchall()
    cur.close(); conn.close()
    return render_template('admin_attendance.html', records=records, subjects=subjects)

@app.route('/admin/attendance/export')
def export_attendance():
    if not login_required('admin')():
        return redirect(url_for('login'))
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT s.roll_number, s.full_name, sub.subject_name,
               a.date, a.time_in, a.status, a.marked_by
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        LEFT JOIN subjects sub ON a.subject_id = sub.id
        ORDER BY a.date DESC
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()

    si = io.StringIO()
    writer = csv.DictWriter(si, fieldnames=['roll_number','full_name','subject_name',
                                            'date','time_in','status','marked_by'])
    writer.writeheader()
    writer.writerows(rows)
    output = io.BytesIO(si.getvalue().encode())
    return send_file(output, mimetype='text/csv',
                     download_name=f'attendance_{date.today()}.csv',
                     as_attachment=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TEACHER
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/teacher')
def teacher_dashboard():
    if not login_required('teacher')():
        return redirect(url_for('login'))

    conn = get_connection()
    cur  = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM teachers WHERE user_id=%s", (session['user_id'],))
    teacher = cur.fetchone()
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('logout'))

    session['teacher_id'] = teacher['id']

    cur.execute("""
        SELECT sub.*, COUNT(a.id) AS total_records
        FROM subjects sub
        LEFT JOIN attendance a ON sub.id = a.subject_id
        WHERE sub.teacher_id = %s
        GROUP BY sub.id
    """, (teacher['id'],))
    subjects = cur.fetchall()

    cur.execute("""
        SELECT a.*, s.full_name, s.roll_number, sub.subject_name
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        LEFT JOIN subjects sub ON a.subject_id = sub.id
        WHERE a.teacher_id = %s AND a.date = %s
        ORDER BY a.time_in DESC
    """, (teacher['id'], date.today()))
    today_records = cur.fetchall()

    # Last 7-day chart
    labels, counts = [], []
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        cur.execute("SELECT COUNT(*) AS c FROM attendance WHERE teacher_id=%s AND date=%s",
                    (teacher['id'], d))
        labels.append(d.strftime('%b %d'))
        counts.append(cur.fetchone()['c'])

    cur.close(); conn.close()
    return render_template('teacher_dashboard.html',
        teacher=teacher,
        subjects=subjects,
        today_records=today_records,
        chart_labels=json.dumps(labels),
        chart_counts=json.dumps(counts)
    )

@app.route('/teacher/attendance/start/<int:subject_id>')
def start_attendance(subject_id):
    if not login_required('teacher')():
        return redirect(url_for('login'))
    session['active_subject_id'] = subject_id
    return render_template('take_attendance.html',
                           subject_id=subject_id,
                           teacher_id=session.get('teacher_id', 0))

@app.route('/video_feed')
def video_feed():
    subject_id = session.get('active_subject_id', 0)
    teacher_id = session.get('teacher_id', 0)
    return Response(
        generate_recognition_stream(subject_id, teacher_id),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/teacher/attendance/view')
def teacher_attendance():
    if not login_required('teacher')():
        return redirect(url_for('login'))
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    teacher_id = session.get('teacher_id')

    if request.args.get('subject_id'):
        cur.execute("""
            SELECT a.*, s.full_name, s.roll_number, sub.subject_name
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            LEFT JOIN subjects sub ON a.subject_id = sub.id
            WHERE a.teacher_id=%s AND a.subject_id=%s
            ORDER BY a.date DESC
        """, (teacher_id, request.args['subject_id']))
    else:
        cur.execute("""
            SELECT a.*, s.full_name, s.roll_number, sub.subject_name
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            LEFT JOIN subjects sub ON a.subject_id = sub.id
            WHERE a.teacher_id=%s
            ORDER BY a.date DESC LIMIT 100
        """, (teacher_id,))

    records = cur.fetchall()
    cur.execute("SELECT id, subject_name FROM subjects WHERE teacher_id=%s", (teacher_id,))
    subjects = cur.fetchall()
    cur.close(); conn.close()
    return render_template('teacher_attendance.html', records=records, subjects=subjects)

@app.route('/teacher/attendance/export')
def teacher_export():
    if not login_required('teacher')():
        return redirect(url_for('login'))
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT s.roll_number, s.full_name, sub.subject_name, a.date, a.time_in, a.status
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        LEFT JOIN subjects sub ON a.subject_id = sub.id
        WHERE a.teacher_id=%s ORDER BY a.date DESC
    """, (session.get('teacher_id'),))
    rows = cur.fetchall()
    cur.close(); conn.close()

    si = io.StringIO()
    writer = csv.DictWriter(si, fieldnames=['roll_number','full_name','subject_name','date','time_in','status'])
    writer.writeheader(); writer.writerows(rows)
    output = io.BytesIO(si.getvalue().encode())
    return send_file(output, mimetype='text/csv',
                     download_name=f'my_attendance_{date.today()}.csv',
                     as_attachment=True)

@app.route('/teacher/mark_manual', methods=['POST'])
def mark_manual():
    if not login_required('teacher')():
        return jsonify({'error': 'unauthorized'}), 401
    data = request.json
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO attendance (student_id, subject_id, teacher_id, date, time_in, status, marked_by)
            VALUES (%s,%s,%s,%s,%s,%s,'manual')
            ON DUPLICATE KEY UPDATE status=%s, marked_by='manual'
        """, (data['student_id'], data['subject_id'], session.get('teacher_id'),
              data['date'], datetime.now().strftime('%H:%M:%S'),
              data['status'], data['status']))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close(); conn.close()

# ═══════════════════════════════════════════════════════════════════════════════
# STUDENT
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/student')
def student_dashboard():
    if not login_required('student')():
        return redirect(url_for('login'))

    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM students WHERE user_id=%s", (session['user_id'],))
    student = cur.fetchone()
    if not student:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('logout'))

    # Attendance per subject
    cur.execute("""
        SELECT sub.subject_name, sub.subject_code,
               COUNT(a.id) AS total_classes,
               SUM(CASE WHEN a.status='present' THEN 1 ELSE 0 END) AS present_count
        FROM subjects sub
        LEFT JOIN attendance a ON sub.id = a.subject_id AND a.student_id = %s
        GROUP BY sub.id
    """, (student['id'],))
    subject_stats = cur.fetchall()

    for s in subject_stats:
        s['percentage'] = (
            round(s['present_count'] / s['total_classes'] * 100, 1)
            if s['total_classes'] else 0
        )

    # Recent attendance
    cur.execute("""
        SELECT a.*, sub.subject_name
        FROM attendance a
        LEFT JOIN subjects sub ON a.subject_id = sub.id
        WHERE a.student_id = %s
        ORDER BY a.date DESC, a.time_in DESC LIMIT 20
    """, (student['id'],))
    recent = cur.fetchall()

    # Overall percentage
    cur.execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN status='present' THEN 1 ELSE 0 END) AS present
        FROM attendance WHERE student_id=%s
    """, (student['id'],))
    overall = cur.fetchone()
    overall_pct = (
        round(overall['present'] / overall['total'] * 100, 1)
        if overall['total'] else 0
    )

    cur.close(); conn.close()
    return render_template('student_dashboard.html',
        student=student,
        subject_stats=subject_stats,
        recent_attendance=recent,
        overall_percentage=overall_pct
    )

@app.route('/student/profile', methods=['GET', 'POST'])
def student_profile():
    if not login_required('student')():
        return redirect(url_for('login'))
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM students WHERE user_id=%s", (session['user_id'],))
    student = cur.fetchone()

    if request.method == 'POST':
        file = request.files.get('profile_image')
        if file and allowed_file(file.filename):
            fn = secure_filename(f"student_{student['id']}.jpg")
            file.save(os.path.join(UPLOAD_FOLDER, fn))
            cur.execute("UPDATE students SET profile_image=%s WHERE id=%s",
                        (fn, student['id']))
            conn.commit()
            flash('Profile image updated!', 'success')
            return redirect(url_for('student_profile'))

    cur.close(); conn.close()
    return render_template('student_profile.html', student=student)

# ─── API: live recognized-faces list (JSON) ───────────────────────────────────

@app.route('/api/recognized_today')
def recognized_today():
    if 'user_id' not in session:
        return jsonify([])
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT s.full_name, s.roll_number, a.time_in, a.status
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE a.date = %s AND a.teacher_id = %s
        ORDER BY a.time_in DESC
    """, (date.today(), session.get('teacher_id', 0)))
    rows = cur.fetchall()
    for r in rows:
        if r['time_in']:
            r['time_in'] = str(r['time_in'])
    cur.close(); conn.close()
    return jsonify(rows)

# ─── Bootstrap ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
