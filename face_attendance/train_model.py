"""
train_model.py
Run this script to (re)train face encodings after adding new student images.

Usage:
    python train_model.py
"""

from face_recognition_helper import train_model

if __name__ == '__main__':
    print("Training face recognition model …")
    result = train_model()
    print(result['message'])
    if result['success']:
        print(f"✓  Encodings saved for {result['students_trained']} student(s).")
    else:
        print("✗  Training failed.")
