import streamlit as st
import streamlit.components.v1 as components
import requests
import base64

st.set_page_config(layout="wide", page_title="360 Viewer")

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
        [data-testid="stAppViewContainer"] { padding: 0 !important; }
        [data-testid="stVerticalBlock"] { gap: 0 !important; padding: 0 !important; }
    </style>

    <!-- Parent-level gyro bridge -->
    <script>
    (function() {
        var bridgeActive = false;

        function forwardGyro(e) {
            var iframes = document.querySelectorAll('iframe');
            iframes.forEach(function(f) {
                try {
                    f.contentWindow.postMessage({
                        type: 'deviceorientation',
                        alpha: e.alpha, beta: e.beta, gamma: e.gamma
                    }, '*');
                } catch(err) {}
            });
        }

        function startBridge() {
            if (bridgeActive) return;
            bridgeActive = true;
            window.addEventListener('deviceorientation', forwardGyro, true);
        }

        // Listen for iframe requesting gyro permission (iOS)
        window.addEventListener('message', function(e) {
            if (!e.data || e.data.type !== 'requestGyro') return;
            if (typeof DeviceOrientationEvent !== 'undefined' &&
                typeof DeviceOrientationEvent.requestPermission === 'function') {
                DeviceOrientationEvent.requestPermission()
                    .then(function(s) {
                        if (s === 'granted') startBridge();
                        // Tell iframe result
                        var iframes = document.querySelectorAll('iframe');
                        iframes.forEach(function(f) {
                            try { f.contentWindow.postMessage({ type: 'gyroPermission', granted: s === 'granted' }, '*'); } catch(err) {}
                        });
                    }).catch(function(){});
            } else {
                startBridge();
            }
        });

        // Android: start immediately (no permission needed)
        if (/Android/i.test(navigator.userAgent)) {
            startBridge();
        }
    })();
    </script>
""", unsafe_allow_html=True)

FILE_ID = "18JMqRl4agEJwJo5YVIi2NTEDDr_-CIpg"

@st.cache_data(show_spinner="Downloading panorama...")
def load_image_as_base64(file_id):
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    session = requests.Session()
    response = session.get(url, stream=True)
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            url = f"https://drive.google.com/uc?export=download&confirm={value}&id={file_id}"
            response = session.get(url, stream=True)
            break
    image_bytes = b"".join(response.iter_content(chunk_size=1024 * 1024))
    return base64.b64encode(image_bytes).decode("utf-8")

b64 = load_image_as_base64(FILE_ID)
image_data_url = f"data:image/jpeg;base64,{b64}"

html_code = f"""
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    html, body {{ width: 100%; height: 100%; background: #000; overflow: hidden; }}
    #pano-container {{
      width: 100vw; height: 100vh;
      position: fixed; top: 0; left: 0;
      overflow: hidden;
    }}
    canvas {{ width: 100% !important; height: 100% !important; display: block; }}
    #debug {{
      position: fixed; top: 16px; left: 50%;
      transform: translateX(-50%);
      background: rgba(0,0,0,0.6); color: white;
      padding: 8px 16px; border-radius: 20px;
      font-size: 14px; font-family: sans-serif;
      z-index: 100; pointer-events: none; white-space: nowrap;
    }}
    #gyro-btn {{
      position: fixed; bottom: 30px; left: 50%;
      transform: translateX(-50%);
      background: rgba(255,255,255,0.2); color: white;
      border: 2px solid rgba(255,255,255,0.6);
      padding: 14px 32px; border-radius: 30px;
      font-size: 16px; font-family: sans-serif;
      cursor: pointer; z-index: 100;
      backdrop-filter: blur(6px); display: none;
    }}
  </style>
</head>
<body>

<div id="pano-container">
  <canvas id="canvas"></canvas>
</div>
<div id="debug">Loading...</div>
<button id="gyro-btn" onclick="enableGyro()">📱 Enable Gyroscope</button>

<script>
const debug   = document.getElementById('debug');
const gyroBtn = document.getElementById('gyro-btn');
const log = msg => {{ debug.textContent = msg; }};

const script = document.createElement('script');
script.src = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js";
script.onload = initPanorama;
script.onerror = () => {{
  const s2 = document.createElement('script');
  s2.src = "https://cdn.jsdelivr.net/npm/three@0.128/build/three.min.js";
  s2.onload = initPanorama;
  s2.onerror = () => log("ERROR: Three.js failed to load");
  document.head.appendChild(s2);
}};
document.head.appendChild(script);

