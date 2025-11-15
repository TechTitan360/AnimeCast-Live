# src/vfx_engine.py
import cv2
import numpy as np
from PIL import Image

class VFXEngine:
    def __init__(self):
        self.cache = {}
        self.rotation_cache = {}  # Store pre-rotated assets

    def load_png(self, path):
        """Load PNG with alpha into numpy RGBA array (H,W,4). Caches result."""
        if path in self.cache:
            return self.cache[path].copy()
        img = Image.open(path).convert("RGBA")
        arr = np.array(img)
        
        # Convert RGB to BGR for OpenCV compatibility (keep alpha as-is)
        # PIL uses RGBA, OpenCV uses BGRA
        arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGRA)
        
        self.cache[path] = arr
        return arr.copy()
    
    def pregenerate_rotations(self, png, steps=72):
        """
        Pre-generate rotated versions of PNG at regular intervals.
        steps=72 means one rotation every 5 degrees (360/72).
        Returns dict: {angle: rotated_png}
        """
        rotations = {}
        angle_step = 360.0 / steps
        h, w = png.shape[:2]
        
        for i in range(steps):
            angle = i * angle_step
            M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
            rotated = cv2.warpAffine(
                png, M, (w, h),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0, 0)
            )
            rotations[angle] = rotated
        
        return rotations
    
    def get_prerotated(self, rotations_dict, angle):
        """
        Get closest pre-rotated asset for given angle.
        rotations_dict: output from pregenerate_rotations()
        angle: target angle in degrees
        """
        # Normalize angle to 0-360
        angle = angle % 360
        
        # Find closest pre-generated angle
        closest = min(rotations_dict.keys(), key=lambda k: abs(k - angle))
        return rotations_dict[closest]
    
    def rotate_png(self, png, angle):
        h, w = png.shape[:2]
        M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
        rotated = cv2.warpAffine(
            png, M, (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_TRANSPARENT
        )
        return rotated


    def overlay_png(self, frame, png_rgba, center_xy, scale=1.0):
        """
        Overlay png_rgba (H,W,4) onto BGR frame at center_xy.
        scale: scaling factor for png.
        Optimized version with pre-multiplied alpha.
        """
        fh, fw = frame.shape[:2]
        ph = int(png_rgba.shape[0] * scale)
        pw = int(png_rgba.shape[1] * scale)
        if ph <= 0 or pw <= 0:
            return frame

        # Resize png only if scale != 1.0 (avoid unnecessary operations)
        if scale != 1.0:
            png_resized = cv2.resize(png_rgba, (pw, ph), interpolation=cv2.INTER_LINEAR)
        else:
            png_resized = png_rgba
            ph, pw = png_resized.shape[:2]

        # Pre-multiply alpha for faster blending
        alpha = png_resized[:, :, 3:4] / 255.0
        
        x_center, y_center = center_xy
        x1 = int(x_center - pw // 2)
        y1 = int(y_center - ph // 2)
        x2 = x1 + pw
        y2 = y1 + ph

        # Clip coordinates
        x1o, y1o = max(0, x1), max(0, y1)
        x2o, y2o = min(fw, x2), min(fh, y2)
        if x1o >= x2o or y1o >= y2o:
            return frame

        # Corresponding png slice
        px1 = x1o - x1
        py1 = y1o - y1
        px2 = px1 + (x2o - x1o)
        py2 = py1 + (y2o - y1o)

        # Extract regions
        roi = frame[y1o:y2o, x1o:x2o]
        fg = png_resized[py1:py2, px1:px2, :3]
        a = alpha[py1:py2, px1:px2]

        # Fast blending with broadcasting
        blended = (a * fg + (1 - a) * roi).astype(np.uint8)
        frame[y1o:y2o, x1o:x2o] = blended
        
        return frame
