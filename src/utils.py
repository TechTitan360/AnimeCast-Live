# src/utils.py
import cv2
import numpy as np

def put_text(frame, text, pos=(10,30), color=(0,255,0), scale=0.7, thickness=2):
    cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)
    return frame

def get_grid_position(x, y, w, h):
    row_h = h // 3
    col_w = w // 3
    row = y // row_h   # 0,1,2
    col = x // col_w   # 0,1,2
    return row, col
