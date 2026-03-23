import streamlit as st
import streamlit.components.v1 as components
import requests
import base64
from PIL import Image
import io

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

    <!-- Gyro bridge: parent page forwards deviceorientation into iframe -->
    <script>
    (function() {
        function sendToIframes(data) {
            document.querySelectorAll('iframe').forEach(function(f) {
                try { f.contentWindow.postMessage(data, '*'); } catch(e) {}
            });
        }

        function startGyro() {
            window.addEventListener('deviceorientation', function(e) {
                sendToIframes({ type: 'gyro', alpha: e.alpha, beta: e.beta, gamma: e.gamma });
            }, true);
        }

        // Listen for iframe requesting iOS permission
        window.addEventListener('message', function(e) {
            if (!e.data || e.data.type !== 'requestGyroPermission') return;
            if (typeof DeviceOrientationEvent !== 'undefined' &&
                typeof DeviceOrientationEvent.requestPermission === 'function') {
                DeviceOrientationEvent.requestPermission().then(function(s) {
                    if (s === 'granted') startGyro();
                    sendToIframes({ type: 'gyroPermissionResult', granted: s === 'granted' });
                }).catch(function(){});
            } else {
                startGyro();
                sendToIframes({ type: 'gyroPermissionResult', granted: true });
            }
        });

        // Android: start immediately
        if (/Android/i.test(navigator.userAgent)) {
            startGyro();
        }
    })();
    </script>
