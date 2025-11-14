# In main.py
import cv2
import mediapipe as mp
import pyautogui
import time

def start_eye_mouse():
    print("Starting Eye Mouse Script...")
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("Error: Cannot open camera")
        return

    face_mesh = mp.solutions.face_mesh.FaceMesh(refine_landmarks=True)
    screen_w, screen_h = pyautogui.size()

    while True:
        success, frame = cam.read()
        if not success:
            print("Failed to grab frame, skipping.")
            time.sleep(0.5)
            continue

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        output = face_mesh.process(rgb_frame)
        landmark_points = output.multi_face_landmarks
        frame_h, frame_w, _ = frame.shape

        if landmark_points:
            landmarks = landmark_points[0].landmark
            
            # --- Mouse Movement (Iris) ---
            # Using landmark 473 for the center of the right iris for stability
            iris_landmark = landmarks[473]
            screen_x = int(iris_landmark.x * screen_w)
            screen_y = int(iris_landmark.y * screen_h)
            pyautogui.moveTo(screen_x, screen_y)
            
            # --- Click Detection (Left Eye Blink) ---
            left = [landmarks[145], landmarks[159]]
            if (left[0].y - left[1].y) < 0.009: # Tune this threshold
                pyautogui.click()
                pyautogui.sleep(1)
                print("Mouse Clicked")
        
        # We don't need to show the camera window, so we comment this out
        # cv2.imshow('Eye controlled mouse', frame)
        
        if cv2.waitKey(1) & 0xFF == 27:
            break

    print("Stopping Eye Mouse Script...")
    cam.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    start_eye_mouse()