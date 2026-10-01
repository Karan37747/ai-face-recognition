"""
face_recognition_helper.py  (v3 — Relaxed + Better Lighting)
"""

import os
import cv2
import time
import pickle
import numpy as np
import face_recognition as fr
from datetime import datetime

# DATASET_DIR    = r'C:\ai face recognation\face_attendance\dataset\student_faces'
# ENCODINGS_FILE = r'C:\ai face recognation\face_attendance\models\face_encodings.pkl'
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR    = os.path.join(BASE_DIR, 'dataset', 'student_faces')
ENCODINGS_FILE = os.path.join(BASE_DIR, 'models', 'face_encodings.pkl')

os.makedirs(DATASET_DIR,                     exist_ok=True)
os.makedirs(os.path.dirname(ENCODINGS_FILE), exist_ok=True)


# ─── Lighting enhancement ──────────────────────────────────────────────────────

def enhance_frame(frame: np.ndarray) -> np.ndarray:
    """
    Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    to improve visibility in poor/uneven lighting.
    Works on the L channel of LAB color space so colors stay natural.
    """
    lab   = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l     = clahe.apply(l)
    lab   = cv2.merge((l, a, b))
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def _brightness(frame: np.ndarray) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray))


def _sharpness(frame: np.ndarray) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


# ─── Overlay drawing ───────────────────────────────────────────────────────────