function initPanorama() {{
  log("Loading panorama...");

  const container = document.getElementById('pano-container');
  const canvas    = document.getElementById('canvas');

  const renderer = new THREE.WebGLRenderer({{ canvas, antialias: true }});
  renderer.setPixelRatio(1); // Fix: force 1:1 so FOV is consistent across devices
  renderer.setSize(window.innerWidth, window.innerHeight);

  const scene  = new THREE.Scene();

  // Fix: use a consistent diagonal-based FOV so it looks the same on all screen sizes
  function calcFov() {{
    const aspect = window.innerWidth / window.innerHeight;
    // Base horizontal FOV of 110deg, convert to vertical for Three.js
    const hFov = 110;
    return 2 * Math.atan(Math.tan((hFov * Math.PI / 180) / 2) / aspect) * 180 / Math.PI;
  }}

  const camera = new THREE.PerspectiveCamera(calcFov(), window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.set(0, 0, 0.01);

  window.addEventListener('resize', () => {{
    renderer.setSize(window.innerWidth, window.innerHeight);
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.fov    = calcFov();
    camera.updateProjectionMatrix();
  }});

  const geometry = new THREE.SphereGeometry(500, 60, 40);
  geometry.scale(-1, 1, 1);

  const img = new Image();
  img.onload = () => {{
    log("✓ Drag or tilt to explore");
    setTimeout(() => {{ debug.style.display = 'none'; }}, 3000);
    const texture = new THREE.Texture(img);
    texture.needsUpdate = true;
    scene.add(new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({{ map: texture }})));
    setupControls();
    animate();
  }};
  img.onerror = () => log("ERROR: Could not decode image");
  img.src = "{image_data_url}";

  // ── State ──────────────────────────────────────────────
  let lon = 0, lat = 0;
  let isDragging = false, prevMouse = {{ x:0, y:0 }};
  let prevTouch = null, prevPinchDist = null;
  let alphaOffset = null, gyroActive = false;
  let baseFov = calcFov();

  // ── Mouse drag ─────────────────────────────────────────
  canvas.addEventListener('mousedown', e => {{ isDragging = true; prevMouse = {{ x: e.clientX, y: e.clientY }}; }});
  window.addEventListener('mouseup',   () => isDragging = false);
  window.addEventListener('mousemove', e => {{
    if (!isDragging) return;
    lon -= (e.clientX - prevMouse.x) * 0.2;
    lat += (e.clientY - prevMouse.y) * 0.2;
    lat  = Math.max(-85, Math.min(85, lat));
    prevMouse = {{ x: e.clientX, y: e.clientY }};
  }});

  // ── Mouse scroll zoom ──────────────────────────────────
  canvas.addEventListener('wheel', e => {{
    e.preventDefault();
    baseFov = Math.max(40, Math.min(120, baseFov + e.deltaY * 0.05));
    camera.fov = baseFov;
    camera.updateProjectionMatrix();
  }}, {{ passive: false }});

  // ── Touch: drag + pinch zoom ───────────────────────────
  canvas.addEventListener('touchstart', e => {{
    e.preventDefault();
    if (e.touches.length === 1) {{
      prevTouch = {{ x: e.touches[0].clientX, y: e.touches[0].clientY }};
      prevPinchDist = null;
    }} else if (e.touches.length === 2) {{
      prevTouch = null;
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      prevPinchDist = Math.sqrt(dx*dx + dy*dy);
    }}
  }}, {{ passive: false }});

  canvas.addEventListener('touchend', e => {{
    e.preventDefault();
    if (e.touches.length < 2) prevPinchDist = null;
    if (e.touches.length === 0) prevTouch = null;
  }}, {{ passive: false }});

  canvas.addEventListener('touchmove', e => {{
    e.preventDefault();
    if (e.touches.length === 1 && prevTouch) {{
      // Single finger drag — pan
      lon -= (e.touches[0].clientX - prevTouch.x) * 0.2;
      lat += (e.touches[0].clientY - prevTouch.y) * 0.2;
      lat  = Math.max(-85, Math.min(85, lat));
      prevTouch = {{ x: e.touches[0].clientX, y: e.touches[0].clientY }};
    }} else if (e.touches.length === 2 && prevPinchDist !== null) {{
      // Two finger pinch — zoom
      const dx   = e.touches[0].clientX - e.touches[1].clientX;
      const dy   = e.touches[0].clientY - e.touches[1].clientY;
      const dist = Math.sqrt(dx*dx + dy*dy);
      const delta = prevPinchDist - dist;
      baseFov = Math.max(40, Math.min(120, baseFov + delta * 0.1));
      camera.fov = baseFov;
      camera.updateProjectionMatrix();
      prevPinchDist = dist;
    }}
  }}, {{ passive: false }});

  // ── Gyro via postMessage from parent ──────────────────
  window.addEventListener('message', e => {{
    if (!e.data) return;
    if (e.data.type === 'gyroPermission') {{
      if (e.data.granted) {{
        gyroActive = true;
        log("📱 Gyroscope active");
        setTimeout(() => {{ debug.style.display = 'none'; }}, 2000);
      }} else {{
        log("Gyroscope permission denied");
      }}
    }}
    if (e.data.type === 'deviceorientation') {{
      if (!gyroActive) return;
      const {{ alpha, beta, gamma }} = e.data;
      if (alpha == null) return;
      if (alphaOffset === null) alphaOffset = alpha;
      const a = alpha - alphaOffset;
      const portrait = window.innerHeight > window.innerWidth;
      lon = -a;
      lat = portrait ? (beta - 90) : gamma;
      lat = Math.max(-85, Math.min(85, lat));
    }}
  }});

  // ── Controls setup ─────────────────────────────────────
  function setupControls() {{
    const isIOS     = /iPhone|iPad|iPod/i.test(navigator.userAgent);
    const isAndroid = /Android/i.test(navigator.userAgent);
    if (isIOS) {{
      gyroBtn.style.display = 'block';
    }} else if (isAndroid) {{
      // Android bridge starts in parent — just enable here
      gyroActive = true;
      log("📱 Gyroscope active");
      setTimeout(() => {{ debug.style.display = 'none'; }}, 2000);
    }}
  }}

  window.enableGyro = function() {{
    gyroBtn.style.display = 'none';
    log("Requesting gyroscope...");
    window.parent.postMessage({{ type: 'requestGyro' }}, '*');
  }};

  // ── Render loop ────────────────────────────────────────
  function animate() {{
    requestAnimationFrame(animate);
    const phi   = THREE.MathUtils.degToRad(90 - lat);
    const theta = THREE.MathUtils.degToRad(lon);
    camera.lookAt(
      Math.sin(phi) * Math.cos(theta),
      Math.cos(phi),
      Math.sin(phi) * Math.sin(theta)
    );
    renderer.render(scene, camera);
  }}
}}
</script>
</body>
</html>
"""

components.html(html_code, height=10000, scrolling=False)
