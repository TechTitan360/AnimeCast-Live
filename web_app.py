# web_app.py
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import cv2
import numpy as np
import base64
import math
import time
from src.vfx_engine import VFXEngine
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'animecast-live-secret'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Initialize VFX Engine
vfx = VFXEngine()

# Load and pre-generate VFX assets
print("⚡ Loading VFX assets...")
freeza_png = vfx.load_png("assets/vfx/freeza/f1.png")
goku_png = vfx.load_png("assets/vfx/goku/g1.png")
rasengan_png = vfx.load_png("assets/vfx/naruto/n1.png")

print("⚡ Pre-generating rotations...")
freeza_rotations = vfx.pregenerate_rotations(freeza_png, steps=72)
goku_rotations = vfx.pregenerate_rotations(goku_png, steps=72)
rasengan_rotations = vfx.pregenerate_rotations(rasengan_png, steps=72)
print("✓ Server ready!")

# Store current rotation angle (server-side animation)
rotation_state = {'freeza': 0, 'goku': 0, 'rasengan': 0}

# Store charge state for Spirit Bomb
charge_state = {'level': 0, 'max_time': 10.0, 'start_time': None}


@app.route('/')
def index():
    """Serve the main web app page"""
    return render_template('index.html')


@app.route('/mobile')
def mobile():
    """Serve mobile-optimized version"""
    return render_template('mobile.html')


@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('status', {'message': 'Connected to AnimeCast Live Server'})


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


def is_open_palm(hand):
    """Check if hand is in open palm position"""
    if len(hand) < 21:
        return False
    # Check if all fingertips are higher than their MCPs (except thumb)
    fingers_extended = 0
    # Index, Middle, Ring, Pinky
    for tip_idx, mcp_idx in [(8, 5), (12, 9), (16, 13), (20, 17)]:
        if hand[tip_idx]['y'] < hand[mcp_idx]['y']:
            fingers_extended += 1
    return fingers_extended >= 3

def is_only_index_up(hand):
    """Check if only index finger is up (strict Freeza beam)"""
    if len(hand) < 21:
        return False
    # Index tip above MCP
    index_up = hand[8]['y'] < hand[5]['y']
    # Other fingers down
    middle_down = hand[12]['y'] > hand[9]['y']
    ring_down = hand[16]['y'] > hand[13]['y']
    pinky_down = hand[20]['y'] > hand[17]['y']
    return index_up and middle_down and ring_down and pinky_down

@socketio.on('process_frame')
def handle_frame(data):
    """
    Receive hand landmarks from client, return VFX data
    OPTIMIZED: Only processes gesture logic, client renders VFX
    """
    try:
        hands = data.get('hands', [])
        w, h = data['width'], data['height']
        
        # Reset charge if no hands
        if len(hands) == 0:
            charge_state['start_time'] = None
            charge_state['level'] = 0
            emit('processed_frame', {'vfx_data': None, 'effect': None})
            return
        
        # ========= RASENGAN (Single hand open palm) =========
        if len(hands) == 1:
            hand = hands[0]
            
            # Check for open palm first (higher priority)
            if is_open_palm(hand):
                # Get palm center (wrist + middle_mcp) / 2
                if len(hand) > 9:
                    wrist = hand[0]
                    mid_mcp = hand[9]
                    cx = int(((wrist['x'] + mid_mcp['x']) / 2) * w)
                    cy = int(((wrist['y'] + mid_mcp['y']) / 2) * h)
                    
                    # Animate rotation (fast spin)
                    rotation_state['rasengan'] = (rotation_state['rasengan'] + 15) % 360
                    
                    emit('processed_frame', {
                        'vfx_data': {
                            'type': 'rasengan',
                            'angle': rotation_state['rasengan'],
                            'position': {'x': cx, 'y': cy},
                            'scale': 0.25
                        },
                        'effect': 'Rasengan'
                    })
                    return
            
            # ========= FREEZA (Only index finger up) =========
            elif is_only_index_up(hand):
                if len(hand) > 8:
                    tip = hand[8]
                    cx = int(tip['x'] * w)
                    cy = int(tip['y'] * h)
                    
                    # Animate rotation
                    rotation_state['freeza'] = (rotation_state['freeza'] + 8) % 360
                    
                    emit('processed_frame', {
                        'vfx_data': {
                            'type': 'freeza',
                            'angle': rotation_state['freeza'],
                            'position': {'x': cx, 'y': cy},
                            'scale': 0.3
                        },
                        'effect': 'Freeza Beam'
                    })
                    return
        
        # ========= GOKU SPIRIT BOMB (Two hands top row with charge) =========
        elif len(hands) == 2:
            hand0 = hands[0]
            hand1 = hands[1]
            
            if len(hand0) > 9 and len(hand1) > 9:
                # Get palm centers
                wrist0 = hand0[0]
                mid0 = hand0[9]
                p0x = ((wrist0['x'] + mid0['x']) / 2)
                p0y = ((wrist0['y'] + mid0['y']) / 2)
                
                wrist1 = hand1[0]
                mid1 = hand1[9]
                p1x = ((wrist1['x'] + mid1['x']) / 2)
                p1y = ((wrist1['y'] + mid1['y']) / 2)
                
                # Check if both in top third
                if p0y < 0.33 and p1y < 0.33:
                    # Initialize charge timer
                    if charge_state['start_time'] is None:
                        charge_state['start_time'] = time.time()
                    
                    # Calculate charge level
                    elapsed = time.time() - charge_state['start_time']
                    charge_level = min(1.0, elapsed / charge_state['max_time'])
                    charge_state['level'] = charge_level
                    
                    cx = int(((p0x + p1x) / 2) * w)
                    cy = int(((p0y + p1y) / 2) * h)
                    
                    # Scale grows from 0.2 to 1.2 based on charge
                    vfx_scale = 0.2 + (charge_level * 1.0)
                    
                    # Animate rotation
                    rotation_state['goku'] = (rotation_state['goku'] + 12) % 360
                    
                    emit('processed_frame', {
                        'vfx_data': {
                            'type': 'goku',
                            'angle': rotation_state['goku'],
                            'position': {'x': cx, 'y': cy},
                            'scale': vfx_scale,
                            'charge_level': charge_level
                        },
                        'effect': 'Spirit Bomb'
                    })
                    return
                else:
                    # Reset charge if not in top row
                    charge_state['start_time'] = None
                    charge_state['level'] = 0
        
        # No effect detected - reset charge
        charge_state['start_time'] = None
        charge_state['level'] = 0
        emit('processed_frame', {'vfx_data': None, 'effect': None})
        
    except Exception as e:
        print(f"Error processing frame: {e}")
        import traceback
        traceback.print_exc()
        emit('error', {'message': str(e)})


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🔥 AnimeCast Live - Web Server")
    print("="*60)
    print("\n📱 Access from your device:")
    print("   Desktop: http://localhost:5000")
    print("   Mobile:  http://<your-pc-ip>:5000/mobile")
    print("\n💡 To find your PC IP:")
    print("   Windows: ipconfig")
    print("   Mac/Linux: ifconfig")
    print("\n" + "="*60 + "\n")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
