# src/gesture_logic.py
import math

class GestureState:
    """
    Stabilizer: on_frames needed to activate, off_frames needed to deactivate.
    """
    def __init__(self, on_frames=3, off_frames=5):
        self.active = False
        self.counter_on = 0
        self.counter_off = 0
        self.on_frames = on_frames
        self.off_frames = off_frames

    def update(self, condition: bool) -> bool:
        if condition:
            self.counter_on += 1
            self.counter_off = 0
            if self.counter_on >= self.on_frames:
                self.active = True
        else:
            self.counter_off += 1
            self.counter_on = 0
            if self.counter_off >= self.off_frames:
                self.active = False
        return self.active


# --- Gesture helpers (mediapipe landmarks expected) ---

def is_index_finger_up(hand_landmarks, margin=0.02):
    """
    Check if index finger is extended (tip above pip).
    hand_landmarks: single-hand landmarks (mediapipe)
    Returns True/False.
    """
    # landmarks indices: 8 = index_finger_tip, 6 = index_finger_pip
    tip = hand_landmarks.landmark[8]
    pip = hand_landmarks.landmark[6]
    return tip.y < (pip.y - margin)


def get_fingertip_pixel(hand_landmarks, frame_w, frame_h):
    lm = hand_landmarks.landmark[8]
    return int(lm.x * frame_w), int(lm.y * frame_h)


def get_palm_center_pixel(hand_landmarks, frame_w, frame_h):
    # approximate palm center as average of wrist (0) and middle_finger_mcp (9)
    wrist = hand_landmarks.landmark[0]
    mid_mcp = hand_landmarks.landmark[9]
    cx = (wrist.x + mid_mcp.x) / 2.0
    cy = (wrist.y + mid_mcp.y) / 2.0
    return int(cx * frame_w), int(cy * frame_h)


def is_goku_pose(p0, p1, frame_w, frame_h, palm_distance_ratio=0.18, y_threshold_ratio=0.65):
    """
    p0, p1: two palm center pixel tuples.
    Returns True if palms are close enough and above a vertical threshold.
    """
    if p0 is None or p1 is None:
        return False
    dist = math.hypot(p0[0] - p1[0], p0[1] - p1[1])
    threshold = palm_distance_ratio * frame_w
    avg_y = (p0[1] + p1[1]) / 2.0
    # palms must be close and above the y threshold (upper portion of frame)
    return (dist < threshold) and (avg_y < y_threshold_ratio * frame_h)
