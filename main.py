# main.py
import cv2
import numpy as np
from src.hand_detector import HandDetector
import src.gesture_logic as gestures
from src.vfx_engine import VFXEngine
from src.utils import put_text, get_grid_position
from src.gesture_logic import GestureState, ChargeState
import time
import math

freeza_state = GestureState(on_frames=3, off_frames=5)
freeza_charge = ChargeState(max_charge_time=6.0, release_duration=1.5)
goku_state  = GestureState(on_frames=3, off_frames=5)
goku_charge = ChargeState(max_charge_time=10.0, release_duration=2.0)
rasengan_state = GestureState(on_frames=3, off_frames=5)

FREEZA_PNG = "assets/vfx/freeza/f1.png"
GOKU_PNG   = "assets/vfx/goku/g1.png"
NARUTO_PNG = "assets/vfx/naruto/n1.png"

# Performance settings
DETECTION_WIDTH = 640   # MediaPipe processes at lower res
DETECTION_HEIGHT = 360
SKIP_FRAMES = 2         # Process MediaPipe every Nth frame


def main():
    cap = cv2.VideoCapture(0)

    # Camera resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    detector = HandDetector(max_num_hands=2)
    vfx = VFXEngine()

    freeza_png = vfx.load_png(FREEZA_PNG)
    goku_png   = vfx.load_png(GOKU_PNG)
    naruto_png = vfx.load_png(NARUTO_PNG)

    # Pre-generate rotations for smooth performance
    print("⚡ Pre-generating rotations...")
    freeza_rotations = vfx.pregenerate_rotations(freeza_png, steps=72)
    goku_rotations = vfx.pregenerate_rotations(goku_png, steps=72)
    naruto_rotations = vfx.pregenerate_rotations(naruto_png, steps=72)
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

        # ========= RASENGAN (Single hand, open palm) =========
        # Check FIRST to prioritize over Freeza if both conditions met
        if len(hands) == 1:
            hand = hands[0]
            
            # Check for open palm (all fingers extended)
            rasengan_active = rasengan_state.update(gestures.is_open_palm(hand, margin=0.02))
            
            if rasengan_active:
                # Position at palm center
                palm_x, palm_y = gestures.get_palm_center_pixel(hand, w, h)
                
                # Calculate palm size for proportional scaling
                wrist = hand.landmark[0]
                middle_mcp = hand.landmark[9]
                palm_size = abs(wrist.y - middle_mcp.y) * h
                
                # Scale based on palm size (smaller, more realistic)
                vfx_scale = max(0.15, min(0.3, palm_size / 180))
                
                # Fast spinning rotation for Rasengan
                angle = (cv2.getTickCount() % 3600) / 5  # Much faster rotation
                rotated = vfx.get_prerotated(naruto_rotations, angle)
                
                vfx_center = (palm_x, palm_y)
                active_vfx = rotated
                
                put_text(frame, "RASENGAN!", (10, 60), color=(100, 150, 255), scale=0.9)

        # ========= FREEZA (Single hand, ONLY index finger up with CHARGE-UP) =========
        if len(hands) == 1 and active_vfx is None:
            hand = hands[0]

            # Strict detection: ONLY index finger up, all others down
            freeza_active = freeza_state.update(gestures.is_only_index_finger_up(hand, margin=0.02))
            
            # Update charge state
            is_charging, is_releasing, charge_level = freeza_charge.update(freeza_active)
            
            if freeza_active or is_releasing:
                # Get fingertip position
                cx, cy = gestures.get_fingertip_pixel(hand, w, h)

                # Calculate finger size for base scaling
                tip = hand.landmark[8]
                pip = hand.landmark[6]
                finger_length = abs(tip.y - pip.y) * h
                base_scale = max(0.15, min(0.35, finger_length / 200))
                
                # Calculate pointing direction (from wrist to fingertip)
                wrist = hand.landmark[0]
                wrist_x, wrist_y = int(wrist.x * w), int(wrist.y * h)
                dx = cx - wrist_x
                dy = cy - wrist_y
                angle_rad = math.atan2(dy, dx)
                
                # CHARGING: Reduce size for accuracy
                if is_charging:
                    # Size reduces as charge increases (more focused)
                    charge_reduction = 1.0 - (charge_level * 0.4)  # Reduces to 60% size
                    pulse = 1.0 + (0.08 * math.sin(time.time() * 10))  # Fast pulse
                    vfx_scale = base_scale * charge_reduction * pulse
                    
                    # Rotation slows down while charging (focusing energy)
                    rotation_angle = (cv2.getTickCount() % 3600) / (20 + charge_level * 30)
                    rotated = vfx.get_prerotated(freeza_rotations, rotation_angle)
                    
                    vfx_center = (cx, cy)
                    active_vfx = rotated
                    
                    # Display charge status
                    charge_percent = int(charge_level * 100)
                    put_text(frame, f"Charging Beam... {charge_percent}%", (10, 60), color=(200, 100, 255), scale=0.8)
                    
                    # Small charge indicator near fingertip
                    indicator_radius = int(5 + charge_level * 10)
                    cv2.circle(frame, (cx, cy), indicator_radius, (200, 100, 255), 2)
                
                # RELEASING: Fire beam in pointed direction
                elif is_releasing:
                    release_progress = freeza_charge.get_release_progress()
                    
                    # Beam shoots out in the direction you were pointing
                    beam_distance = release_progress * w * 0.8  # Travels 80% of screen width
                    beam_x = cx + int(beam_distance * math.cos(angle_rad))
                    beam_y = cy + int(beam_distance * math.sin(angle_rad))
                    
                    # Beam stays small and focused
                    release_scale = base_scale * 0.6  # Compact beam
                    
                    # Fast rotation during fire
                    rotation_angle = (cv2.getTickCount() % 3600) / 5
                    rotated = vfx.get_prerotated(freeza_rotations, rotation_angle)
                    
                    # Draw beam trail from finger to current position
                    for i in range(8):
                        trail_progress = release_progress * (i / 8.0)
                        trail_x = cx + int(beam_distance * trail_progress * math.cos(angle_rad))
                        trail_y = cy + int(beam_distance * trail_progress * math.sin(angle_rad))
                        trail_alpha = 1.0 - (i * 0.1)
                        trail_scale = release_scale * (1.0 - i * 0.05)
                        
                        if 0 <= trail_x < w and 0 <= trail_y < h and trail_alpha > 0:
                            trail_vfx = (rotated * trail_alpha).astype(np.uint8)
                            frame = vfx.overlay_png(frame, trail_vfx, (trail_x, trail_y), scale=trail_scale)
                    
                    vfx_center = (beam_x, beam_y)
                    vfx_scale = release_scale
                    active_vfx = rotated
                    
                    put_text(frame, "DEATH BEAM!", (10, 60), color=(255, 100, 200), scale=1.0)
                
                # NORMAL: No charge, normal beam
                else:
                    vfx_scale = base_scale

                # Use pre-rotated asset instead of rotating every frame
                angle = (cv2.getTickCount() % 3600) / 20
                rotated = vfx.get_prerotated(freeza_rotations, angle)

                vfx_center = (cx, cy)
                active_vfx = rotated

                put_text(frame, "Freeza Beam", (10, 60), color=(200, 100, 255))

        # ========= GOKU (Two hands top row with CHARGE-UP) =========
        elif len(hands) == 2:
            # Scale coordinates back to full resolution
            p0 = gestures.get_palm_center_pixel(hands[0], w, h)
            p1 = gestures.get_palm_center_pixel(hands[1], w, h)

            r0, _ = get_grid_position(p0[0], p0[1], w, h)
            r1, _ = get_grid_position(p1[0], p1[1], w, h)

            # Both palms must be in row 0
            goku_condition = (r0 == 0 and r1 == 0)
            goku_active = goku_state.update(goku_condition)
            
            # Update charge state
            is_charging, is_releasing, charge_level = goku_charge.update(goku_active)
            
            if goku_active or is_releasing:
                cx = (p0[0] + p1[0]) // 2
                cy = (p0[1] + p1[1]) // 2

                dist = np.sqrt((p0[0]-p1[0])**2 + (p0[1]-p1[1])**2)
                
                # CHARGING: Start small and grow with charge level + pulsing
                if is_charging:
                    # Start at 0.2x, grow to 1.2x max
                    base_scale = 0.2
                    charge_multiplier = 1.0 + (charge_level * 5.0)  # Grows from 1.0x to 6.0x of base
                    pulse = 1.0 + (0.1 * math.sin(time.time() * 8))  # Subtle pulsing
                    vfx_scale = base_scale * charge_multiplier * pulse
                    
                    # Use pre-rotated asset (faster rotation while charging)
                    angle = (cv2.getTickCount() % 3600) / (15 - charge_level * 10)  # Speeds up
                    rotated = vfx.get_prerotated(goku_rotations, angle)
                    
                    active_vfx = rotated
                    vfx_center = (cx, cy)
                    
                    # Display charge status
                    charge_percent = int(charge_level * 100)
                    put_text(frame, f"CHARGING... {charge_percent}%", (10, 60), color=(100, 200, 255), scale=0.9)
                    
                    # Draw charge bar
                    bar_w = 300
                    bar_h = 25
                    bar_x = (w - bar_w) // 2
                    bar_y = h - 80
                    
                    # Background
                    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (50, 50, 50), -1)
                    # Fill based on charge
                    fill_w = int(bar_w * charge_level)
                    color = (0, int(255 * (1 - charge_level)), int(255 * charge_level))  # Green -> Red
                    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), color, -1)
                    # Border
                    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (255, 255, 255), 2)
                    
                # RELEASING: Shoot upward with animation
                elif is_releasing:
                    release_progress = goku_charge.get_release_progress()
                    
                    # Move upward
                    offset_y = -release_progress * h * 0.9  # Moves up 90% of screen
                    release_cy = cy + int(offset_y)
                    
                    # Grow moderately during release (not too big)
                    release_scale = 1.2 * (1.0 + release_progress * 0.8)  # Max 2.16x
                    
                    # Fast rotation during release
                    angle = (cv2.getTickCount() % 3600) / 3
                    rotated = vfx.get_prerotated(goku_rotations, angle)
                    
                    # Create trail effect
                    for i in range(5):
                        trail_offset = i * 50
                        trail_cy = release_cy + trail_offset
                        if trail_cy < h:
                            trail_scale = release_scale * (1.0 - i * 0.15)
                            trail_alpha = 1.0 - (i * 0.2) - (release_progress * 0.3)
                            if trail_alpha > 0:
                                # Apply transparency by blending
                                trail_vfx = (rotated * trail_alpha).astype(np.uint8)
                                frame = vfx.overlay_png(frame, trail_vfx, (cx, trail_cy), scale=trail_scale)
                    
                    vfx_center = (cx, release_cy)
                    vfx_scale = release_scale
                    active_vfx = rotated
                    
                    put_text(frame, "SPIRIT BOMB RELEASED!", (10, 60), color=(255, 255, 0), scale=1.0)

        # Reset states when hand count doesn't match
        if len(hands) != 1:
            freeza_state.update(False)
            rasengan_state.update(False)
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
