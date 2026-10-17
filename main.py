"""
AI Virtual Eye & Head Mouse Controller (Upgraded & Ultra-Smooth)
==============================================================
Features:
- Dual-axis One-Euro (1€) adaptive filter for jitter-free, zero-latency tracking.
- Fast Win32 Direct Cursor Engine (0ms hardware-accelerated pointer positioning).
- Eye Muscle Squeeze Detection (No exaggerated full blinks required):
    * Left Eye Muscle Squeeze  = LEFT CLICK (Hold > 0.45s = Mouse Drag & Drop)
    * Right Eye Muscle Squeeze = RIGHT CLICK
    * Both Eyes Closed = Safe Exit Timer (NO clicks on natural bilateral blinks)
- Click-Freeze Stabilization: Freezes cursor during squeezes to prevent facial twitch deflection.
- Bi-directional Hands-Free Scrolling:
    * Mouth Open (relaxed/jaw drop) = SCROLL DOWN
    * Mouth Open + Showing Teeth    = SCROLL UP
    * Smooth continuous scroll accumulator for fluid reading.
- Multi-Tracking Modes:
    * Hybrid Mode (Head anchor + Iris gaze steering for genuine Virtual Eye Mouse)
    * Head Precision Mode (Ultra-stable ergonomic head control)
    * Eye Priority Mode (High iris gaze sensitivity)
- Cyberpunk Glassmorphic HUD with real-time biometric gauges and visual reticles.
- Interactive Help Card [H], Pause/Resume [SPACE], Sensitivity [S], Tracking [T], Recenter [C].
"""

import os
import sys
import time
import math
import urllib.request
import ctypes
import cv2
import numpy as np
import pyautogui
import mediapipe as mp

# ==============================================================================
# PYAUTOGUI & SYSTEM CONFIGURATION
# ==============================================================================
pyautogui.PAUSE = 0.0          # Remove pyautogui's default artificial delay
pyautogui.FAILSAFE = False     # Guarded manually with screen boundary margin
SCREEN_W, SCREEN_H = pyautogui.size()

