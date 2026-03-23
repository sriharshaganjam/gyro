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
    <!-- Gyro bridge: listen in parent page, forward to iframe via postMessage -->
    <script>
    (function() {
        function forwardGyro(e) {
            var iframes = document.querySelectorAll('iframe');
            iframes.forEach(function(iframe) {
                try {
                    iframe.contentWindow.postMessage({
                        type: 'deviceorientation',
                        alpha: e.alpha,
                        beta: e.beta,
                        gamma: e.gamma
                    }, '*');
                } catch(err) {}
            });
        }

        function startBridge() {
            window.addEventListener('deviceorientation', forwardGyro, true);
        }

        // iOS 13+ needs permission
        if (typeof DeviceOrientationEvent !== 'undefined' &&
            typeof DeviceOrientationEvent.requestPermission === 'function') {
            // Expose for button tap
            window._requestGyroBridge = function() {
                DeviceOrientationEvent.requestPermission()
                    .then(function(state) {
                        if (state === 'granted') startBridge();
                    }).catch(function(){});
            };
        } else {
            // Android / older iOS — start immediately
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
      cursor: grab; overflow: hidden;
    }}
    #pano-container:active {{ cursor: grabbing; }}
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
const debug = document.getElementById('debug');
const gyroBtn = document.getElementById('gyro-btn');
const log = msg => {{ debug.textContent = msg; }};

// Load Three.js
const script = document.createElement('script');
script.src = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js";
script.onload = initPanorama;
script.onerror = () => {{
  const s2 = document.createElement('script');
  s2.src = "https://cdn.jsdelivr.net/npm/three@0.128/build/three.min.js";
  s2.onload = initPanorama;
  s2.onerror = () => log("ERROR: Could not load Three.js.");
  document.head.appendChild(s2);
}};
document.head.appendChild(script);

function initPanorama() {{
  log("Loading panorama...");

  const container = document.getElementById('pano-container');
  const canvas    = document.getElementById('canvas');

  const renderer = new THREE.WebGLRenderer({{ canvas, antialias: true }});
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(window.innerWidth, window.innerHeight);

  const scene  = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(120, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.set(0, 0, 0.01);

  window.addEventListener('resize', () => {{
    renderer.setSize(window.innerWidth, window.innerHeight);
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
  }});

  const geometry = new THREE.SphereGeometry(500, 60, 40);
  geometry.scale(-1, 1, 1);

  const image = new Image();
  image.onload = () => {{
    log("✓ Drag to look around");
    setTimeout(() => {{ debug.style.display = 'none'; }}, 3000);
    const texture = new THREE.Texture(image);
    texture.needsUpdate = true;
    const material = new THREE.MeshBasicMaterial({{ map: texture }});
    scene.add(new THREE.Mesh(geometry, material));
    setupControls();
    animate();
  }};
  image.onerror = () => log("ERROR: Could not decode image.");
  image.src = "{image_data_url}";

  // ── State ──────────────────────────────────────────────
  let lon = 0, lat = 0;
  let isDragging = false, prevMouse = {{ x: 0, y: 0 }};
  let prevTouch  = null;
  let alphaOffset = null;

  // ── Mouse ──────────────────────────────────────────────
  container.addEventListener('mousedown', e => {{ isDragging = true; prevMouse = {{ x: e.clientX, y: e.clientY }}; }});
  window.addEventListener('mouseup',   () => isDragging = false);
  window.addEventListener('mousemove', e => {{
    if (!isDragging) return;
    lon -= (e.clientX - prevMouse.x) * 0.2;
    lat += (e.clientY - prevMouse.y) * 0.2;
    lat  = Math.max(-85, Math.min(85, lat));
    prevMouse = {{ x: e.clientX, y: e.clientY }};
  }});

  // ── Touch ──────────────────────────────────────────────
  container.addEventListener('touchstart', e => {{
    e.preventDefault();
    if (e.touches.length === 1) prevTouch = {{ x: e.touches[0].clientX, y: e.touches[0].clientY }};
  }}, {{ passive: false }});
  container.addEventListener('touchend',   () => prevTouch = null);
  container.addEventListener('touchmove',  e => {{
    e.preventDefault();
    if (!prevTouch || e.touches.length !== 1) return;
    lon -= (e.touches[0].clientX - prevTouch.x) * 0.2;
    lat += (e.touches[0].clientY - prevTouch.y) * 0.2;
    lat  = Math.max(-85, Math.min(85, lat));
    prevTouch = {{ x: e.touches[0].clientX, y: e.touches[0].clientY }};
  }}, {{ passive: false }});

  // ── Scroll zoom ────────────────────────────────────────
  container.addEventListener('wheel', e => {{
    camera.fov = Math.max(30, Math.min(130, camera.fov + e.deltaY * 0.05));
    camera.updateProjectionMatrix();
  }});

  // ── Gyro via postMessage from parent ──────────────────
  window.addEventListener('message', e => {{
    if (!e.data || e.data.type !== 'deviceorientation') return;
    const {{ alpha, beta, gamma }} = e.data;
    if (alpha == null) return;

    if (alphaOffset === null) alphaOffset = alpha;
    const a = alpha - alphaOffset;
    const portrait = window.innerHeight > window.innerWidth;

    lon = -a;
    lat = portrait ? (beta - 90) : gamma;
    lat = Math.max(-85, Math.min(85, lat));
  }});

  // ── Controls setup ─────────────────────────────────────
  function setupControls() {{
    const isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);
    if (isIOS) {{
      gyroBtn.style.display = 'block';
    }}
    // Android gyro starts from parent bridge immediately (no permission needed)
  }}

  // Called when iOS button is tapped — asks parent page for permission
  window.enableGyro = function() {{
    gyroBtn.style.display = 'none';
    log("📱 Gyroscope active");
    setTimeout(() => {{ debug.style.display = 'none'; }}, 2000);
    // Tell parent to request permission and start bridge
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

# Listen for requestGyro message from iframe and trigger parent bridge
st.markdown("""
<script>
window.addEventListener('message', function(e) {
    if (e.data && e.data.type === 'requestGyro') {
        if (window._requestGyroBridge) {
            window._requestGyroBridge();
        }
    }
});
</script>
""", unsafe_allow_html=True)

components.html(html_code, height=10000, scrolling=False)
