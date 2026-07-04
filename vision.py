"""
vision.py – Computer Vision, Blink Detection & Head Pose Tracking
=================================================================
Handles webcam capture, MediaPipe Face Mesh landmark extraction,
vertical eyelid distance calculation (EAR-style), blink event firing,
and head pose estimation (yaw / pitch) for camera control.
"""

import math
import os
import time
from dataclasses import dataclass, field
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np

# ---------------------------------------------------------------------------
# Landmark indices (MediaPipe Face Mesh, refine_landmarks=True)
# ---------------------------------------------------------------------------
EYE_TOP_IDX    = 386   # Left eye – upper eyelid
EYE_BOTTOM_IDX = 374   # Left eye – lower eyelid

# Head pose reference landmarks
NOSE_TIP_IDX    = 1    # Nose tip
FACE_LEFT_IDX   = 234  # Outer left cheek edge
FACE_RIGHT_IDX  = 454  # Outer right cheek edge
FACE_TOP_IDX    = 10   # Forehead centre
FACE_BOTTOM_IDX = 152  # Chin tip

# Eye contour points for overlay drawing
EYE_CONTOUR_LEFT  = [33, 160, 158, 133, 153, 144]
EYE_CONTOUR_RIGHT = [263, 387, 385, 362, 380, 373]

# Smoothing / dead-zone
HEAD_SMOOTH_ALPHA = 0.25   # EMA factor (0 = frozen, 1 = instant)
HEAD_DEAD_ZONE    = 0.07   # Fraction of range to ignore (reduce jitter)


# ---------------------------------------------------------------------------
# Data container returned each frame
# ---------------------------------------------------------------------------
@dataclass
class VisionResult:
    frame:       np.ndarray   # BGR webcam frame (original resolution)
    ear:         float        # Raw eyelid distance (normalised coords)
    state:       str          # "OPEN" | "BLINKING"
    blink_fired: bool         # True on the leading edge of a blink only
    head_yaw:    float = 0.0  # -1.0 (hard left) … +1.0 (hard right)
    head_pitch:  float = 0.0  # -1.0 (looking up) … +1.0 (looking down)