# ==============================================================================
# FAST WIN32 CURSOR & MOUSE CONTROLLER
# ==============================================================================
class MouseController:
    """
    High-performance native mouse driver using Win32 API on Windows
    with automatic fallback to PyAutoGUI for cross-platform compatibility.
    """
    def __init__(self):
        self.is_windows = (sys.platform == "win32")
        self.is_left_down = False
        if self.is_windows:
            self.user32 = ctypes.windll.user32
            # Event flags
            self.MOUSEEVENTF_LEFTDOWN = 0x0002
            self.MOUSEEVENTF_LEFTUP = 0x0004
            self.MOUSEEVENTF_RIGHTDOWN = 0x0008
            self.MOUSEEVENTF_RIGHTUP = 0x0010
            self.MOUSEEVENTF_WHEEL = 0x0800
        else:
            self.user32 = None

    def move_to(self, x, y):
        """Instant zero-latency cursor positioning."""
        x = max(0, min(SCREEN_W - 1, int(x)))
        y = max(0, min(SCREEN_H - 1, int(y)))
        if self.is_windows:
            self.user32.SetCursorPos(x, y)
        else:
            pyautogui.moveTo(x, y)

    def click_left(self):
        """Simulate single left mouse click."""
        if self.is_windows:
            self.user32.mouse_event(self.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            self.user32.mouse_event(self.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        else:
            pyautogui.click(button='left')

    def click_right(self):
        """Simulate single right mouse click."""
        if self.is_windows:
            self.user32.mouse_event(self.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            self.user32.mouse_event(self.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        else:
            pyautogui.click(button='right')

    def mouse_down_left(self):
        """Hold down left button for dragging."""
        if not self.is_left_down:
            if self.is_windows:
                self.user32.mouse_event(self.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            else:
                pyautogui.mouseDown(button='left')
            self.is_left_down = True

    def mouse_up_left(self):
        """Release left button to drop."""
        if self.is_left_down:
            if self.is_windows:
                self.user32.mouse_event(self.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            else:
                pyautogui.mouseUp(button='left')
            self.is_left_down = False

    def scroll(self, delta):
        """
        Scroll mouse wheel.
        Positive delta = Scroll UP (away from user).
        Negative delta = Scroll DOWN (toward user).
        """
        if self.is_windows:
            # Win32 wheel delta: 120 per standard click
            self.user32.mouse_event(self.MOUSEEVENTF_WHEEL, 0, 0, int(delta), 0)
        else:
            pyautogui.scroll(int(delta / 2.5))


# ==============================================================================
# CONFIGURATION CONSTANTS
# ==============================================================================
MODEL_FILENAME = "face_landmarker.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"

# Eye Muscle Squeeze & Click Thresholds
SQUEEZE_THRESHOLD = 0.24       # Minimum muscle squeeze score (easy to trigger without full blinks)
SQUEEZE_DIFF_THRESHOLD = 0.10  # Asymmetry difference to isolate single-sided squeeze
SQUEEZE_TRIGGER_FRAMES = 2     # Consecutive frames to confirm intentional squeeze (~40-60ms)
DRAG_TRIGGER_FRAMES = 14       # Squeeze frames held to initiate drag (~0.45s)
CLICK_COOLDOWN = 0.32          # Seconds before consecutive clicks can trigger

# Mouth & Teeth Scrolling Thresholds
MOUTH_OPEN_THRESHOLD = 0.28    # Mouth openness threshold to trigger scrolling
TEETH_THRESHOLD = 0.25         # Teeth exposure score to toggle Scroll UP instead of Down
SCROLL_BASE_SPEED = 120        # Wheel clicks per unit
SCROLL_ACCUM_INTERVAL = 0.04   # Accumulator evaluation interval

# General Stability & Safety
DEADZONE_MIN = 1.2             # Pixels: movement below this is completely suppressed
DEADZONE_MAX = 4.5             # Pixels: smooth s-curve ramp up to full movement
BORDER_MARGIN = 4              # Keep cursor within [BORDER_MARGIN, SCREEN - BORDER_MARGIN]
SHUTDOWN_TIME = 3.5            # Seconds with both eyes shut to trigger safe exit

# Sensitivity Presets: (Label, Mult X, Mult Y, 1€ min_cutoff, 1€ beta)
SENSITIVITY_PRESETS = [
    ("Balanced", 1.8, 1.4, 0.60, 0.045),
    ("Fast", 2.5, 2.0, 0.85, 0.075),
    ("Precision", 1.1, 0.9, 0.35, 0.020),
    ("Ultra-Smooth", 1.5, 1.2, 0.25, 0.015),
]

# Tracking Modes: (Label, Iris Weight)
TRACKING_MODES = [
    ("Hybrid (Eye + Head)", 0.22),
    ("Head Precision", 0.0),
    ("Eye Priority", 0.45),
]


# ==============================================================================
# ONE-EURO ADAPTIVE FILTER
# ==============================================================================
class OneEuroFilter:
    """
    Adaptive low-pass filter for human head & eye tracking.
    Heavily damps micro-jitters at rest; eliminates lag when moving briskly.
    """
    def __init__(self, min_cutoff=0.6, beta=0.045, d_cutoff=1.0):
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None

    def _alpha(self, cutoff, dt):
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def filter(self, x, t):
        if self.t_prev is None:
            self.x_prev = x
            self.dx_prev = 0.0
            self.t_prev = t
            return x

        dt = t - self.t_prev
        if dt <= 1e-5:
            return self.x_prev

        # Estimate derivative (speed) with low-pass filtering
        dx = (x - self.x_prev) / dt
        alpha_d = self._alpha(self.d_cutoff, dt)
        dx_hat = alpha_d * dx + (1.0 - alpha_d) * self.dx_prev

        # Dynamic cutoff frequency based on velocity
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        alpha = self._alpha(cutoff, dt)
        x_hat = alpha * x + (1.0 - alpha) * self.x_prev

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t
        return x_hat

    def reset(self):
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None


# ==============================================================================
# MODEL MANAGEMENT & INITIALIZATION
# ==============================================================================
def ensure_model_file():
    """Ensures face_landmarker.task exists, downloads if missing."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(script_dir, MODEL_FILENAME)
    if not os.path.exists(model_path):
        print(f"Downloading MediaPipe Face Landmarker model to {model_path}...")
        try:
            urllib.request.urlretrieve(MODEL_URL, model_path)
            print("Model downloaded successfully!")
        except Exception as e:
            print(f"Error downloading model: {e}")
            sys.exit(1)
    return model_path


def init_face_landmarker(model_path):
    """Initializes the MediaPipe Face Landmarker with Face Blendshapes."""
    BaseOptions = mp.tasks.BaseOptions
    FaceLandmarker = mp.tasks.vision.FaceLandmarker
    FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=VisionRunningMode.VIDEO,
        output_face_blendshapes=True,
        num_faces=1
    )
    return FaceLandmarker.create_from_options(options)


# ==============================================================================
# GEOMETRIC UTILITIES & FEATURE EXTRACTION
# ==============================================================================
def landmark_dist(p1, p2):
    return math.hypot(p1.x - p2.x, p1.y - p2.y)


def get_eye_aspect_ratio(landmarks, is_physical_left=True):
    """
    Computes Eye Aspect Ratio (EAR) for geometric analysis.
    In unmirrored frame:
    - User's physical left eye is the anatomical LEFT eye: 33 (outer), 133 (inner)
    - User's physical right eye is the anatomical RIGHT eye: 263 (outer), 362 (inner)
    """
    if is_physical_left:
        p_c1, p_c2 = landmarks[33], landmarks[133]
        v1_t, v1_b = landmarks[160], landmarks[144]
        v2_t, v2_b = landmarks[158], landmarks[153]
    else:
        p_c1, p_c2 = landmarks[263], landmarks[362]
        v1_t, v1_b = landmarks[385], landmarks[380]
        v2_t, v2_b = landmarks[387], landmarks[373]

    d_h = landmark_dist(p_c1, p_c2)
    if d_h < 1e-4:
        return 0.3
    d_v = (landmark_dist(v1_t, v1_b) + landmark_dist(v2_t, v2_b)) / 2.0
    return d_v / d_h


def compute_eye_muscle_squeeze(bs_map, landmarks):
    """
    Calculates real-time eye muscle squeeze score for left and right eyes.
    Detects subtle muscle squeezes, winks, squints, and cheek contractions
    without requiring an exaggerated full eyelid closure.
    """
    # 1. Neural Blendshape Muscle Signals
    l_blink = bs_map.get('eyeBlinkLeft', 0.0)
    l_squint = bs_map.get('eyeSquintLeft', 0.0)
    l_cheek = bs_map.get('cheekSquintLeft', 0.0)
    l_brow = bs_map.get('browDownLeft', 0.0)

    r_blink = bs_map.get('eyeBlinkRight', 0.0)
    r_squint = bs_map.get('eyeSquintRight', 0.0)
    r_cheek = bs_map.get('cheekSquintRight', 0.0)
    r_brow = bs_map.get('browDownRight', 0.0)

    # 2. Geometric EAR Supplement
    l_ear = get_eye_aspect_ratio(landmarks, is_physical_left=True)
    r_ear = get_eye_aspect_ratio(landmarks, is_physical_left=False)
    # EAR drop below 0.25 indicates eyelid narrowing
    ear_l_drop = max(0.0, min(1.0, (0.26 - l_ear) / 0.12)) if l_ear < 0.26 else 0.0
    ear_r_drop = max(0.0, min(1.0, (0.26 - r_ear) / 0.12)) if r_ear < 0.26 else 0.0

    # Squeeze Score calculation: blends blink, orbicularis squint, cheek lift, and EAR
    left_squeeze = max(
        l_blink * 0.55 + l_squint * 0.35 + l_cheek * 0.20 + l_brow * 0.10,
        l_squint * 0.65 + l_cheek * 0.45,
        l_blink,
        ear_l_drop
    )
    right_squeeze = max(
        r_blink * 0.55 + r_squint * 0.35 + r_cheek * 0.20 + r_brow * 0.10,
        r_squint * 0.65 + r_cheek * 0.45,
        r_blink,
        ear_r_drop
    )

    return max(0.0, min(1.0, left_squeeze)), max(0.0, min(1.0, right_squeeze))


def get_mouth_aspect_ratio(landmarks):
    """Computes vertical to horizontal mouth ratio."""
    d_v = landmark_dist(landmarks[13], landmarks[14])
    d_h = landmark_dist(landmarks[78], landmarks[308])
    if d_h < 1e-4:
        return 0.0
    return d_v / d_h


def compute_teeth_exposure(bs_map, frame, landmarks):
    """
    Robust multimodal detection of teeth exposure:
    1. Blendshapes:
       - mouthUpperUpLeft & mouthUpperUpRight (raising upper lip exposes top teeth)
       - mouthLowerDownLeft & mouthLowerDownRight (lowering bottom lip exposes bottom teeth)
       - mouthSmileLeft & mouthSmileRight (broad smile exposes teeth)
       - Subtracted by mouthFunnel & mouthPucker ('O' shape mouth hides teeth)
    2. Computer Vision Pixel Brightness:
       - Samples the interior mouth cavity between inner lips (landmarks 13 & 14)
       - Calculates bright, low-saturation pixel ratio (white teeth vs dark oral cavity)
    """
    # 1. Blendshapes component
    u_l = bs_map.get('mouthUpperUpLeft', 0.0)
    u_r = bs_map.get('mouthUpperUpRight', 0.0)
    d_l = bs_map.get('mouthLowerDownLeft', 0.0)
    d_r = bs_map.get('mouthLowerDownRight', 0.0)
    s_l = bs_map.get('mouthSmileLeft', 0.0)
    s_r = bs_map.get('mouthSmileRight', 0.0)
    funnel = bs_map.get('mouthFunnel', 0.0)
    pucker = bs_map.get('mouthPucker', 0.0)

    raw_blend = (u_l + u_r + d_l + d_r) * 0.75 + (s_l + s_r) * 0.35 - (funnel + pucker) * 0.45
    teeth_bs_score = max(0.0, min(1.0, raw_blend * 1.6))

    # 2. Computer Vision Inner-Mouth Pixel Analysis
    teeth_pixel_score = 0.0
    try:
        h, w = frame.shape[:2]
        p_upper = landmarks[13]
        p_lower = landmarks[14]
        p_left = landmarks[78]
        p_right = landmarks[308]

        ymin = int(min(p_upper.y, p_lower.y) * h)
        ymax = int(max(p_upper.y, p_lower.y) * h)
        xmin = int(min(p_left.x, p_right.x) * w)
        xmax = int(max(p_left.x, p_right.x) * w)

        pad_y = max(1, int((ymax - ymin) * 0.15))
        ymin = max(0, ymin - pad_y)
        ymax = min(h, ymax + pad_y)
        xmin = max(0, xmin)
        xmax = min(w, xmax)

        if ymax - ymin >= 4 and xmax - xmin >= 8:
            roi = frame[ymin:ymax, xmin:xmax]
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            # Teeth mask: bright, low saturation
            mask = cv2.inRange(hsv, (0, 0, 115), (180, 95, 255))
            teeth_pixel_score = float(np.count_nonzero(mask)) / float(mask.size + 1e-5)
            teeth_pixel_score = min(1.0, teeth_pixel_score * 2.8)
    except Exception:
        teeth_pixel_score = 0.0

    # Fused Teeth Score
    final_score = 0.65 * teeth_bs_score + 0.35 * teeth_pixel_score
    return max(0.0, min(1.0, final_score))


def compute_eye_gaze_offset(landmarks, bs_map):
    """
    Computes horizontal & vertical gaze deflection vector.
    Fuses iris landmark offsets with gaze blendshapes.
    """
    # Blendshape gaze
    look_in_l = bs_map.get('eyeLookInLeft', 0.0)
    look_out_l = bs_map.get('eyeLookOutLeft', 0.0)
    look_in_r = bs_map.get('eyeLookInRight', 0.0)
    look_out_r = bs_map.get('eyeLookOutRight', 0.0)
    look_up = (bs_map.get('eyeLookUpLeft', 0.0) + bs_map.get('eyeLookUpRight', 0.0)) / 2.0
    look_down = (bs_map.get('eyeLookDownLeft', 0.0) + bs_map.get('eyeLookDownRight', 0.0)) / 2.0

    # User looking to user's right: Left eye looks IN, Right eye looks OUT
    bs_gaze_x = (look_in_l + look_out_r) / 2.0 - (look_out_l + look_in_r) / 2.0
    bs_gaze_y = look_down - look_up

    # Iris landmark offset relative to eye corners
    try:
        # Physical Left Eye (anatomical left: 33 outer, 133 inner, 468 iris)
        w_l = abs(landmarks[133].x - landmarks[33].x)
        iris_l_ratio = (landmarks[468].x - min(landmarks[33].x, landmarks[133].x)) / (w_l + 1e-5) - 0.5

        # Physical Right Eye (anatomical right: 263 outer, 362 inner, 473 iris)
        w_r = abs(landmarks[263].x - landmarks[362].x)
        iris_r_ratio = (landmarks[473].x - min(landmarks[263].x, landmarks[362].x)) / (w_r + 1e-5) - 0.5

        iris_gaze_x = (iris_l_ratio + iris_r_ratio) / 2.0
    except Exception:
        iris_gaze_x = 0.0

    # Weighted blend
    gaze_x = 0.6 * bs_gaze_x + 0.4 * (iris_gaze_x * 2.0)
    gaze_y = bs_gaze_y
    return gaze_x, gaze_y


# ==============================================================================
# HUD & GRAPHICS RENDERING ENGINE
# ==============================================================================
def draw_glass_rect(img, x, y, w, h, alpha=0.72, color=(20, 22, 28)):
    """Renders a semi-transparent glassmorphic panel with border."""
    ih, iw = img.shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(iw, x + w), min(ih, y + h)
    if x2 > x1 and y2 > y1:
        roi = img[y1:y2, x1:x2]
        colored_rect = np.full_like(roi, color, dtype=np.uint8)
        cv2.addWeighted(colored_rect, alpha, roi, 1.0 - alpha, 0, roi)
        cv2.rectangle(img, (x1, y1), (x2, y2), (70, 75, 90), 1)


def draw_metric_bar(img, x, y, w, h, label, val, thresh, max_val=1.0, active_color=(0, 230, 255)):
    """Renders a sleek biometric telemetry gauge with active glow."""
    cv2.putText(img, label, (x, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 205, 215), 1, cv2.LINE_AA)
    # Background
    cv2.rectangle(img, (x, y), (x + w, y + h), (35, 38, 48), -1)

    # Progress
    norm_val = max(0.0, min(1.0, val / max_val))
    bar_w = int(w * norm_val)
    is_active = val >= thresh
    color = active_color if is_active else (130, 135, 145)
    if bar_w > 0:
        cv2.rectangle(img, (x, y), (x + bar_w, y + h), color, -1)

    # Threshold indicator
    tx = x + int(w * (thresh / max_val))
    tick_color = (255, 255, 255) if is_active else (0, 0, 240)
    cv2.line(img, (tx, y - 2), (tx, y + h + 2), tick_color, 1)


def draw_scroll_indicator(img, direction_is_up, speed_factor):
    """Renders floating animated scroll feedback chevrons."""
    ih, iw = img.shape[:2]
    cx = iw - 45
    cy = ih // 2

    color = (0, 240, 120) if direction_is_up else (255, 90, 240)
    label = "SCROLL UP" if direction_is_up else "SCROLL DOWN"

    # Semi-transparent backing pill
    draw_glass_rect(img, iw - 130, cy - 42, 115, 84, alpha=0.75, color=(18, 20, 26))
    cv2.putText(img, label, (iw - 122, cy - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA)

    # Animated arrow chevrons
    t_pulse = int((time.time() * 6) % 3)
    offsets = [-10, 0, 10] if direction_is_up else [10, 0, -10]

    for i, dy in enumerate(offsets):
        arrow_y = cy + 10 + dy
        p1 = (cx - 14, arrow_y + (8 if direction_is_up else -8))
        p2 = (cx, arrow_y)
        p3 = (cx + 14, arrow_y + (8 if direction_is_up else -8))
        c_use = color if i == t_pulse else (70, 75, 85)
        cv2.polylines(img, [np.array([p1, p2, p3], dtype=np.int32)], False, c_use, 2, cv2.LINE_AA)


def draw_help_card(img):
    """Draws floating quick-start reference modal."""
    ih, iw = img.shape[:2]
    cw, ch = 500, 300
    cx = (iw - cw) // 2
    cy = (ih - ch) // 2

    draw_glass_rect(img, cx, cy, cw, ch, alpha=0.94, color=(14, 16, 22))
    cv2.rectangle(img, (cx, cy), (cx + cw, cy + ch), (0, 220, 255), 1)

    cv2.putText(img, "AI VIRTUAL EYE MOUSE - QUICK GUIDE", (cx + 25, cy + 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 230, 255), 2, cv2.LINE_AA)

    instructions = [
        ("Left Eye Muscle Squeeze", "Single Left Click (Hold > 0.45s = Drag & Drop)"),
        ("Right Eye Muscle Squeeze", "Single Right Click"),
        ("Both Eyes Closed (3.5s)", "Safe Auto-Exit Timer (Natural blinks ignored)"),
        ("Mouth Open", "Scroll DOWN continuously"),
        ("Mouth Open + Show Teeth", "Scroll UP continuously"),
        ("[C] Key", "Recalibrate cursor center to current posture"),
        ("[S] Key", "Cycle Sensitivity (Balanced / Fast / Precision / Smooth)"),
        ("[T] Key", "Cycle Tracking Mode (Hybrid / Head / Eye Priority)"),
        ("[SPACE]", "Pause / Resume Mouse Movement"),
        ("[D] Key", "Toggle HUD biometrics overlay"),
        ("[H] Key", "Toggle this help guide modal"),
        ("[Q] or [ESC]", "Quit application cleanly"),
    ]

    y_pos = cy + 54
    for key, desc in instructions:
        cv2.putText(img, key, (cx + 18, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (240, 220, 100), 1, cv2.LINE_AA)
        cv2.putText(img, f"-  {desc}", (cx + 185, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (210, 215, 225), 1, cv2.LINE_AA)
        y_pos += 19


# ==============================================================================
# MAIN APPLICATION ENGINE
# ==============================================================================
def main():
    model_path = ensure_model_file()
    landmarker = init_face_landmarker(model_path)
    mouse = MouseController()

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)

    # Sensitivity & Tracking Mode Setup
    preset_idx = 0
    preset_name, sens_x, sens_y, min_cut, beta = SENSITIVITY_PRESETS[preset_idx]
    x_filter = OneEuroFilter(min_cutoff=min_cut, beta=beta)
    y_filter = OneEuroFilter(min_cutoff=min_cut, beta=beta)

    track_mode_idx = 0
    track_mode_name, iris_weight = TRACKING_MODES[track_mode_idx]

    # Posture Center Calibration
    center_x, center_y = 0.5, 0.45
    curr_x, curr_y = SCREEN_W // 2, SCREEN_H // 2
    prev_x, prev_y = curr_x, curr_y

    # Gesture Tracking Counters
    left_squeeze_frames = 0
    right_squeeze_frames = 0
    left_clicked_in_squeeze = False
    right_clicked_in_squeeze = False
    last_click_time = 0.0

    scroll_accumulator = 0.0
    last_scroll_eval = time.time()
    eyes_closed_start_time = None
    is_paused = False
    is_dragging = False
    click_frozen_until = 0.0

    # UI Feedback State
    show_hud = True
    show_help = False
    flash_status = ("ACTIVE", (0, 230, 160), 0.0)

    # Performance
    fps_time = time.time()
    fps_frames = 0
    current_fps = 30.0

    print("==================================================================")
    print("      AI VIRTUAL EYE & HEAD MOUSE READY (UPGRADED & ULTRA-SMOOTH)")
    print("------------------------------------------------------------------")
    print(" [C] Recalibrate cursor center on your posture")
    print(" [S] Switch Sensitivity (Balanced / Fast / Precision / Ultra-Smooth)")
    print(" [T] Switch Tracking Mode (Hybrid / Head / Eye Priority)")
    print(" [SPACE] Pause / Resume Mouse Control")
    print(" [D] Toggle biometric HUD overlay")
    print(" [H] Toggle Quick Help card")
    print(" [Q] or [ESC] Quit application")
    print("------------------------------------------------------------------")
    print(" GESTURES:")
    print(" - Left Eye Muscle Squeeze  -> LEFT CLICK (Hold > 0.45s = DRAG)")
    print(" - Right Eye Muscle Squeeze -> RIGHT CLICK")
    print(" - Mouth Open               -> SCROLL DOWN")
    print(" - Mouth Open + Show Teeth  -> SCROLL UP")
    print(f" - Both Eyes Closed for {SHUTDOWN_TIME}s -> Safe Auto-Exit")
    print("==================================================================")

    while cap.isOpened():
        success, raw_frame = cap.read()
        if not success:
            break

        now = time.time()
        fps_frames += 1
        if now - fps_time >= 1.0:
            current_fps = fps_frames / (now - fps_time)
            fps_frames = 0
            fps_time = now

        # Convert raw frame to RGB for MediaPipe (unmirrored for 100% anatomical accuracy)
        rgb_frame = cv2.cvtColor(raw_frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        timestamp_ms = int(now * 1000)

        results = landmarker.detect_for_video(mp_image, timestamp_ms)

        # Mirrored preview display frame for natural mirror-like experience
        display_frame = cv2.flip(raw_frame, 1)
        h, w = display_frame.shape[:2]

        # Biometric Score Placeholders
        user_left_squeeze = 0.0
        user_right_squeeze = 0.0
        mouth_open_score = 0.0
        teeth_score = 0.0
        gaze_x, gaze_y = 0.0, 0.0

        is_squeezing = False
        scrolling_direction = 0  # +1 = Up, -1 = Down, 0 = None

        status_text = "PAUSED" if is_paused else "CURSOR ACTIVE"
        status_color = (0, 160, 255) if is_paused else (0, 230, 160)

        if results and results.face_landmarks and len(results.face_landmarks) > 0:
            landmarks = results.face_landmarks[0]

            # ------------------------------------------------------------------
            # 1. EXTRACT BLENDSHAPES & EYE MUSCLE SQUEEZES
            # ------------------------------------------------------------------
            if results.face_blendshapes and len(results.face_blendshapes) > 0:
                bs_map = {c.category_name: c.score for c in results.face_blendshapes[0]}
                user_left_squeeze, user_right_squeeze = compute_eye_muscle_squeeze(bs_map, landmarks)
                jaw_open = bs_map.get('jawOpen', 0.0)
                mar = get_mouth_aspect_ratio(landmarks)
                mouth_open_score = max(jaw_open, min(1.0, mar * 1.5))
                teeth_score = compute_teeth_exposure(bs_map, raw_frame, landmarks)
                gaze_x, gaze_y = compute_eye_gaze_offset(landmarks, bs_map)
            else:
                # Geometric Fallback
                l_ear = get_eye_aspect_ratio(landmarks, is_physical_left=True)
                r_ear = get_eye_aspect_ratio(landmarks, is_physical_left=False)
                user_left_squeeze = max(0.0, min(1.0, (0.26 - l_ear) / 0.12)) if l_ear < 0.26 else 0.0
                user_right_squeeze = max(0.0, min(1.0, (0.26 - r_ear) / 0.12)) if r_ear < 0.26 else 0.0
                mar = get_mouth_aspect_ratio(landmarks)
                mouth_open_score = min(1.0, mar * 1.6)
                teeth_score = 0.0

            # ------------------------------------------------------------------
            # 2. EYE MUSCLE SQUEEZE & CLICK DETECTION (DIFFERENTIAL ISOLATION)
            # ------------------------------------------------------------------
            # When someone squeezes an eye muscle, that eye produces a significantly
            # higher score than the opposite eye. Natural bilateral blinks produce
            # high scores on BOTH eyes with near-zero asymmetry.
            diff_squeeze = user_left_squeeze - user_right_squeeze

            both_eyes_closed = (user_left_squeeze >= 0.40) and (user_right_squeeze >= 0.40) and (abs(diff_squeeze) < SQUEEZE_DIFF_THRESHOLD)
            left_squeezing = (user_left_squeeze >= SQUEEZE_THRESHOLD) and (diff_squeeze >= SQUEEZE_DIFF_THRESHOLD) and not both_eyes_closed
            right_squeezing = (user_right_squeeze >= SQUEEZE_THRESHOLD) and (-diff_squeeze >= SQUEEZE_DIFF_THRESHOLD) and not both_eyes_closed

            if both_eyes_closed:
                # Bilateral closure: NEVER fire click on natural blinks!
                left_squeeze_frames = 0
                right_squeeze_frames = 0
                left_clicked_in_squeeze = False
                right_clicked_in_squeeze = False

                if eyes_closed_start_time is None:
                    eyes_closed_start_time = now

                elapsed = now - eyes_closed_start_time
                countdown = max(0.0, SHUTDOWN_TIME - elapsed)
                status_text = f"AUTO-EXIT IN: {countdown:.1f}s"
                status_color = (0, 0, 255)

                if elapsed >= SHUTDOWN_TIME:
                    print("Safe Shutdown Triggered via Eye Closure.")
                    break
            else:
                eyes_closed_start_time = None

                # PHYSICAL LEFT EYE MUSCLE SQUEEZE -> LEFT CLICK / DRAG
                if left_squeezing:
                    is_squeezing = True
                    left_squeeze_frames += 1
                    click_frozen_until = now + 0.22  # Freeze cursor so twitch doesn't deflect pointer

                    # Drag initiation (holding muscle squeeze for > 0.45s)
                    if left_squeeze_frames >= DRAG_TRIGGER_FRAMES and not is_dragging:
                        is_dragging = True
                        mouse.mouse_down_left()
                        flash_status = ("DRAGGING...", (0, 180, 255), now + 0.8)

                    # Single Left Click initiation
                    elif left_squeeze_frames >= SQUEEZE_TRIGGER_FRAMES and not left_clicked_in_squeeze and not is_dragging:
                        if now - last_click_time > CLICK_COOLDOWN:
                            mouse.click_left()
                            last_click_time = now
                            left_clicked_in_squeeze = True
                            flash_status = ("LEFT CLICK", (0, 255, 255), now + 0.35)
                else:
                    if is_dragging:
                        # Muscle relaxed: release drag
                        mouse.mouse_up_left()
                        is_dragging = False
                        flash_status = ("DROPPED", (0, 255, 120), now + 0.35)
                    left_squeeze_frames = 0
                    left_clicked_in_squeeze = False

                # PHYSICAL RIGHT EYE MUSCLE SQUEEZE -> RIGHT CLICK
                if right_squeezing:
                    is_squeezing = True
                    right_squeeze_frames += 1
                    click_frozen_until = now + 0.22

                    if right_squeeze_frames >= SQUEEZE_TRIGGER_FRAMES and not right_clicked_in_squeeze:
                        if now - last_click_time > CLICK_COOLDOWN:
                            mouse.click_right()
                            last_click_time = now
                            right_clicked_in_squeeze = True
                            flash_status = ("RIGHT CLICK", (255, 160, 0), now + 0.35)
                else:
                    right_squeeze_frames = 0
                    right_clicked_in_squeeze = False

            # ------------------------------------------------------------------
            # 3. BI-DIRECTIONAL SCROLLING
            # ------------------------------------------------------------------
            # "mouth open for scroll down if show teeth when mouth open will scroll up"
            if not both_eyes_closed and not is_paused:
                if mouth_open_score >= MOUTH_OPEN_THRESHOLD:
                    dt_scroll = now - last_scroll_eval
                    last_scroll_eval = now

                    if teeth_score >= TEETH_THRESHOLD:
                        # SHOWING TEETH -> SCROLL UP
                        scrolling_direction = 1
                        speed_factor = 1.0 + (teeth_score - TEETH_THRESHOLD) * 3.5 + mouth_open_score
                        scroll_accumulator += speed_factor * SCROLL_BASE_SPEED * (dt_scroll / SCROLL_ACCUM_INTERVAL)
                        status_text = "SCROLL UP [TEETH]"
                        status_color = (0, 240, 120)
                    else:
                        # MOUTH OPEN WITHOUT TEETH -> SCROLL DOWN
                        scrolling_direction = -1
                        speed_factor = 1.0 + (mouth_open_score - MOUTH_OPEN_THRESHOLD) * 3.0
                        scroll_accumulator -= speed_factor * SCROLL_BASE_SPEED * (dt_scroll / SCROLL_ACCUM_INTERVAL)
                        status_text = "SCROLL DOWN"
                        status_color = (255, 90, 240)

                    # Smooth continuous scroll dispatch
                    if abs(scroll_accumulator) >= 20.0:
                        mouse.scroll(scroll_accumulator)
                        scroll_accumulator = 0.0
                else:
                    last_scroll_eval = now
                    scroll_accumulator = 0.0

            # ------------------------------------------------------------------
            # 4. ULTRA-SMOOTH CURSOR TRACKING (1€ FILTER + ADAPTIVE DEADZONE)
            # ------------------------------------------------------------------
            # Anchor point: nasal bridge (midpoint of landmarks 168 & 1)
            p_bridge = landmarks[168]
            p_nose = landmarks[1]
            anchor_x = (p_bridge.x + p_nose.x) / 2.0
            anchor_y = (p_bridge.y + p_nose.y) / 2.0

            # Mirrored X coordinate for display and screen mapping
            mirrored_anchor_x = 1.0 - anchor_x

            range_x = 0.17 / sens_x
            range_y = 0.13 / sens_y

            # Normalized offset relative to calibrated center [-1.0, 1.0]
            rel_x = (mirrored_anchor_x - center_x) / range_x
            rel_y = (anchor_y - center_y) / range_y

            # Incorporate Iris Eye Gaze offset based on active tracking mode
            if iris_weight > 0.0:
                rel_x += (gaze_x * iris_weight)
                rel_y += (gaze_y * iris_weight * 0.75)

            rel_x = max(-1.0, min(1.0, rel_x))
            rel_y = max(-1.0, min(1.0, rel_y))

            # Non-linear acceleration (smooth precision at center, easy reach at corners)
            def accel_curve(v, power=1.20):
                return math.copysign(abs(v) ** power, v)

            screen_target_x = (accel_curve(rel_x) * 0.5 + 0.5) * SCREEN_W
            screen_target_y = (accel_curve(rel_y) * 0.5 + 0.5) * SCREEN_H

            # Apply One-Euro Adaptive Filter
            filtered_x = x_filter.filter(screen_target_x, now)
            filtered_y = y_filter.filter(screen_target_y, now)

            # CLICK-FREEZE STABILIZATION:
            # During muscle squeeze clicks, lock cursor so facial twitches don't move pointer.
            # While dragging, cursor is free to move.
            is_click_frozen = (now < click_frozen_until) and not is_dragging

            if not is_paused and not both_eyes_closed and not is_click_frozen:
                dx = filtered_x - prev_x
                dy = filtered_y - prev_y
                dist_moved = math.hypot(dx, dy)

                # Subpixel Adaptive Deadzone with smooth Hermite ramp
                if dist_moved >= DEADZONE_MIN:
                    if dist_moved < DEADZONE_MAX:
                        # Smoothstep ramp
                        t_ramp = (dist_moved - DEADZONE_MIN) / (DEADZONE_MAX - DEADZONE_MIN)
                        factor = t_ramp * t_ramp * (3.0 - 2.0 * t_ramp)
                        move_x = prev_x + dx * factor
                        move_y = prev_y + dy * factor
                    else:
                        move_x = filtered_x
                        move_y = filtered_y

                    curr_x = int(np.clip(move_x, BORDER_MARGIN, SCREEN_W - BORDER_MARGIN))
                    curr_y = int(np.clip(move_y, BORDER_MARGIN, SCREEN_H - BORDER_MARGIN))
                    mouse.move_to(curr_x, curr_y)
                    prev_x, prev_y = curr_x, curr_y

            # ------------------------------------------------------------------
            # 5. VISUAL RETICLES & LANDMARK GLOW ON MIRRORED FRAME
            # ------------------------------------------------------------------
            if show_hud:
                def to_mirrored_px(norm_x, norm_y):
                    return int((1.0 - norm_x) * w), int(norm_y * h)

                # Iris Glowing Target Reticles
                if len(landmarks) > 473:
                    # User's physical left iris (468) -> appears on viewer's left
                    lx, ly = to_mirrored_px(landmarks[468].x, landmarks[468].y)
                    l_color = (0, 255, 255) if left_squeezing else (100, 200, 255)
                    cv2.circle(display_frame, (lx, ly), 3, l_color, -1, cv2.LINE_AA)
                    cv2.circle(display_frame, (lx, ly), 7, l_color, 1, cv2.LINE_AA)

                    # User's physical right iris (473) -> appears on viewer's right
                    rx, ry = to_mirrored_px(landmarks[473].x, landmarks[473].y)
                    r_color = (255, 170, 0) if right_squeezing else (220, 160, 80)
                    cv2.circle(display_frame, (rx, ry), 3, r_color, -1, cv2.LINE_AA)
                    cv2.circle(display_frame, (rx, ry), 7, r_color, 1, cv2.LINE_AA)

                # Nasal Bridge Tracking Crosshair
                bx, by = to_mirrored_px(anchor_x, anchor_y)
                cv2.circle(display_frame, (bx, by), 4, (0, 240, 160), -1, cv2.LINE_AA)
                cv2.circle(display_frame, (bx, by), 12, (0, 240, 160), 1, cv2.LINE_AA)
                cv2.line(display_frame, (bx - 16, by), (bx + 16, by), (0, 240, 160), 1, cv2.LINE_AA)
                cv2.line(display_frame, (bx, by - 16), (bx, by + 16), (0, 240, 160), 1, cv2.LINE_AA)

                # Lip Contour Highlight during mouth gestures
                if mouth_open_score >= MOUTH_OPEN_THRESHOLD:
                    lip_color = (0, 240, 120) if teeth_score >= TEETH_THRESHOLD else (255, 90, 240)
                    for pt_idx in [13, 14, 78, 308]:
                        px, py = to_mirrored_px(landmarks[pt_idx].x, landmarks[pt_idx].y)
                        cv2.circle(display_frame, (px, py), 2, lip_color, -1, cv2.LINE_AA)

        # ----------------------------------------------------------------------
        # 6. GLASSMORPHIC CYBERPUNK HUD RENDERING
        # ----------------------------------------------------------------------
        if now < flash_status[2]:
            status_text = flash_status[0]
            status_color = flash_status[1]

        if show_hud:
            # Top Glass Header Panel
            draw_glass_rect(display_frame, 10, 10, w - 20, 64, alpha=0.75)

            # Status Badge Pill
            cv2.rectangle(display_frame, (18, 20), (235, 58), (30, 32, 42), -1)
            cv2.rectangle(display_frame, (18, 20), (235, 58), status_color, 1)
            cv2.putText(display_frame, status_text, (28, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.48, status_color, 2, cv2.LINE_AA)

            # Biometric Telemetry Bars
            bar_start_x = 248
            bar_w = 68
            bar_h = 10
            # Physical Left Eye Muscle Squeeze (corresponds to user's left)
            draw_metric_bar(display_frame, bar_start_x, 38, bar_w, bar_h, "L-SQUEEZE",
                            user_left_squeeze, SQUEEZE_THRESHOLD, active_color=(0, 255, 255))
            # Physical Right Eye Muscle Squeeze (corresponds to user's right)
            draw_metric_bar(display_frame, bar_start_x + 76, 38, bar_w, bar_h, "R-SQUEEZE",
                            user_right_squeeze, SQUEEZE_THRESHOLD, active_color=(255, 170, 0))
            # Mouth Openness Bar
            draw_metric_bar(display_frame, bar_start_x + 152, 38, bar_w, bar_h, "MOUTH",
                            mouth_open_score, MOUTH_OPEN_THRESHOLD, active_color=(255, 90, 240))
            # Teeth Exposure Bar
            draw_metric_bar(display_frame, bar_start_x + 228, 38, bar_w, bar_h, "TEETH",
                            teeth_score, TEETH_THRESHOLD, active_color=(0, 240, 120))

            # FPS and Mode Badges
            fps_str = f"FPS: {int(current_fps)}"
            sens_str = f"SENS: {preset_name}"
            track_str = f"MODE: {track_mode_name}"
            cv2.putText(display_frame, fps_str, (w - 105, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (190, 195, 205), 1, cv2.LINE_AA)
            cv2.putText(display_frame, sens_str, (w - 105, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 220, 255), 1, cv2.LINE_AA)
            cv2.putText(display_frame, track_str, (w - 105, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (180, 230, 100), 1, cv2.LINE_AA)

            # Bottom Controls Guide Bar
            draw_glass_rect(display_frame, 10, h - 34, w - 20, 26, alpha=0.65)
            guide_str = "[C] Center  |  [S] Sens  |  [T] Mode  |  [SPACE] Pause  |  [H] Help  |  [Q] Exit"
            cv2.putText(display_frame, guide_str, (22, h - 17), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (210, 215, 225), 1, cv2.LINE_AA)

            # Animated Scroll Feedback
            if scrolling_direction != 0:
                draw_scroll_indicator(display_frame, scrolling_direction > 0, 1.0)

            # Auto-Shutdown Progress Overlay (when both eyes are closed)
            if eyes_closed_start_time is not None:
                elapsed = now - eyes_closed_start_time
                prog = min(1.0, elapsed / SHUTDOWN_TIME)
                pb_w = int((w - 40) * prog)
                cv2.rectangle(display_frame, (20, h - 60), (w - 20, h - 48), (28, 30, 38), -1)
                cv2.rectangle(display_frame, (20, h - 60), (20 + pb_w, h - 48), (0, 0, 255), -1)
                cv2.putText(display_frame, f"CLOSING SYSTEM IN {max(0.0, SHUTDOWN_TIME - elapsed):.1f}s (OPEN EYES TO ABORT)",
                            (25, h - 68), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 120, 255), 1, cv2.LINE_AA)

            # Quick Help Card Modal
            if show_help:
                draw_help_card(display_frame)

        cv2.imshow('AI Virtual Eye & Head Mouse Controller', display_frame)

        # ----------------------------------------------------------------------
        # KEYBOARD SHORTCUTS
        # ----------------------------------------------------------------------
        key = cv2.waitKey(1) & 0xFF
        if key in [ord('q'), 27]:  # 'q' or ESC
            print("Quit requested by user.")
            break
        elif key == ord('c'):
            # Recalibrate screen center to current head posture
            if results and results.face_landmarks and len(results.face_landmarks) > 0:
                lms = results.face_landmarks[0]
                center_x = 1.0 - (lms[168].x + lms[1].x) / 2.0
                center_y = (lms[168].y + lms[1].y) / 2.0
                x_filter.reset()
                y_filter.reset()
                flash_status = ("RE-CENTERED", (255, 255, 255), now + 0.6)
                print(f"Center re-calibrated: ({center_x:.3f}, {center_y:.3f})")
        elif key == ord('s'):
            # Cycle Sensitivity Preset
            preset_idx = (preset_idx + 1) % len(SENSITIVITY_PRESETS)
            preset_name, sens_x, sens_y, min_cut, beta = SENSITIVITY_PRESETS[preset_idx]
            x_filter = OneEuroFilter(min_cutoff=min_cut, beta=beta)
            y_filter = OneEuroFilter(min_cutoff=min_cut, beta=beta)
            flash_status = (f"SENS: {preset_name.upper()}", (0, 255, 255), now + 0.6)
            print(f"Sensitivity preset changed: {preset_name}")
        elif key == ord('t'):
            # Cycle Tracking Mode
            track_mode_idx = (track_mode_idx + 1) % len(TRACKING_MODES)
            track_mode_name, iris_weight = TRACKING_MODES[track_mode_idx]
            flash_status = (f"MODE: {track_mode_name.upper()}", (180, 255, 80), now + 0.6)
            print(f"Tracking mode changed: {track_mode_name}")
        elif key == ord(' '):
            # Pause / Resume Mouse Movement
            is_paused = not is_paused
            state_label = "TRACKING PAUSED" if is_paused else "TRACKING RESUMED"
            flash_color = (0, 100, 255) if is_paused else (0, 255, 160)
            flash_status = (state_label, flash_color, now + 0.8)
            print(state_label)
        elif key == ord('d'):
            show_hud = not show_hud
        elif key == ord('h'):
            show_help = not show_help

    # Clean shutdown
    if is_dragging:
        mouse.mouse_up_left()
    landmarker.close()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
