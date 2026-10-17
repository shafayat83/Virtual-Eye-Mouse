# AI Virtual Eye & Head Mouse Controller 👁️🖱️

An advanced, ultra-smooth, hands-free computer control system powered by **MediaPipe Face Landmarker (Blendshapes)** and **Fast Win32 Hardware Mouse Acceleration**.

---

## ✨ Features

- **🚀 Silky Smooth Cursor Dynamics:**
  - **Dual-Axis 1€ (One-Euro) Adaptive Filter:** Heavily suppresses micro-tremors and head shivering when stationary; dynamically scales down filtering as velocity increases for zero lag during brisk motions.
  - **Subpixel Hermite Deadzone:** Eliminates cursor vibration around small icons and links while ensuring seamless transitions to movement.
  - **Direct Win32 Driver (`user32.SetCursorPos`):** Hardware-accelerated cursor positioning with 0ms artificial delay.

- **🎯 Eye Muscle Squeeze Clicking (No Full Blinks Needed):**
  - **Left Eye Muscle Squeeze:** Triggers **Left Click** on even subtle squints, eyelid contractions, or winks.
  - **Hold Squeeze (> 0.45s):** Triggers **Mouse Drag** (Left button held down for selecting text, dragging windows, etc.). Relaxing the eye releases the drag (**Drop**).
  - **Right Eye Muscle Squeeze:** Triggers **Right Click**.
  - **Differential Isolation:** Evaluates muscle asymmetry between left and right eyes so normal bilateral blinks **never** trigger accidental clicks.
  - **Click-Freeze Stabilization:** The cursor position locks instantaneously when a muscle squeeze begins, preventing facial muscle twitches from deflecting the pointer.

- **📜 Bi-Directional Hands-Free Scrolling:**
  - **Mouth Open (Relaxed / Jaw Drop):** Continuously **Scrolls DOWN**.
  - **Mouth Open + Showing Teeth:** Continuously **Scrolls UP**.
  - **Multimodal Teeth Detection:** Fuses deep blendshape scores (`mouthUpperUp`, `mouthLowerDown`, `mouthSmile`) with real-time HSV pixel brightness analysis of the oral cavity.
  - **Dynamic Scroll Accumulator:** Smooth continuous scrolling speed proportional to jaw opening and teeth exposure.

- **🎛️ Multi-Tracking Modes:**
  - **Hybrid Mode (Eye Gaze + Head Anchor):** True Virtual Eye Mouse experience combining head pose with real-time Iris gaze vector steering.
  - **Head Precision Mode:** Ultra-stable ergonomic tracking using the nasal bridge.
  - **Eye Priority Mode:** Higher iris sensitivity for hands-free eye-focused navigation.

- **🖥️ Cyberpunk Glassmorphic HUD:**
  - Real-time biometric telemetry meters: `L-SQUEEZE`, `R-SQUEEZE`, `MOUTH`, `TEETH` with calibrated threshold markers.
  - Glowing iris reticles and nasal tracking crosshairs.
  - Animated chevron feedback for scrolling up and down.
  - Floating Quick Help modal card (`[H]`).
  - Safe auto-shutdown countdown when closing both eyes for 3.5 seconds.

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|:---:|:---|
| **`[C]`** | **Recalibrate Center:** Re-centers cursor origin to your current posture. |
| **`[S]`** | **Cycle Sensitivity:** Balanced ➔ Fast ➔ Precision ➔ Ultra-Smooth. |
| **`[T]`** | **Cycle Tracking Mode:** Hybrid (Eye+Head) ➔ Head Precision ➔ Eye Priority. |
| **`[SPACE]`** | **Pause / Resume:** Temporarily freezes cursor to watch videos or type without moving the mouse. |
| **`[D]`** | **Toggle HUD:** Shows / hides the biometric telemetry overlay. |
| **`[H]`** | **Help Card:** Displays the interactive on-screen quick reference modal. |
| **`[Q]` / `[ESC]`** | **Quit:** Gracefully exits the application. |

---

## 📦 Requirements & Installation

Install dependencies using `requirements.txt`:
```bash
pip install -r requirements.txt
```

Contains:
- `opencv-python>=4.10.0`
- `mediapipe>=1.0.0`
- `pyautogui>=0.9.54`
- `numpy>=1.26.0`

---

## 🚀 How to Run

```bash
python main.py
```

*The required `face_landmarker.task` model will be automatically downloaded on first launch if not already present.*
