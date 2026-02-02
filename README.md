# AI Eye-Controlled Virtual Mouse 🖱️👁️
An advanced, hands-free human-computer interaction system that allows users to control their computer mouse using real-time facial expressions and eye movements. Built with Python, OpenCV, and MediaPipe.
![alt text](https://img.shields.io/badge/python-3.9.9-blue.svg)

![alt text](https://img.shields.io/badge/license-MIT-green.svg)

![alt text](https://img.shields.io/badge/contributions-welcome-orange.svg)
🌟 Key Features
Precise Cursor Control: Move your mouse cursor smoothly by moving your head/eyes.
Intelligent Blinking:
😉 Left Eye Blink: Performs a Left Click.
😉 Right Eye Blink: Performs a Right Click.
Smart Scrolling: 😲 Open your mouth to trigger an automatic scroll-down action.
Safety Auto-Shutdown: 😴 Close both eyes for 4 seconds to automatically exit the program (no keyboard required).
Anti-Shake Smoothing: Uses Linear Interpolation (LERP) to ensure the cursor doesn't jitter or shake.
Real-time HUD: On-screen status display showing current actions and a shutdown countdown.
🛠️ Tech Stack
Language: Python 3.9.9
Computer Vision: OpenCV
Face Tracking: MediaPipe (Face Mesh)
Automation: PyAutoGUI
Math: NumPy
📥 Installation
1. Clone the repository
code
Bash
git clone https://github.com/YOUR_USERNAME/eye-controlled-virtual-mouse.git
cd eye-controlled-virtual-mouse
2. Install Dependencies
To avoid common version conflicts (specifically the numpy.core.multiarray error), it is recommended to install the following specific versions:
code
Bash
pip install numpy==1.23.5
pip install opencv-python mediapipe pyautogui
🚀 How to Use
Run the script:
code
Bash
python main.py
Position yourself in front of the webcam with good lighting.
The system will start tracking once your face is detected.
🎮 Controls Guide
Action	Control
Move Cursor	Move Head / Eyes
Left Click	Blink Left Eye
Right Click	Blink Right Eye
Scroll Down	Open Mouth
Exit Program	Close both eyes for 4 seconds
Emergency Stop	Move mouse cursor to any corner of the screen
⚙️ Configuration
You can adjust the sensitivity and thresholds at the top of main.py:
SENSITIVITY: Increase this if the mouse moves too slowly.
SMOOTH_FACTOR: Increase (up to 0.9) for smoother movement, or decrease for faster response.
BLINK_EAR_THRESHOLD: Adjust if the system isn't detecting your blinks correctly.
⚠️ Troubleshooting
Error: ImportError: numpy.core.multiarray failed to import
This is a common version mismatch between OpenCV and NumPy. To fix it, run:
pip uninstall numpy and then pip install numpy==1.23.5.
Cursor is Shaking:
Ensure your room is well-lit. Shadows on the face can confuse the landmark detection.
📜 License
This project is licensed under the MIT License - see the LICENSE file for details.
🤝 Contributing
Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are greatly appreciated.
Developed with ❤️ by [Your Name/GitHub Username]
