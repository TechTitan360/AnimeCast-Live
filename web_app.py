# web_app.py
from flask import Flask, render_template, Response, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import cv2
import numpy as np
import base64
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

print("⚡ Pre-generating rotations...")
freeza_rotations = vfx.pregenerate_rotations(freeza_png, steps=72)
goku_rotations = vfx.pregenerate_rotations(goku_png, steps=72)
print("✓ Server ready!")

# Store current rotation angle (server-side animation)
rotation_state = {'freeza': 0, 'goku': 0}


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


@socketio.on('process_frame')
def handle_frame(data):
    """
    Receive frame + hand landmarks from client, apply VFX, return processed frame
    data format: {
        'frame': base64_encoded_image,
        'hands': [landmark_data],
        'width': int,
        'height': int
    }
    """
    try:
        # Decode frame
        frame_data = base64.b64decode(data['frame'].split(',')[1])
        nparr = np.frombuffer(frame_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        hands = data.get('hands', [])
        w, h = data['width'], data['height']
        
        active_vfx = None
        vfx_center = None
        vfx_scale = 1.0
        effect_name = None
        
        # ========= FREEZA (Single hand, index up) =========
        if len(hands) == 1:
            hand = hands[0]
            # Get fingertip from landmarks (index 8)
            if len(hand) > 8:
                tip = hand[8]
                cx = int(tip['x'] * w)
                cy = int(tip['y'] * h)
                
                # Animate rotation
                rotation_state['freeza'] = (rotation_state['freeza'] + 5) % 360
                rotated = vfx.get_prerotated(freeza_rotations, rotation_state['freeza'])
                
                vfx_scale = 0.5
                vfx_center = (cx, cy)
                active_vfx = rotated
                effect_name = "Freeza Beam"
        
        # ========= GOKU (Two hands top row) =========
        elif len(hands) == 2:
            hand0 = hands[0]
            hand1 = hands[1]
            
            if len(hand0) > 9 and len(hand1) > 9:
                # Get palm centers (average of wrist [0] and middle_mcp [9])
                wrist0 = hand0[0]
                mid0 = hand0[9]
                p0x = int(((wrist0['x'] + mid0['x']) / 2) * w)
                p0y = int(((wrist0['y'] + mid0['y']) / 2) * h)
                
                wrist1 = hand1[0]
                mid1 = hand1[9]
                p1x = int(((wrist1['x'] + mid1['x']) / 2) * w)
                p1y = int(((wrist1['y'] + mid1['y']) / 2) * h)
                
                # Check if both in top third (row 0)
                row_h = h // 3
                if p0y < row_h and p1y < row_h:
                    cx = (p0x + p1x) // 2
                    cy = (p0y + p1y) // 2
                    
                    dist = np.sqrt((p0x - p1x)**2 + (p0y - p1y)**2)
                    vfx_scale = max(0.7, dist / (goku_png.shape[1] + 1))
                    
                    # Animate rotation
                    rotation_state['goku'] = (rotation_state['goku'] + 8) % 360
                    rotated = vfx.get_prerotated(goku_rotations, rotation_state['goku'])
                    
                    active_vfx = rotated
                    vfx_center = (cx, cy)
                    effect_name = "Goku Spirit Bomb"
        
        # Apply VFX overlay
        if active_vfx is not None:
            frame = vfx.overlay_png(frame, active_vfx, vfx_center, scale=vfx_scale)
        
        # Encode back to base64
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        frame_b64 = base64.b64encode(buffer).decode('utf-8')
        
        # Send back processed frame
        emit('processed_frame', {
            'frame': f'data:image/jpeg;base64,{frame_b64}',
            'effect': effect_name
        })
        
    except Exception as e:
        print(f"Error processing frame: {e}")
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