def _draw_overlay(frame, count, total, face_box, status_msg, fps, brightness, sharpness):
    h, w  = frame.shape[:2]
    color_ok  = (0, 200, 100)
    color_bad = (0, 100, 255)

    # Top bar
    bar = frame.copy()
    cv2.rectangle(bar, (0, 0), (w, 58), (20, 20, 30), -1)
    cv2.addWeighted(bar, 0.75, frame, 0.25, 0, frame)

    # Progress bar
    cv2.rectangle(frame, (10, 48), (w - 10, 54), (60, 60, 80), -1)
    prog = int((count / total) * (w - 20))
    cv2.rectangle(frame, (10, 48), (10 + prog, 54), color_ok, -1)

    # Text top bar
    cv2.putText(frame, f"Captured: {count}/{total}",
                (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, f"FPS:{fps:.0f}  B:{brightness:.0f}  S:{sharpness:.0f}",
                (w - 220, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

    # Face bounding box with corners
    if face_box is not None:
        x, y, fw, fh = face_box
        c   = color_ok
        th  = 2
        seg = 22
        # corners
        cv2.line(frame, (x, y),          (x + seg, y),       c, th)
        cv2.line(frame, (x, y),          (x, y + seg),       c, th)
        cv2.line(frame, (x+fw, y),       (x+fw-seg, y),      c, th)
        cv2.line(frame, (x+fw, y),       (x+fw, y+seg),      c, th)
        cv2.line(frame, (x, y+fh),       (x+seg, y+fh),      c, th)
        cv2.line(frame, (x, y+fh),       (x, y+fh-seg),      c, th)
        cv2.line(frame, (x+fw, y+fh),    (x+fw-seg, y+fh),   c, th)
        cv2.line(frame, (x+fw, y+fh),    (x+fw, y+fh-seg),   c, th)

    # Bottom status bar
    bot = frame.copy()
    cv2.rectangle(bot, (0, h - 44), (w, h), (20, 20, 30), -1)
    cv2.addWeighted(bot, 0.7, frame, 0.3, 0, frame)
    cv2.putText(frame, status_msg,
                (12, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 220, 220), 1)

    # Hint
    cv2.putText(frame, "Press Q to quit",
                (w - 130, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (120, 120, 120), 1)

    return frame


# ─── Main capture function ────────────────────────────────────────────────────

def capture_face_images(student_id: str, num_images: int = 30) -> dict:
    """
    Capture face images with:
      - CLAHE lighting enhancement
      - Very relaxed quality thresholds
      - Histogram-equalised detection for low light
      - Auto-retry if frame is bad
      - Mirror view for natural interaction
    """
    student_dir = os.path.join(DATASET_DIR, str(student_id))
    os.makedirs(student_dir, exist_ok=True)

    # Clear old images
    for f in os.listdir(student_dir):
        try:
            os.remove(os.path.join(student_dir, f))
        except Exception:
            pass

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        # Try index 1 (external webcam)
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            return {'success': False, 'count': 0,
                    'message': 'Cannot open webcam. Check camera connection.'}

    # Camera settings
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,   1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT,  720)
    cap.set(cv2.CAP_PROP_FPS,          30)
    cap.set(cv2.CAP_PROP_AUTOFOCUS,    1)

    # Haar cascade — frontal face
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    # Secondary cascade for profile faces
    profile_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml'
    )

    count       = 0
    last_saved  = 0.0
    min_gap     = 0.4       # seconds between saves
    status_msg  = "Look straight at the camera"
    fps         = 30.0
    prev_time   = time.time()

    # Warmup — discard first 10 frames (camera auto-adjusts)
    print("[Capture] Warming up camera…")
    for _ in range(10):
        cap.read()

    print(f"[Capture] Ready. Capturing {num_images} images for student {student_id}…")

    while count < num_images:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.05)
            continue

        # FPS
        now       = time.time()
        fps       = 0.9 * fps + 0.1 * (1.0 / max(now - prev_time, 0.001))
        prev_time = now

        # Mirror flip
        frame = cv2.flip(frame, 1)

        # Apply CLAHE enhancement for better detection
        enhanced = enhance_frame(frame)

        # Brightness & sharpness on ORIGINAL frame
        bright = _brightness(frame)
        sharp  = _sharpness(frame)

        # Prepare grayscale for detection (use enhanced frame)
        gray    = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)

        # ── Very relaxed detection parameters ──
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor  = 1.05,   # smaller step = more detections
            minNeighbors = 4,       # lower = more sensitive
            minSize      = (80, 80),# accept smaller/farther faces
            flags        = cv2.CASCADE_SCALE_IMAGE
        )

        # Fallback to alt cascade if primary finds nothing
        if len(faces) == 0:
            faces = profile_cascade.detectMultiScale(
                gray,
                scaleFactor  = 1.05,
                minNeighbors = 3,
                minSize      = (80, 80)
            )

        face_box = None

        if len(faces) == 0:
            status_msg = "No face detected — move closer or improve lighting"

        elif len(faces) > 1:
            # Pick largest face
            faces    = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
            faces    = faces[:1]
            face_box = tuple(faces[0])
            status_msg = "Multiple faces — using largest one"

        else:
            x, y, fw, fh = faces[0]
            face_box     = (x, y, fw, fh)

            # Only check sharpness (very lenient threshold)
            # Brightness check removed — CLAHE handles it
            if sharp < 20:
                status_msg = f"Too blurry — hold still ({sharp:.0f})"

            elif (now - last_saved) < min_gap:
                status_msg = f"Hold still… ({count}/{num_images})"

            else:
                # SAVE — always save the original (not enhanced) frame
                count     += 1
                last_saved = now
                path       = os.path.join(student_dir, f'{count}.jpg')
                cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                status_msg = f"Saved {count}/{num_images} ✓  B:{bright:.0f} S:{sharp:.0f}"
                print(f"[Capture] {count}/{num_images}  bright={bright:.0f}  sharp={sharp:.0f}")

        # Draw overlay on display frame (show enhanced for better visibility)
        display = _draw_overlay(
            enhanced.copy(), count, num_images,
            face_box, status_msg, fps, bright, sharp
        )
        cv2.imshow('FaceAttend — Face Registration  (Q = quit)', display)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), ord('Q'), 27):
            print("[Capture] Cancelled by user")
            break

    cap.release()
    cv2.destroyAllWindows()

    success = count >= 5   # Accept as low as 5 images
    print(f"[Capture] Finished. {count} images saved for student {student_id}.")
    return {
        'success': success,
        'count':   count,
        'message': f'Captured {count} images for student {student_id}'
    }


# ─── Train model ──────────────────────────────────────────────────────────────

