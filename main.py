import cv2
import mediapipe as mp
import pyautogui
import time
import numpy as np

# ==========================================
# CONFIGURATION
# ==========================================
SENSITIVITY_X = 1.8
SENSITIVITY_Y = 1.5
SMOOTH_FACTOR = 0.5

# Thresholds
BLINK_EAR_THRESHOLD = 0.20
MOUTH_MAR_THRESHOLD = 0.6
CLICK_DELAY = 0.4
SHUTDOWN_TIME = 4.0  # Seconds to close eyes for automatic exit

# Screen setup
SCREEN_W, SCREEN_H = pyautogui.size()
pyautogui.FAILSAFE = True

# ==========================================
# INITIALIZE MEDIAPIPE
# ==========================================
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Landmark indices
LEFT_EYE_TOP_BOTTOM = [159, 145]
LEFT_EYE_LEFT_RIGHT = [33, 133]
RIGHT_EYE_TOP_BOTTOM = [386, 374]
RIGHT_EYE_LEFT_RIGHT = [362, 263]
MOUTH_TOP_BOTTOM = [13, 14]
MOUTH_LEFT_RIGHT = [78, 308]

# Global state variables
prev_x, prev_y = 0, 0
last_click_time = 0
eyes_closed_start_time = None  # To track shutdown timer


def get_aspect_ratio(landmarks, top_bottom, left_right):
    """Calculates the ratio to detect blinks or mouth opening."""
    p_top = landmarks[top_bottom[0]]
    p_bottom = landmarks[top_bottom[1]]
    p_left = landmarks[left_right[0]]
    p_right = landmarks[left_right[1]]

    dist_v = np.sqrt((p_top.x - p_bottom.x) ** 2 + (p_top.y - p_bottom.y) ** 2)
    dist_h = np.sqrt((p_left.x - p_right.x) ** 2 + (p_left.y - p_right.y) ** 2)
    return dist_v / dist_h


# ==========================================
# MAIN LOOP
# ==========================================
cap = cv2.VideoCapture(0)

print("--- SYSTEM STARTING ---")
print(f"Close BOTH eyes for {SHUTDOWN_TIME} seconds to EXIT.")

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)

    current_status = "Scanning..."
    status_color = (0, 255, 0)

    if results.multi_face_landmarks:
        landmarks = results.multi_face_landmarks[0].landmark

        # 1. CURSOR MOVEMENT (Nose Tip)
        nose = landmarks[1]
        target_x = np.interp(nose.x, (0.3, 0.7), (0, SCREEN_W))
        target_y = np.interp(nose.y, (0.3, 0.7), (0, SCREEN_H))

        curr_x = prev_x + (target_x - prev_x) * (1 - SMOOTH_FACTOR)
        curr_y = prev_y + (target_y - prev_y) * (1 - SMOOTH_FACTOR)

        pyautogui.moveTo(curr_x, curr_y, _pause=False)
        prev_x, prev_y = curr_x, curr_y
        current_status = "Cursor Active"

        # 2. EYE RATIO CALCULATION
        left_ear = get_aspect_ratio(landmarks, LEFT_EYE_TOP_BOTTOM, LEFT_EYE_LEFT_RIGHT)
        right_ear = get_aspect_ratio(landmarks, RIGHT_EYE_TOP_BOTTOM, RIGHT_EYE_LEFT_RIGHT)

        # 3. AUTO-SHUTDOWN LOGIC (BOTH EYES CLOSED)
        if left_ear < BLINK_EAR_THRESHOLD and right_ear < BLINK_EAR_THRESHOLD:
            if eyes_closed_start_time is None:
                eyes_closed_start_time = time.time()

            elapsed_time = time.time() - eyes_closed_start_time
            countdown = round(SHUTDOWN_TIME - elapsed_time, 1)

            current_status = f"SHUTTING DOWN IN: {countdown}s"
            status_color = (0, 0, 255)  # Red text

            if elapsed_time >= SHUTDOWN_TIME:
                print("System Closed via Eye Timer.")
                break
        else:
            # Reset timer if eyes are opened
            eyes_closed_start_time = None

            # 4. CLICK DETECTION (INDIVIDUAL BLINKS)
            # Only check for clicks if we aren't trying to shut down
            curr_time = time.time()
            if curr_time - last_click_time > CLICK_DELAY:
                if left_ear < BLINK_EAR_THRESHOLD:
                    pyautogui.click(button='left')
                    last_click_time = curr_time
                    current_status = "LEFT CLICK"
                elif right_ear < BLINK_EAR_THRESHOLD:
                    pyautogui.click(button='right')
                    last_click_time = curr_time
                    current_status = "RIGHT CLICK"

        # 5. MOUTH SCROLL
        mar = get_aspect_ratio(landmarks, MOUTH_TOP_BOTTOM, MOUTH_LEFT_RIGHT)
        if mar > MOUTH_MAR_THRESHOLD:
            pyautogui.scroll(-40)
            current_status = "SCROLLING"

        # 6. VISUAL LANDMARKS
        for idx in [159, 145, 386, 374]:  # Eye points
            px, py = int(landmarks[idx].x * w), int(landmarks[idx].y * h)
            cv2.circle(frame, (px, py), 2, (255, 255, 255), -1)

    # UI OVERLAY
    cv2.rectangle(frame, (0, 0), (450, 60), (0, 0, 0), -1)
    cv2.putText(frame, f"STATUS: {current_status}", (15, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)

    cv2.imshow('AI Eye Control Mouse', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()