# 🎓 FaceAttend — AI-Powered Face Recognition Attendance System

A full-stack web application built with **Python Flask**, **OpenCV**, **face_recognition (dlib)**, and **MySQL** that automates student attendance using real-time webcam face detection.

---

## 📁 Project Structure

```
face_attendance/
│
├── app.py                        # Main Flask application (all routes)
├── database.py                   # MySQL setup & helper (run once to init)
├── face_recognition_helper.py    # Face capture, encoding, live stream
├── train_model.py                # CLI script to (re)train the AI model
├── requirements.txt              # Python dependencies
│
├── templates/
│   ├── base.html                 # Shared layout with sidebar
│   ├── login.html                # Role-based login page
│   ├── admin_dashboard.html      # Admin home with charts
│   ├── admin_students.html       # Student list + face registration
│   ├── add_student.html          # Add student form
│   ├── edit_student.html         # Edit student form
│   ├── admin_teachers.html       # Teacher list
│   ├── add_teacher.html          # Add teacher form
│   ├── admin_subjects.html       # Subject management
│   ├── admin_attendance.html     # Filterable attendance report
│   ├── teacher_dashboard.html    # Teacher home with subject cards
│   ├── take_attendance.html      # Live webcam attendance screen
│   ├── teacher_attendance.html   # View + manually edit records
│   ├── student_dashboard.html    # Student attendance summary + charts
│   └── student_profile.html      # Student profile with photo upload
│
├── static/
│   ├── css/custom.css            # Extra styles
│   ├── js/app.js                 # Shared JS utilities
│   └── images/profiles/          # Uploaded profile photos
│
├── dataset/
│   └── student_faces/            # Auto-created face image folders
│       └── <student_id>/         # 20–30 captured JPGs per student
│
└── models/
    └── face_encodings.pkl        # Trained face encodings (auto-generated)
```

---

## ⚙️ Prerequisites

| Tool      | Version       |
|-----------|---------------|
| Python    | 3.8 – 3.11    |
| MySQL     | 5.7+ / 8.x    |
| CMake     | Latest        |
| Visual C++ Build Tools (Windows) or gcc/g++ (Linux/macOS) | — |

> **dlib** requires a C++ compiler and CMake. Install them before running `pip install`.

### Install CMake + build tools

**Ubuntu / Debian**
```bash
sudo apt update
sudo apt install -y cmake build-essential libopenblas-dev liblapack-dev libx11-dev
```

**macOS**
```bash
brew install cmake
xcode-select --install
```

