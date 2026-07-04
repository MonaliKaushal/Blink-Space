# Blink Space 🚀👁️
### An Accessible Eye-Blink Arcade Game

> **Fully playable with ONLY eye blinks** — designed for individuals with severe motor impairments (ALS, quadriplegia, etc.) who cannot use a keyboard, mouse, or controller.

---

## Requirements

| Package | Version |
|---|---|
| Python | 3.10+ |
| pygame | ≥ 2.5 |
| opencv-python | ≥ 4.9 |
| mediapipe | ≥ 0.10 |
| numpy | ≥ 1.24 |

---

## Setup

```bash
# 1. Clone / download the project folder
cd "Blink Space"

# 2. Install dependencies
pip install pygame opencv-python mediapipe numpy

# 3. Run the game
python main.py
```

---

## Controls

| Input | Action |
|---|---|
| **Blink** (webcam) | Fire bullet / Start game |
| `SPACE` | Manual fire (keyboard testing fallback) |
| `R` | Restart immediately |
| `+` / `-` | Raise / lower blink threshold |
| `Q` or `ESC` | Quit |

> **Game Over restart:** Hold a sustained blink for **2 seconds** (a progress bar appears), or press `R`.

---

## How to Play

1. Allow webcam access when prompted.
2. Position your face in the centre of the webcam feed (right panel).
3. Watch the **gold orbiting reticle** rotate around your ship.
4. **Blink** at the exact moment the reticle points toward an incoming pirate sailor to fire a cannonball.
5. Each destroyed pirate scores **+100 points**.
6. Don't let pirates board your ship!

---

## Window Layout

```
┌──────────────────────────┬──────────────────┐
│                          │  CONTROL TOWER   │
│    GAME FIELD (800×800)  │                  │
│                          │  ┌────────────┐  │
│  • Gold reticle orbits   │  │ Live Feed  │  │
│    your ship             │  └────────────┘  │
│  • Blink to fire         │  EAR: 0.0234     │
│  • Avoid pirate boarders │  ● OPEN           │
│                          │  ▓▓▓▓▓░░ gauge   │
│                          │                  │
│                          │  SCORE: 000300   │
│                          │  Instructions… │  │
└──────────────────────────┴──────────────────┘
```

---

## Blink Threshold Calibration

The blink threshold controls how tightly your eye must close to register as a blink. Default: **`0.022`** (normalised eyelid distance).

### When to adjust

| Situation | Action |
|---|---|
| Too many false blinks (flickering EAR bar) | Press `-` to lower threshold |
| Blinks not registering at all | Press `+` to raise threshold |
| Bright lighting / reflections | Try lowering threshold slightly |
| Dim / backlit conditions | Try raising threshold |
| Glasses or contact lenses | Usually fine; if not, raise slightly |

### Live feedback
The right panel shows:
- **EAR value** (Eye Aspect Ratio-style distance) in real time.
- **Threshold marker** (gold vertical line on the gauge bar).
- **EAR history sparkline** — you can see your blinks as valleys.
- **State badge** — `● OPEN` (green) or `● BLINKING` (red).

### Manual threshold edit
Open `vision.py` and change `DEFAULT_THRESHOLD = 0.022` to your preferred value.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `RuntimeError: Cannot open camera index 0` | Change `CAMERA_INDEX = 0` in `main.py` to `1` or `2` |
| Webcam feed is black / frozen | Restart the app; another application may hold the camera |
| Face not detected | Ensure your face is well-lit, centred, and not obstructed |
| Blinks not firing | Press `+` a few times to raise the threshold |
| Too many accidental fires | Press `-` to lower the threshold |
| Low FPS | Close other applications; reduce webcam resolution in `vision.py` |
| Game window doesn't fit screen | Your display resolution must be ≥ 1200×800 |

---

## Project Structure

```
Blink Space/
├── main.py        ← Entry point & game loop
├── vision.py      ← Webcam + MediaPipe blink detection
├── game.py        ← Game entities, physics, collision, rendering
├── ui.py          ← Right panel UI (webcam feed + diagnostics)
├── particles.py   ← Explosions, screen shake, ring effects
└── README.md      ← This file
```

---

## Accessibility Notes

- The game is intentionally designed so **zero fine motor control** is required.
- The only input is a **full eye blink** — even slow or laboured blinks register reliably.
- The 300 ms cooldown prevents accidental double-fires from a single prolonged blink.
- The reticle speed (40°/sec) gives ~9 seconds per full orbit — enough time for motor-planning.

---
