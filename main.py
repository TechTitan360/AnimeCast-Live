# main.py
import cv2
import numpy as np
from src.hand_detector import HandDetector
import src.gesture_logic as gestures
from src.vfx_engine import VFXEngine
from src.utils import put_text, get_grid_position
from src.gesture_logic import GestureState
import time

freeza_state = GestureState(on_frames=3, off_frames=5)
goku_state  = GestureState(on_frames=3, off_frames=5)

FREEZA_PNG = "assets/vfx/freeza/f1.png"
GOKU_PNG   = "assets/vfx/goku/g1.png"

# Performance settings
DETECTION_WIDTH = 640   # MediaPipe processes at lower res
DETECTION_HEIGHT = 360
SKIP_FRAMES = 2         # Process MediaPipe every Nth frame


def main():
    cap = cv2.VideoCapture(0)

    # >>> FIX 1: Increase camera resolution <<<
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    detector = HandDetector(max_num_hands=2)
    vfx = VFXEngine()

    freeza_png = vfx.load_png(FREEZA_PNG)
    goku_png   = vfx.load_png(GOKU_PNG)

    # Pre-generate rotations for smooth performance
    print("⚡ Pre-generating rotations...")
    freeza_rotations = vfx.pregenerate_rotations(freeza_png, steps=72)
    goku_rotations = vfx.pregenerate_rotations(goku_png, steps=72)
    print("✓ Rotations cached!")

    show_skeleton = False
    frame_count = 0
    
    # Cached landmarks for frame skipping
    cached_hands = []
    
    # FPS tracking
    fps_start_time = time.time()
    fps_counter = 0
    current_fps = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]

        # Process MediaPipe only every SKIP_FRAMES frames
        if frame_count % SKIP_FRAMES == 0:
            # Downscale for detection
            small_frame = cv2.resize(frame, (DETECTION_WIDTH, DETECTION_HEIGHT))
            rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            results = detector.process(rgb)
            cached_hands = results.multi_hand_landmarks or []
        
        hands = cached_hands
        frame_count += 1

        active_vfx = None
        vfx_center = None
        vfx_scale  = 1.0

        # ========= FREEZA (Single hand, index up) =========
        if len(hands) == 1:
            hand = hands[0]

            # Check gesture with proper margin parameter
            freeza_active = freeza_state.update(gestures.is_index_finger_up(hand, margin=0.02))
            
            if freeza_active:
                # Scale coordinates back to full resolution
                cx, cy = gestures.get_fingertip_pixel(hand, w, h)

                # Use pre-rotated asset instead of rotating every frame
                angle = (cv2.getTickCount() % 3600) / 20
                rotated = vfx.get_prerotated(freeza_rotations, angle)

                # SCALE: slightly bigger now
                vfx_scale = 0.5  
                vfx_center = (cx, cy)
                active_vfx = rotated

                put_text(frame, "Freeza Beam", (10, 60), color=(200, 100, 255))

        # ========= GOKU (Two hands top row) =========
        elif len(hands) == 2:
            # Scale coordinates back to full resolution
            p0 = gestures.get_palm_center_pixel(hands[0], w, h)
            p1 = gestures.get_palm_center_pixel(hands[1], w, h)

            r0, _ = get_grid_position(p0[0], p0[1], w, h)
            r1, _ = get_grid_position(p1[0], p1[1], w, h)

            # Both palms must be in row 0
            goku_condition = (r0 == 0 and r1 == 0)
            goku_active = goku_state.update(goku_condition)
            
            if goku_active:
                cx = (p0[0] + p1[0]) // 2
                cy = (p0[1] + p1[1]) // 2

                dist = np.sqrt((p0[0]-p1[0])**2 + (p0[1]-p1[1])**2)
                vfx_scale = max(0.7, dist / (goku_png.shape[1] + 1))

                # Use pre-rotated asset
                angle = (cv2.getTickCount() % 3600) / 15
                rotated = vfx.get_prerotated(goku_rotations, angle)

                active_vfx = rotated
                vfx_center = (cx, cy)
                put_text(frame, "Goku Spirit Bomb", (10, 60), color=(100, 200, 255))

        # Reset states when hand count doesn't match
        if len(hands) != 1:
            freeza_state.update(False)
        if len(hands) != 2:
            goku_state.update(False)

        # ========= OVERLAY =========
        if active_vfx is not None:
            frame = vfx.overlay_png(frame, active_vfx, vfx_center, scale=vfx_scale)

        # FPS calculation
        fps_counter += 1
        if time.time() - fps_start_time >= 1.0:
            current_fps = fps_counter
            fps_counter = 0
            fps_start_time = time.time()

        # Display FPS and controls
        put_text(frame, f"FPS: {current_fps}", (10, 30), color=(0, 255, 255), scale=0.8)
        put_text(frame, "Esc: Quit | S: Skeleton", (10, h - 20))
        cv2.imshow("AnimeCast LIVE", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            break
        if key == ord('s'):
            show_skeleton = not show_skeleton

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
