import os
import pickle
import time

import cv2
import face_recognition
import numpy as np
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

#! ---------------------------- VARIABLEs & SETUP ----------------------------
MQTT_HOST = os.getenv("MQTT_HOST")
MQTT_POST = int(os.getenv("MQTT_POST"))
KEEP_ALIVE = int(os.getenv("KEEP_ALIVE"))
TOPIC_PUB = os.getenv("TOPIC_DOOR")

# Load pre-trained face encodings
print("[INFO] loading encodings...")
with open(".config/encodings.pickle", "rb") as f:
    data = pickle.loads(f.read())

known_face_encodings = data["encodings"]
known_face_names = data["names"]

# Initialize the USB Camera
print("[INFO] initializing USB camera...")
cap = cv2.VideoCapture(2)

if not cap.isOpened():
    print("Error: Could not open video stream.")
    exit()


# Initialize variables
cv_scaler = 4  # Scale factor for resizing frames to improve performance
face_locations = []
face_encodings = []
face_names = []

last_open_time = 0
is_open = False


#! ---------------------------- FUNCs ----------------------------
def process_frame(frame):
    global face_locations, face_encodings, face_names, last_open_time, is_open

    # Resize the frame to improve performance
    resized_frame = cv2.resize(frame, (0, 0), fx=(1 / cv_scaler), fy=(1 / cv_scaler))

    # Convert the image from BGR to RGB color space
    rgb_resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)

    # Detect faces and get face encodings
    face_locations = face_recognition.face_locations(rgb_resized_frame)
    face_encodings = face_recognition.face_encodings(
        rgb_resized_frame, face_locations, model="large"
    )

    face_names = []

    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces(
            known_face_encodings, face_encoding, tolerance=0.45
        )
        name = "Unknown"

        # Use the known face with the smallest distance
        face_distances = face_recognition.face_distance(
            known_face_encodings, face_encoding
        )
        best_match_index = np.argmin(face_distances)
        if matches[best_match_index]:
            name = known_face_names[best_match_index]

            if not is_open or (time.time() - last_open_time > 3):
                client.publish(TOPIC_PUB, "OPEN")
                print(f"Hello, {name}")
                last_open_time = time.time()
                is_open = True

        face_names.append(name)

    if is_open and (time.time() - last_open_time > 3):
        client.publish(TOPIC_PUB, "CLOSE")
        print("Door closed")
        is_open = False

    return frame


def draw_results(frame):
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        top *= cv_scaler
        right *= cv_scaler
        bottom *= cv_scaler
        left *= cv_scaler

        cv2.rectangle(frame, (left, top), (right, bottom), (244, 42, 3), 3)
        cv2.rectangle(
            frame, (left - 3, top - 35), (right + 3, top), (244, 42, 3), cv2.FILLED
        )
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, top - 6), font, 1.0, (255, 255, 255), 1)

    return frame


client = mqtt.Client()
client.connect(MQTT_HOST, MQTT_POST, KEEP_ALIVE)


#! ---------------------------- MAIN LOOP ----------------------------
while True:
    ret, frame = cap.read()
    if not ret:
        print("[ERROR] Unable to capture video")
        break

    processed_frame = process_frame(frame)
    display_frame = draw_results(processed_frame)

    if cv2.waitKey(1) == ord("q"):
        break

# Clean up
cap.release()
cv2.destroyAllWindows()