def train_model() -> dict:
    known_encodings  = []
    known_ids        = []
    students_trained = 0

    if not os.path.exists(DATASET_DIR):
        return {'success': False, 'students_trained': 0,
                'message': 'Dataset directory not found'}

    for student_id in os.listdir(DATASET_DIR):
        student_dir = os.path.join(DATASET_DIR, student_id)
        if not os.path.isdir(student_dir):
            continue

        encoded_any = False
        img_files   = [f for f in os.listdir(student_dir)
                       if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

        for img_file in img_files:
            img_path = os.path.join(student_dir, img_file)
            try:
                bgr = cv2.imread(img_path)
                if bgr is None:
                    continue

                # Resize if too large
                h, w = bgr.shape[:2]
                if w > 800:
                    scale = 800 / w
                    bgr   = cv2.resize(bgr, (800, int(h * scale)))

                # BGR → RGB for face_recognition
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                rgb = np.ascontiguousarray(rgb, dtype=np.uint8)

                locations = fr.face_locations(rgb, model='hog')
                if not locations:
                    continue

                encs = fr.face_encodings(rgb, locations)
                if encs:
                    known_encodings.append(encs[0])
                    known_ids.append(student_id)
                    encoded_any = True

            except Exception as e:
                print(f"[Train] Error on {img_file}: {e}")
                continue

        if encoded_any:
            students_trained += 1
            print(f"[Train] Student {student_id} OK")

    data = {'encodings': known_encodings, 'ids': known_ids}
    with open(ENCODINGS_FILE, 'wb') as f:
        pickle.dump(data, f)

    return {
        'success':          True,
        'students_trained': students_trained,
        'message':          f'Trained {students_trained} students, '
                            f'{len(known_encodings)} encodings'
    }


# ─── Load encodings ────────────────────────────────────────────────────────────

def load_encodings() -> dict:
    if not os.path.exists(ENCODINGS_FILE):
        return {'encodings': [], 'ids': []}
    with open(ENCODINGS_FILE, 'rb') as f:
        return pickle.load(f)


# ─── Recognise frame ──────────────────────────────────────────────────────────

def recognize_faces_in_frame(frame: np.ndarray) -> list:
    data = load_encodings()
    if not data['encodings']:
        return []

    # Enhance then downscale
    enhanced = enhance_frame(frame)
    small    = cv2.resize(enhanced, (0, 0), fx=0.25, fy=0.25)
    rgb      = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
    rgb      = np.ascontiguousarray(rgb, dtype=np.uint8)

    boxes = fr.face_locations(rgb, model='hog')
    encs  = fr.face_encodings(rgb, boxes)

    results = []
    for enc, box in zip(encs, boxes):
        distances  = fr.face_distance(data['encodings'], enc)
        best_idx   = int(np.argmin(distances))
        best_dist  = float(distances[best_idx])
        confidence = max(0.0, 1.0 - best_dist)
        student_id = data['ids'][best_idx] if best_dist < 0.55 else 'unknown'
        top, right, bottom, left = [v * 4 for v in box]
        results.append({
            'student_id': student_id,
            'location':   (top, right, bottom, left),
            'confidence': round(confidence * 100, 1)
        })

    return results


# ─── MJPEG stream ─────────────────────────────────────────────────────────────

def generate_recognition_stream(subject_id: int, teacher_id: int):
    from database import get_connection
    from datetime import date as dt_date

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS,         30)

    marked_today: set = set()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame      = cv2.flip(frame, 1)
        enhanced   = enhance_frame(frame)
        recognized = recognize_faces_in_frame(frame)

        for r in recognized:
            top, right, bottom, left = r['location']
            sid   = r['student_id']
            conf  = r['confidence']
            color = (0, 200, 100) if sid != 'unknown' else (60, 60, 220)
            th    = 2
            seg   = 18

            # Corner box
            cv2.line(enhanced, (left,  top),    (left+seg,  top),    color, th)
            cv2.line(enhanced, (left,  top),    (left,   top+seg),   color, th)
            cv2.line(enhanced, (right, top),    (right-seg, top),    color, th)
            cv2.line(enhanced, (right, top),    (right,  top+seg),   color, th)
            cv2.line(enhanced, (left,  bottom), (left+seg,  bottom), color, th)
            cv2.line(enhanced, (left,  bottom), (left,   bottom-seg),color, th)
            cv2.line(enhanced, (right, bottom), (right-seg, bottom), color, th)
            cv2.line(enhanced, (right, bottom), (right,  bottom-seg),color, th)

            label = f"{sid}  {conf}%" if sid != 'unknown' else "Unknown"
            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(enhanced, (left, top - lh - 10), (left + lw + 8, top), color, -1)
            cv2.putText(enhanced, label, (left + 4, top - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

            if sid != 'unknown' and sid not in marked_today:
                marked_today.add(sid)
                conn = get_connection()
                if conn:
                    cur = conn.cursor()
                    try:
                        cur.execute("""
                            INSERT IGNORE INTO attendance
                            (student_id, subject_id, teacher_id, date, time_in, status, marked_by)
                            VALUES (%s,%s,%s,%s,%s,'present','face_recognition')
                        """, (sid, subject_id, teacher_id,
                              dt_date.today(),
                              datetime.now().strftime('%H:%M:%S')))
                        conn.commit()
                    except Exception as e:
                        print(f"[Stream] DB: {e}")
                    finally:
                        cur.close()
                        conn.close()

        _, buf = cv2.imencode('.jpg', enhanced, [cv2.IMWRITE_JPEG_QUALITY, 85])
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n'
               + buf.tobytes() + b'\r\n')

    cap.release()
