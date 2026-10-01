import os
import pickle
import cv2
import numpy as np
import face_recognition as fr

DATASET_DIR    = r'C:\ai face recognation\face_attendance\dataset\student_faces'
ENCODINGS_FILE = r'C:\ai face recognation\face_attendance\models\face_encodings.pkl'

os.makedirs(os.path.dirname(ENCODINGS_FILE), exist_ok=True)
known_encodings = []
known_ids = []
students_trained = 0

for student_id in os.listdir(DATASET_DIR):
    student_dir = os.path.join(DATASET_DIR, student_id)
    if not os.path.isdir(student_dir):
        continue
    print(f'\nStudent {student_id}...')
    encoded_any = False

    for img_file in os.listdir(student_dir):
        img_path = os.path.join(student_dir, img_file)
        try:
            # Read with OpenCV
            bgr = cv2.imread(img_path)
            if bgr is None:
                continue

            # Resize to standard size
            bgr = cv2.resize(bgr, (640, 480))

            # Convert BGR to RGB
            rgb = bgr[:, :, ::-1]

            # Force contiguous array with correct type
            rgb = np.ascontiguousarray(rgb, dtype=np.uint8)

            # Verify array
            assert rgb.dtype == np.uint8
            assert rgb.ndim == 3
            assert rgb.shape[2] == 3

            print(f'  {img_file} → shape:{rgb.shape} dtype:{rgb.dtype} contiguous:{rgb.flags["C_CONTIGUOUS"]}')

            locations = fr.face_locations(rgb, model='hog')
            if not locations:
                print(f'  No face detected: {img_file}')
                continue

            encs = fr.face_encodings(rgb, locations)
            if encs:
                known_encodings.append(encs[0])
                known_ids.append(student_id)
                encoded_any = True
                print(f'  ✓ Encoded: {img_file}')

        except Exception as e:
            print(f'  ERROR {img_file}: {e}')
            continue

    if encoded_any:
        students_trained += 1
        print(f'  Student {student_id} DONE!')
    else:
        print(f'  Student {student_id} - no faces found!')

with open(ENCODINGS_FILE, 'wb') as f:
    pickle.dump({'encodings': known_encodings, 'ids': known_ids}, f)

print(f'\nFinal: {students_trained} students, {len(known_encodings)} encodings saved')