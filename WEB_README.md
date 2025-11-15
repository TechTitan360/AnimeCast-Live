# 🌐 AnimeCast Live - Web Edition Setup

## 📦 Installation

1. **Install new dependencies:**
```bash
pip install -r requirements.txt
```

2. **Run the web server:**
```bash
python web_app.py
```

3. **Access the app:**
   - **Desktop:** Open browser → `http://localhost:5000`
   - **Mobile/Tablet:** Open browser → `http://<YOUR_PC_IP>:5000/mobile`

---

## 🔍 Find Your PC IP Address

**Windows (PowerShell):**
```powershell
ipconfig
```
Look for "IPv4 Address" under your active network adapter (e.g., `192.168.1.100`)

**Mac/Linux:**
```bash
ifconfig | grep inet
```

---

## 📱 Mobile Access Steps

1. Make sure your phone/tablet is on the **same WiFi** as your PC
2. Run `python web_app.py` on your PC
3. Note the IP address shown in the terminal
4. On your mobile device, open browser and go to:
   ```
   http://192.168.1.X:5000/mobile
   ```
   (Replace X with your actual IP)
5. Allow camera permission when prompted
6. Press **Start** button
7. Perform gestures! 🔥

---

## ⚡ Features

### Desktop Version (`/`)
- Full HD display (1280×720)
- Real-time FPS counter
- Gesture effect labels
- Optimized for mouse/keyboard

### Mobile Version (`/mobile`)
- Fullscreen immersive mode
- Touch-optimized controls
- Camera flip button (front/back)
- Lower processing load for battery life
- Gesture guide overlay

---

## 🎮 Gestures

| Gesture | Effect |
|---------|--------|
| **Single hand, index finger up** | 💜 Freeza Beam |
| **Two hands in top third of screen** | 💙 Goku Spirit Bomb |

---

## 🔧 Performance Tips

### For Better Mobile Performance:
- Use **WiFi** not cellular data
- Close background apps
- Reduce distance to WiFi router
- Use **Back Camera** (usually higher quality)

### For Better Desktop Performance:
- Ensure good lighting
- Position hands clearly in frame
- Avoid cluttered backgrounds

---

## 🐛 Troubleshooting

**"Camera access denied"**
- Allow camera permission in browser settings
- Try HTTPS if needed (some browsers require it)

**"Cannot connect to server"**
- Check firewall settings (allow port 5000)
- Verify PC and phone on same network
- Try `http://0.0.0.0:5000` on PC first

**Low FPS**
- Close other applications
- Reduce browser zoom level
- Try mobile version (optimized)

---

## 🚀 Advanced Usage

### Run on Different Port:
```python
# In web_app.py, change last line:
socketio.run(app, host='0.0.0.0', port=8080, debug=True)
```

### Enable HTTPS (for iOS):
```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

# Run with SSL
socketio.run(app, host='0.0.0.0', port=5000, ssl_context=('cert.pem', 'key.pem'))
```

---

## 📊 Architecture

```
Phone Camera → MediaPipe Web (Browser) → WebSocket → Flask Server → VFX Engine → WebSocket → Browser Display
```

**Benefits:**
- Zero app installation
- Works on iOS + Android
- Cross-platform compatible
- Easy updates (just refresh browser)

---

## 🎯 Next Steps

Want to extend the web app?
- Add recording/download feature
- Implement more VFX effects
- Create gesture combos
- Add multiplayer mode
- Integrate social sharing

---

**Enjoy your web-powered VFX system! 🔥⚡**