# ---------------------------------------------------------------------------
# Main vision class
# ---------------------------------------------------------------------------
class EyeTracker:
    """
    Webcam capture + MediaPipe Face Mesh for real-time:
      • blink detection  (EAR-style eyelid distance)
      • head pose        (yaw / pitch from nose position relative to face)
    """

    DEFAULT_THRESHOLD = 0.022
    COOLDOWN_MS       = 300

    def __init__(self, camera_index: int = 0,
                 threshold: float = DEFAULT_THRESHOLD):
        self.threshold = threshold
        self._cooldown = self.COOLDOWN_MS
        self.camera_index = camera_index

        # Webcam
        self._cap = cv2.VideoCapture(camera_index)
        if not self._cap.isOpened():
            # Try DirectShow on Windows if default API fails
            self._cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
            if not self._cap.isOpened():
                raise RuntimeError(
                    f"Cannot open camera index {camera_index}. "
                    "Check that a webcam is connected and not in use by another app."
                )

        # MediaPipe Face Mesh
        model_path = os.path.join(os.path.dirname(__file__), "face_landmarker.task")
        BaseOptions = mp.tasks.BaseOptions
        FaceLandmarker = mp.tasks.vision.FaceLandmarker
        FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
        VisionRunningMode = mp.tasks.vision.RunningMode

        options = FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=VisionRunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=0.6,
            min_face_presence_confidence=0.6,
            min_tracking_confidence=0.6,
        )
        self._mesh = FaceLandmarker.create_from_options(options)

        # Blink state
        self._prev_state    : str   = "OPEN"
        self._last_blink_ts : float = 0.0
        self._last_ear      : float = 1.0
        self._landmarks     : Optional[list] = None

        # Head pose state (smoothed)
        self._smooth_yaw   : float = 0.0
        self._smooth_pitch : float = 0.0

    def switch_camera(self, new_index: int) -> bool:
        """Closes the current camera and attempts to open the camera at new_index."""
        if self._cap is not None:
            self._cap.release()
        self.camera_index = new_index
        # Try opening camera
        self._cap = cv2.VideoCapture(new_index)
        if not self._cap.isOpened():
            self._cap = cv2.VideoCapture(new_index, cv2.CAP_DSHOW)
        
        success = self._cap.isOpened()
        print(f"[EyeTracker] Switched to camera index {new_index}. Open success: {success}")
        return success

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read(self) -> VisionResult:
        """Capture one frame, run inference, return a VisionResult."""
        ret, frame = self._cap.read()
        if not ret or frame is None:
            blank = np.zeros((480, 640, 3), dtype=np.uint8)
            return VisionResult(blank, self._last_ear, self._prev_state,
                                False, self._smooth_yaw, self._smooth_pitch)

        frame = cv2.flip(frame, 1)   # Mirror so movement feels natural

        # ── Face Mesh inference ──────────────────────────────────────
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = int(time.monotonic() * 1000)
        results = self._mesh.detect_for_video(mp_image, timestamp_ms)

        ear         = self._last_ear
        blink_fired = False
        self._landmarks = None

        if results.face_landmarks:
            lm = results.face_landmarks[0]
            self._landmarks = lm

            # ── EAR (blink distance) ─────────────────────────────────
            top    = lm[EYE_TOP_IDX]
            bottom = lm[EYE_BOTTOM_IDX]
            ear    = abs(top.y - bottom.y)
            self._last_ear = ear

            # ── Head pose ────────────────────────────────────────────
            nose       = lm[NOSE_TIP_IDX]
            face_left  = lm[FACE_LEFT_IDX].x
            face_right = lm[FACE_RIGHT_IDX].x
            face_top   = lm[FACE_TOP_IDX].y
            face_bot   = lm[FACE_BOTTOM_IDX].y

            face_cx = (face_left + face_right) * 0.5
            face_cy = (face_top  + face_bot)   * 0.5
            face_w  = max(face_right - face_left, 0.001)
            face_h  = max(face_bot   - face_top,  0.001)

            # Normalise: centre = 0, edge ≈ ±1
            raw_yaw   = float(np.clip((nose.x - face_cx) / (face_w * 0.5), -1.5, 1.5))
            raw_pitch = float(np.clip((nose.y - face_cy) / (face_h * 0.5), -1.5, 1.5))

            # EMA smoothing
            a = HEAD_SMOOTH_ALPHA
            self._smooth_yaw   = a * raw_yaw   + (1 - a) * self._smooth_yaw
            self._smooth_pitch = a * raw_pitch + (1 - a) * self._smooth_pitch

        yaw   = _apply_dead_zone(self._smooth_yaw)
        pitch = _apply_dead_zone(self._smooth_pitch)

        # ── Blink state machine ──────────────────────────────────────
        now        = time.monotonic()
        cooldown_s = self._cooldown / 1000.0
        new_state  = "BLINKING" if ear < self.threshold else "OPEN"

        if (new_state == "BLINKING"
                and self._prev_state == "OPEN"
                and (now - self._last_blink_ts) >= cooldown_s):
            blink_fired         = True
            self._last_blink_ts = now

        self._prev_state = new_state

        return VisionResult(
            frame       = frame,
            ear         = ear,
            state       = new_state,
            blink_fired = blink_fired,
            head_yaw    = yaw,
            head_pitch  = pitch,
        )

    def draw_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Draw eye-contour and nose crosshair overlay on a copy of the frame."""
        out = frame.copy()
        if self._landmarks is None:
            return out

        h, w = out.shape[:2]
        lm   = self._landmarks

        # Subtle face mesh dots
        for idx in range(min(len(lm), 468)):
            x = int(lm[idx].x * w)
            y = int(lm[idx].y * h)
            cv2.circle(out, (x, y), 1, (30, 55, 55), -1)

        # Eye contours
        for contour in (EYE_CONTOUR_LEFT, EYE_CONTOUR_RIGHT):
            pts = [(int(lm[i].x * w), int(lm[i].y * h)) for i in contour]
            for pt in pts:
                cv2.circle(out, pt, 3, (0, 255, 200), -1)
            arr = np.array(pts, np.int32).reshape((-1, 1, 2))
            cv2.polylines(out, [arr], True, (0, 200, 160), 1)

        # EAR measurement landmarks (gold)
        for idx in (EYE_TOP_IDX, EYE_BOTTOM_IDX):
            x = int(lm[idx].x * w)
            y = int(lm[idx].y * h)
            cv2.circle(out, (x, y), 5, (255, 220, 0), -1)

        # Nose tip crosshair (cyan) – shows head pose tracking point
        nx = int(lm[NOSE_TIP_IDX].x * w)
        ny = int(lm[NOSE_TIP_IDX].y * h)
        cv2.drawMarker(out, (nx, ny), (0, 220, 255),
                       cv2.MARKER_CROSS, 16, 2)

        return out

    def adjust_threshold(self, delta: float) -> None:
        """Nudge the blink threshold up or down (called on +/- keypress)."""
        self.threshold = max(0.005, min(0.08, self.threshold + delta))

    def release(self) -> None:
        """Release webcam and MediaPipe resources."""
        self._cap.release()
        self._mesh.close()


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------
def _apply_dead_zone(value: float, dz: float = HEAD_DEAD_ZONE) -> float:
    """Remove dead zone and remap remaining range back to [-1, 1]."""
    if abs(value) < dz:
        return 0.0
    sign = 1.0 if value > 0 else -1.0
    return sign * min(1.0, (abs(value) - dz) / (1.0 - dz))
