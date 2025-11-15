# src/gesture_logic.py
import math
import time

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


class ChargeState:
    """
    Handles charge-up mechanics for VFX effects.
    Charges over time, auto-releases at max, animates release.
    """
    def __init__(self, max_charge_time=10.0, release_duration=2.0):
        self.is_charging = False
        self.charge_start_time = None
        self.charge_level = 0.0  # 0.0 to 1.0
        self.max_charge_time = max_charge_time
        self.is_released = False
        self.release_time = None
        self.release_duration = release_duration
        
    def update(self, is_active):
        """
        Update charge state based on whether gesture is active.
        Returns: (is_charging, is_releasing, charge_level)
        """
        if is_active:
            if not self.is_charging and not self.is_released:
                # Start charging
                self.is_charging = True
                self.charge_start_time = time.time()
            elif self.is_charging:
                # Continue charging
                elapsed = time.time() - self.charge_start_time
                self.charge_level = min(1.0, elapsed / self.max_charge_time)
                
                # Auto-release at max charge
                if self.charge_level >= 1.0 and not self.is_released:
                    self.trigger_release()
        else:
            # Gesture stopped
            if not self.is_released:
                # Reset if not fully charged
                self.reset()
        
        # Check if release animation is finished
        if self.is_released and not self.is_releasing():
            self.reset()
        
        return self.is_charging, self.is_releasing(), self.charge_level
    
    def trigger_release(self):
        """Trigger the release animation"""
        self.is_released = True
        self.release_time = time.time()
        self.is_charging = False
    
    def is_releasing(self):
        """Check if currently in release animation"""
        if not self.is_released or self.release_time is None:
            return False
        return (time.time() - self.release_time) < self.release_duration
    
    def get_release_progress(self):
        """Get release animation progress (0.0 to 1.0)"""
        if not self.is_releasing():
            return 0.0
        return (time.time() - self.release_time) / self.release_duration
    
    def reset(self):
        """Reset charge state"""
        self.is_charging = False
        self.charge_start_time = None
        self.charge_level = 0.0
        self.is_released = False
        self.release_time = None


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


def is_only_index_finger_up(hand_landmarks, margin=0.02):
    """
    Check if ONLY index finger is extended, all others are down.
    This is more strict - perfect for Freeza beam.
    """
    # Index finger must be up
    index_tip = hand_landmarks.landmark[8]
    index_pip = hand_landmarks.landmark[6]
    index_up = index_tip.y < (index_pip.y - margin)
    
    if not index_up:
        return False
    
    # Middle finger must be down (tip below pip)
    middle_tip = hand_landmarks.landmark[12]
    middle_pip = hand_landmarks.landmark[10]
    middle_down = middle_tip.y > (middle_pip.y - margin)
    
    # Ring finger must be down
    ring_tip = hand_landmarks.landmark[16]
    ring_pip = hand_landmarks.landmark[14]
    ring_down = ring_tip.y > (ring_pip.y - margin)
    
    # Pinky must be down
    pinky_tip = hand_landmarks.landmark[20]
    pinky_pip = hand_landmarks.landmark[18]
    pinky_down = pinky_tip.y > (pinky_pip.y - margin)
    
    # Thumb should be somewhat closed (not extended)
    thumb_tip = hand_landmarks.landmark[4]
    thumb_ip = hand_landmarks.landmark[3]
    thumb_closed = abs(thumb_tip.x - thumb_ip.x) < 0.1  # Thumb not extended sideways
    
    return middle_down and ring_down and pinky_down and thumb_closed


def is_open_palm(hand_landmarks, margin=0.02):
    """
    Check if all fingers are extended (open palm gesture).
    Perfect for: Rasengan, Force Push, Energy Shield, etc.
    """
    # Check if all 4 main fingers are up
    fingers = [
        (8, 6),   # Index
        (12, 10), # Middle
        (16, 14), # Ring
        (20, 18)  # Pinky
    ]
    
    for tip_idx, pip_idx in fingers:
        tip = hand_landmarks.landmark[tip_idx]
        pip = hand_landmarks.landmark[pip_idx]
        if tip.y > (pip.y - margin):  # Finger is down
            return False
    
    return True


def is_fist(hand_landmarks, margin=0.02):
    """
    Check if all fingers are closed (fist gesture).
    Perfect for: Power charge, Punch effects, Shockwave, etc.
    """
    # Check if all 4 main fingers are down
    fingers = [
        (8, 6),   # Index
        (12, 10), # Middle
        (16, 14), # Ring
        (20, 18)  # Pinky
    ]
    
    for tip_idx, pip_idx in fingers:
        tip = hand_landmarks.landmark[tip_idx]
        pip = hand_landmarks.landmark[pip_idx]
        if tip.y < (pip.y + margin):  # Finger is up
            return False
    
    return True


def is_peace_sign(hand_landmarks, margin=0.02):
    """
    Check if index + middle fingers are up, others down.
    Perfect for: Clone Jutsu, Split beam, Double shot, etc.
    """
    # Index up
    index_tip = hand_landmarks.landmark[8]
    index_pip = hand_landmarks.landmark[6]
    index_up = index_tip.y < (index_pip.y - margin)
    
    # Middle up
    middle_tip = hand_landmarks.landmark[12]
    middle_pip = hand_landmarks.landmark[10]
    middle_up = middle_tip.y < (middle_pip.y - margin)
    
    # Ring down
    ring_tip = hand_landmarks.landmark[16]
    ring_pip = hand_landmarks.landmark[14]
    ring_down = ring_tip.y > (ring_pip.y - margin)
    
    # Pinky down
    pinky_tip = hand_landmarks.landmark[20]
    pinky_pip = hand_landmarks.landmark[18]
    pinky_down = pinky_tip.y > (pinky_pip.y - margin)
    
    return index_up and middle_up and ring_down and pinky_down


def is_thumb_up(hand_landmarks):
    """
    Check if only thumb is extended upward.
    Perfect for: Approval effect, Boost power, etc.
    """
    # Thumb tip should be above thumb IP joint
    thumb_tip = hand_landmarks.landmark[4]
    thumb_ip = hand_landmarks.landmark[3]
    thumb_mcp = hand_landmarks.landmark[2]
    
    # Thumb extended upward
    thumb_up = thumb_tip.y < thumb_mcp.y
    
    # All other fingers closed
    index_tip = hand_landmarks.landmark[8]
    index_mcp = hand_landmarks.landmark[5]
    fingers_closed = index_tip.y > index_mcp.y
    
    return thumb_up and fingers_closed


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