**Windows**
1. Install [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/) (select "Desktop development with C++")
2. Install [CMake](https://cmake.org/download/)

---

## 🚀 Quick Start

### 1. Clone / Extract the project

```bash
cd face_attendance
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ `dlib` can take 5–15 minutes to compile. Be patient.
> If it fails, try: `pip install dlib --no-cache-dir`

### 4. Configure MySQL

Open `database.py` and update the credentials:

```python
DB_CONFIG = {
    'host':     'localhost',
    'user':     'root',
    'password': 'YOUR_MYSQL_PASSWORD',   # ← change this
    'database': 'face_attendance_db'
}
```

### 5. Initialize the database

```bash
python database.py
```

This will:
- Create the `face_attendance_db` database
- Create all 5 tables (`users`, `students`, `teachers`, `subjects`, `attendance`)
- Seed the default **admin** account

```
Default Admin Login:
  Username : admin
  Password : admin123
```

### 6. Run the application

```bash
python app.py
```

Open your browser at: **http://localhost:5000**

---

## 🧑‍💻 User Guide

### 👑 Admin Workflow

1. **Login** → select *Admin*, enter `admin / admin123`
2. **Add Teachers** → `/admin/teachers/add` → fill form → submit
3. **Add Students** → `/admin/students/add` → fill form → submit
4. **Register Student Face** → Students page → click 📷 camera icon
   - Webcam opens automatically
   - System captures **30 face images** and saves them to `dataset/student_faces/<id>/`
   - Model is retrained automatically
5. **Add Subjects** → `/admin/subjects` → click *Add Subject* → assign to a teacher
6. **View Reports** → `/admin/attendance` → filter by date, student, or subject
7. **Export CSV** → click *Export CSV* button

### 👩‍🏫 Teacher Workflow

1. **Login** → select *Teacher*, enter credentials set by admin
2. **Dashboard** shows your subjects as cards
3. **Start Attendance** → click *Start* on any subject card
   - Live webcam feed opens
   - Recognized faces auto-marked **Present** in real time
   - Right panel shows who has been marked
4. **Stop Session** → click the *Stop Session* button (top-right)
5. **View / Edit Records** → Attendance → filter by subject
6. **Manual Override** → change status via dropdown → click ✓ to save

### 🎓 Student Workflow

1. **Login** → select *Student*, enter credentials set by admin
2. **Dashboard** shows:
   - Overall attendance percentage ring
   - Per-subject breakdown with progress bars
   - Recent attendance log
   - Attendance charts
3. **Profile** → upload a profile photo

---

## 🤖 Face Recognition Training

After adding students and registering faces via the admin panel, you can also retrain manually:

```bash
python train_model.py
```

Or via the web UI: **Admin → Train AI Model** (top right button / sidebar link).

The model saves face encodings to `models/face_encodings.pkl`.

**Recognition threshold:** 0.6 (lower = stricter). Adjust in `face_recognition_helper.py`:
```python
if best_dist < 0.6:   # ← change this value
```

---

## 🗃️ Database Tables

| Table        | Description                                           |
|-------------|-------------------------------------------------------|
| `users`      | Login credentials for all roles                      |
| `students`   | Student profiles linked to users                     |
| `teachers`   | Teacher profiles linked to users                     |
| `subjects`   | Courses with optional teacher assignment             |
| `attendance` | Attendance records (unique per student+subject+date) |

---

## 🔧 Configuration Reference

| Setting                  | File                        | Default            |
|--------------------------|-----------------------------|--------------------|
| MySQL credentials        | `database.py` → `DB_CONFIG` | root / (blank)     |
| Face images per student  | `face_recognition_helper.py` → `capture_face_images()` | 30 |
| Recognition threshold    | `face_recognition_helper.py` → `recognize_faces_in_frame()` | 0.6 |
| Flask secret key         | `app.py` → `app.secret_key` | Change for prod!  |
| Upload folder            | `app.py` → `UPLOAD_FOLDER`  | static/images/profiles |
| Server host/port         | `app.py` → `app.run()`      | 0.0.0.0:5000      |

---

## 📦 Key Dependencies

| Package             | Purpose                             |
|--------------------|-------------------------------------|
| Flask              | Web framework                       |
| mysql-connector-python | MySQL database driver           |
| opencv-python      | Webcam capture & image processing   |
| face-recognition   | Face encoding & matching (dlib)     |
| dlib               | Deep learning face descriptor model |
| numpy              | Array operations                    |
| pandas             | Data export helpers                 |
| Werkzeug           | Password hashing, file uploads      |

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| `dlib` install fails | Install CMake + C++ build tools first |
| Webcam not opening | Check `cv2.VideoCapture(0)` — change `0` to `1` for external webcam |
| MySQL connection error | Verify credentials in `database.py`, ensure MySQL service is running |
| Face not recognized | Re-register face in better lighting, retrain model |
| "Teacher profile not found" | Admin must add teacher profile for that username |
| Port 5000 already in use | Change `port=5000` to `port=5001` in `app.py` |

---

## 🔐 Security Notes (Production)

- Change `app.secret_key` to a long random string
- Use environment variables for DB credentials
- Enable HTTPS (SSL certificate)
- Add rate limiting to the login endpoint
- Hash/salt all passwords (already done with Werkzeug)

---

## 📄 License

MIT License — free for educational and personal use.
