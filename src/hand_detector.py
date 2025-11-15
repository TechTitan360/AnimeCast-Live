# src/hand_detector.py
import mediapipe as mp
import math

class HandDetector:
    def __init__(self, max_num_hands=2, detection_confidence=0.7, tracking_confidence=0.7):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=max_num_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence
        )
        self.mp_draw = mp.solutions.drawing_utils

    def process(self, frame_rgb):
        """Return mediapipe results object when given RGB frame."""
        return self.hands.process(frame_rgb)

    @staticmethod
    def landmark_to_pixel(landmark, width, height):
        return int(landmark.x * width), int(landmark.y * height)

    @staticmethod
    def distance(p1, p2):
        return math.hypot(p1[0]-p2[0], p1[1]-p2[1])