""", unsafe_allow_html=True)

FILE_ID = "18JMqRl4agEJwJo5YVIi2NTEDDr_-CIpg"

@st.cache_data(show_spinner="Downloading panorama...")
def load_image_as_base64(file_id):
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    r = session.get(url, headers=headers)

    confirm = None
    for k, v in r.cookies.items():
        if k.startswith("download_warning"):
            confirm = v
            break
    if confirm is None:
        import re
        m = re.search(r'confirm=([0-9A-Za-z_\-]+)', r.text)
        if m:
            confirm = m.group(1)

    if confirm:
        url = f"https://drive.google.com/uc?export=download&confirm={confirm}&id={file_id}"

    r2 = session.get(url, headers=headers, stream=True)
    image_bytes = b"".join(r2.iter_content(chunk_size=1024 * 1024))

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = img.size

    MAX_W = 4096
    if w > MAX_W:
        new_h = int(h * MAX_W / w)
        img = img.resize((MAX_W, new_h), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

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
    }}
    canvas {{
      position: absolute; top: 0; left: 0;
      width: 100% !important; height: 100% !important;
    }}
    #status {{
      position: fixed; inset: 0;
      display: flex; align-items: center; justify-content: center;
      color: white; font-size: 15px; font-family: sans-serif;
      background: #000; z-index: 50; text-align: center; padding: 20px;
    }}

    /* Zoom slider — fixed position, high z-index, large touch target */
    #zoom-bar {{
      position: fixed;
      bottom: 30px;
      left: 50%;
      transform: translateX(-50%);
      display: none;
      flex-direction: row;
      align-items: center;
      gap: 12px;
      background: rgba(0,0,0,0.65);
      padding: 12px 24px;
      border-radius: 40px;
      z-index: 9999;
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
      touch-action: none;
      pointer-events: all;
    }}
    #zoom-bar .label {{
      color: white; font-size: 14px; font-family: sans-serif;
      user-select: none; min-width: 36px; text-align: center;
    }}
    /* Custom range slider with large thumb for touch */
    #zoom-track {{
      position: relative;
      width: 200px; height: 36px;
      display: flex; align-items: center;
      touch-action: none;
      cursor: pointer;
    }}
    #zoom-fill {{
      position: absolute;
      left: 0; top: 50%;
      transform: translateY(-50%);
      height: 4px; border-radius: 4px;
      background: white;
      pointer-events: none;
    }}
    #zoom-bg {{
      position: absolute;
      left: 0; top: 50%;
      transform: translateY(-50%);
      width: 100%; height: 4px; border-radius: 4px;
      background: rgba(255,255,255,0.3);
      pointer-events: none;
    }}
    #zoom-thumb {{
      position: absolute;
      top: 50%; transform: translateY(-50%);
      width: 28px; height: 28px; border-radius: 50%;
      background: white;
      box-shadow: 0 2px 6px rgba(0,0,0,0.4);
      pointer-events: none;
    }}

    #gyro-btn {{
      position: fixed; bottom: 100px; left: 50%;
      transform: translateX(-50%);
      background: rgba(255,255,255,0.15); color: white;
      border: 2px solid rgba(255,255,255,0.7);
      padding: 14px 32px; border-radius: 30px;
      font-size: 16px; font-family: sans-serif;
      cursor: pointer; z-index: 9999; display: none;
      touch-action: manipulation;
    }}
  </style>
</head>
<body>

<div id="pano-container"><canvas id="canvas"></canvas></div>
<div id="status">Loading...</div>

<div id="zoom-bar">
  <span class="label">🔭</span>
  <div id="zoom-track">
    <div id="zoom-bg"></div>
    <div id="zoom-fill"></div>
    <div id="zoom-thumb"></div>
  </div>
  <span class="label" id="zoom-label">75°</span>
</div>

<button id="gyro-btn" onclick="enableGyro()">📱 Enable Gyroscope</button>

<script>
const statusEl = document.getElementById('status');
const zoomBar  = document.getElementById('zoom-bar');
const zoomTrack= document.getElementById('zoom-track');
const zoomFill = document.getElementById('zoom-fill');
const zoomThumb= document.getElementById('zoom-thumb');
const zoomLabel= document.getElementById('zoom-label');
const gyroBtn  = document.getElementById('gyro-btn');
const log = msg => {{ statusEl.textContent = msg; console.log(msg); }};

function loadScript(url, ok, fail) {{
  const s = document.createElement('script');
  s.src = url; s.onload = ok; s.onerror = fail;
  document.head.appendChild(s);
}}

log("Loading Three.js...");
loadScript(
  "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js",
  () => {{ log("Initialising..."); initViewer(); }},
  () => loadScript(
    "https://cdn.jsdelivr.net/npm/three@0.128/build/three.min.js",
    () => {{ log("Initialising..."); initViewer(); }},
    () => log("❌ Three.js failed to load")
  )
);

function initViewer() {{
  const canvas = document.getElementById('canvas');

  const renderer = new THREE.WebGLRenderer({{ canvas, antialias: true }});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);

  const scene = new THREE.Scene();
  const FOV_MIN = 30, FOV_MAX = 110, FOV_START = 60;
  let fov = FOV_START;

  const camera = new THREE.PerspectiveCamera(fov, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.set(0, 0, 0.01);

  window.addEventListener('resize', () => {{
    renderer.setSize(window.innerWidth, window.innerHeight);
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
  }});

  const geo = new THREE.SphereGeometry(500, 80, 60);
  geo.scale(-1, 1, 1);

  log("Decoding image...");
  new THREE.TextureLoader().load(
    "{image_data_url}",
    (tex) => {{
      tex.minFilter = THREE.LinearFilter;
      tex.generateMipmaps = false;
      scene.add(new THREE.Mesh(geo, new THREE.MeshBasicMaterial({{ map: tex }})));
      statusEl.style.display = 'none';
      zoomBar.style.display  = 'flex';
      applyFov(FOV_START);
      setupControls();
      animate();
    }},
    undefined,
    () => log("❌ Image decode failed")
  );

  // ── State ────────────────────────────────────────────
  let lon = 0, lat = 0;
  let drag = false, pm = {{x:0,y:0}};
  let pt = null, pd = null;
  let gyroOn = false, aOff = null;

  // ── Custom zoom slider (canvas-level touch) ───────────
  function applyFov(v) {{
    fov = Math.max(FOV_MIN, Math.min(FOV_MAX, v));
    camera.fov = fov;
    camera.updateProjectionMatrix();
    zoomLabel.textContent = Math.round(fov) + '°';
    const pct = (fov - FOV_MIN) / (FOV_MAX - FOV_MIN);
    const trackW = zoomTrack.offsetWidth;
    const thumbW = 28;
    const x = pct * (trackW - thumbW);
    zoomThumb.style.left = x + 'px';
    zoomFill.style.width = (x + thumbW/2) + 'px';
  }}

  function fovFromTrackX(clientX) {{
    const rect = zoomTrack.getBoundingClientRect();
    const pct  = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    return FOV_MIN + pct * (FOV_MAX - FOV_MIN);
  }}

  let sliderDrag = false;
  zoomTrack.addEventListener('mousedown',  e => {{ sliderDrag=true; applyFov(fovFromTrackX(e.clientX)); e.stopPropagation(); }});
  window.addEventListener('mouseup',       () => sliderDrag=false);
  window.addEventListener('mousemove',     e => {{ if(sliderDrag) applyFov(fovFromTrackX(e.clientX)); }});
  zoomTrack.addEventListener('touchstart', e => {{ sliderDrag=true; applyFov(fovFromTrackX(e.touches[0].clientX)); e.stopPropagation(); }}, {{passive:true}});
  window.addEventListener('touchend',      () => sliderDrag=false);
  window.addEventListener('touchmove',     e => {{
    if (sliderDrag) applyFov(fovFromTrackX(e.touches[0].clientX));
  }}, {{passive:true}});

  // ── Mouse drag to pan ─────────────────────────────────
  canvas.addEventListener('mousedown', e => {{ drag=true; pm={{x:e.clientX,y:e.clientY}}; }});
  window.addEventListener('mouseup',   () => drag=false);
  window.addEventListener('mousemove', e => {{
    if (!drag || sliderDrag) return;
    lon -= (e.clientX-pm.x)*0.2;
    lat += (e.clientY-pm.y)*0.2;
    lat = Math.max(-85,Math.min(85,lat));
    pm = {{x:e.clientX,y:e.clientY}};
  }});
  canvas.addEventListener('wheel', e => {{
    e.preventDefault();
    applyFov(fov + e.deltaY*0.05);
  }}, {{passive:false}});

  // ── Touch: single finger pan, two finger pinch zoom ───
  canvas.addEventListener('touchstart', e => {{
    if (sliderDrag) return;
    e.preventDefault();
    if (e.touches.length===1) {{
      pt={{x:e.touches[0].clientX,y:e.touches[0].clientY}}; pd=null;
    }} else if (e.touches.length===2) {{
      pt=null;
      const dx=e.touches[0].clientX-e.touches[1].clientX;
      const dy=e.touches[0].clientY-e.touches[1].clientY;
      pd=Math.sqrt(dx*dx+dy*dy);
    }}
  }},{{passive:false}});

  canvas.addEventListener('touchend', e => {{
    e.preventDefault();
    if(e.touches.length<2) pd=null;
    if(e.touches.length===0) pt=null;
  }},{{passive:false}});

  canvas.addEventListener('touchmove', e => {{
    if (sliderDrag) return;
    e.preventDefault();
    if (e.touches.length===1 && pt) {{
      lon -= (e.touches[0].clientX-pt.x)*0.2;
      lat += (e.touches[0].clientY-pt.y)*0.2;
      lat = Math.max(-85,Math.min(85,lat));
      pt = {{x:e.touches[0].clientX,y:e.touches[0].clientY}};
    }} else if (e.touches.length===2 && pd!==null) {{
      const dx=e.touches[0].clientX-e.touches[1].clientX;
      const dy=e.touches[0].clientY-e.touches[1].clientY;
      const d=Math.sqrt(dx*dx+dy*dy);
      applyFov(fov+(pd-d)*0.15);
      pd=d;
    }}
  }},{{passive:false}});

  // ── Gyro via postMessage from parent bridge ───────────
  window.addEventListener('message', e => {{
    if (!e.data) return;
    if (e.data.type === 'gyroPermissionResult') {{
      if (e.data.granted) gyroOn = true;
    }}
    if (e.data.type === 'gyro') {{
      if (!gyroOn || e.data.alpha==null) return;
      if (aOff===null) aOff = e.data.alpha;
      const portrait = window.innerHeight > window.innerWidth;
      lon = -(e.data.alpha - aOff);
      lat = portrait ? -(e.data.beta - 90) : -e.data.gamma;
      lat = Math.max(-85,Math.min(85,lat));
    }}
  }});

  function setupControls() {{
    const isIOS     = /iPhone|iPad|iPod/i.test(navigator.userAgent);
    const isAndroid = /Android/i.test(navigator.userAgent);
    if (isAndroid) {{
      // Parent bridge already started for Android
      gyroOn = true;
    }} else if (isIOS) {{
      gyroBtn.style.display = 'block';
    }}
  }}

  window.enableGyro = function() {{
    gyroBtn.style.display = 'none';
    // Ask parent to request permission and start bridge
    window.parent.postMessage({{ type: 'requestGyroPermission' }}, '*');
  }};

  function animate() {{
    requestAnimationFrame(animate);
    const phi   = THREE.MathUtils.degToRad(90-lat);
    const theta = THREE.MathUtils.degToRad(lon);
    camera.lookAt(
      Math.sin(phi)*Math.cos(theta),
      Math.cos(phi),
      Math.sin(phi)*Math.sin(theta)
    );
    renderer.render(scene, camera);
  }}
}}
</script>
</body>
</html>
"""

components.html(html_code, height=10000, scrolling=False)
