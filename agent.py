# agent.py
import cv2
import mediapipe as mp
import pyautogui
import socketio
import threading
import time
import base64

# --- Global "Switch" ---
is_running = False

# --- SocketIO Client ---
sio = socketio.Client()

@sio.event
def connect():
    print("Agent connected to server. Waiting for commands...")

@sio.event
def disconnect():
    print("Agent disconnected from server.")

@sio.on('command')
def on_command(data):
    global is_running
    action = data.get('action')
    
    if action == 'start' and not is_running:
        is_running = True
        print("Received START command from server")
    elif action == 'stop' and is_running:
        is_running = False
        print("Received STOP command from server")

# --- Eye-Tracking Loop (CORRECTED) ---
def eye_tracking_loop():
    global is_running
    cam = None
    face_mesh = None
    screen_w, screen_h = pyautogui.size()
    mp_face_mesh = mp.solutions.face_mesh

    while True:
        try:
            # --- Handle STOPPING first ---
            if not is_running:
                if cam is not None:
                    print("Stopping camera...")
                    cam.release()
                    cv2.destroyAllWindows()
                    cam = None
                    # *** ADDED: Send STOPPED signal ***
                    try: # Use try/except in case socket is already closed
                        sio.emit('video_frame', {'image': 'STOPPED'})
                    except Exception: pass
                time.sleep(0.1) # Sleep while idle
                continue # Skip the rest of the loop

            # --- Handle STARTING ---
            if cam is None:
                print("Starting camera...")
                cam = cv2.VideoCapture(0)
                if not cam.isOpened():
                    print("Error: Cannot open camera")
                    is_running = False # Turn off if cam fails
                    continue
                face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True)

            # --- Process Frame ---
            ret, image = cam.read()
            if not ret: continue

            image = cv2.flip(image, 1)
            window_h, window_w, _ = image.shape
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            processed_image = face_mesh.process(rgb_image)

            # --- Face Detection & Mouse Control (if face found) ---
            if processed_image.multi_face_landmarks:
                one_face_landmarks = processed_image.multi_face_landmarks[0].landmark
                # ...(Your existing landmark processing, mouse move, and click logic)...
                for id, landmark in enumerate(one_face_landmarks[474:478]):
                    x = int(landmark.x * window_w)
                    y = int(landmark.y * window_h)
                    cv2.circle(image, (x, y), 3, (0, 0, 255), -1)
                    if id == 1:
                        mouse_x = int(screen_w / window_w * x)
                        mouse_y = int(screen_h / window_h * y)
                        pyautogui.moveTo(mouse_x, mouse_y)
                left_eye = [one_face_landmarks[145], one_face_landmarks[159]]
                for landmark in left_eye:
                    x = int(landmark.x * window_w)
                    y = int(landmark.y * window_h)
                    cv2.circle(image, (x, y), 3, (0, 255, 255), -1)
                if (left_eye[0].y - left_eye[1].y) < 0.01:
                    pyautogui.click()
                    pyautogui.sleep(1)

            # --- Encode and Send Frame (MOVED OUTSIDE the 'if face detected') ---
            _, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 50])
            b64_string = base64.b64encode(buffer).decode('utf-8')
            sio.emit('video_frame', {'image': b64_string})
            # --- END MOVED SECTION ---

            # --- Show Local Window ---
            cv2.imshow("Eye Controlled Mouse", image)
            if cv2.waitKey(10) == 27: # ESC key stops the loop
                is_running = False # This will trigger the cleanup code above on the next loop iteration

        except Exception as e:
            print(f"Error in loop: {e}")
            is_running = False # Ensure loop stops on error
            if cam:
                cam.release()
            cv2.destroyAllWindows()
            cam = None
            # *** ADDED: Send STOPPED signal on error too ***
            try:
                sio.emit('video_frame', {'image': 'STOPPED'})
            except Exception: pass
            time.sleep(1) # Pause after error before potentially restarting

# --- Main Execution ---
if __name__ == '__main__':
    threading.Thread(target=eye_tracking_loop, daemon=True).start()
    
    while True:
        try:
            # Connect to the Node.js server on PORT 3000
            sio.connect('http://127.0.0.1:3000') 
            sio.wait()
        except socketio.exceptions.ConnectionError:
            print("Connection failed. Retrying in 5 seconds...")
            time.sleep(5)