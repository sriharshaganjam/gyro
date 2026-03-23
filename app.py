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
""", unsafe_allow_html=True)

FILE_ID = "18JMqRl4agEJwJo5YVIi2NTEDDr_-CIpg"

@st.cache_data(show_spinner="Downloading panorama...")
def load_image_as_base64(file_id):
    session = requests.Session()

    # Use the export=download with a user-agent to avoid compressed preview
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    # First request to get confirmation token for large files
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    r = session.get(url, headers=headers, stream=True)

    # Handle Google's virus-scan warning for large files
    confirm_token = None
    for k, v in r.cookies.items():
        if k.startswith("download_warning"):
            confirm_token = v
            break

    # Also check response content for newer-style confirm token
    if confirm_token is None:
        import re
        content_start = b"".join(r.iter_content(8192) for _ in range(10))
        match = re.search(b'confirm=([0-9A-Za-z_-]+)', content_start)
        if match:
            confirm_token = match.group(1).decode()

    if confirm_token:
        url = f"https://drive.google.com/uc?export=download&confirm={confirm_token}&id={file_id}"
        r = session.get(url, headers=headers, stream=True)

    image_bytes = b"".join(r.iter_content(chunk_size=1024 * 1024))

    # Open with PIL to check and resize
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = img.size
    st.write(f"Downloaded image: {w}×{h}px ({len(image_bytes)/1024/1024:.1f}MB)")

    # Resize to max 4096px wide — sweet spot for mobile GPU texture limits
    # while keeping full equirectangular 2:1 ratio
    MAX_W = 4096
    if w > MAX_W:
        new_h = int(h * MAX_W / w)
        img = img.resize((MAX_W, new_h), Image.LANCZOS)
        st.write(f"Resized to: {MAX_W}×{new_h}px for optimal mobile performance")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
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
    #zoom-bar {{
      position: fixed; bottom: 24px; left: 50%;
      transform: translateX(-50%);
      display: none;
      align-items: center; gap: 10px;
      background: rgba(0,0,0,0.55);
      padding: 10px 20px; border-radius: 30px;
      z-index: 100; backdrop-filter: blur(8px);
    }}
    #zoom-bar span {{
      color: white; font-size: 13px; font-family: sans-serif;
      user-select: none; white-space: nowrap;
    }}
    #zoom-slider {{
      -webkit-appearance: none;
      width: 180px; height: 4px;
      border-radius: 4px; outline: none;
      background: rgba(255,255,255,0.3);
      cursor: pointer;
    }}
    #zoom-slider::-webkit-slider-thumb {{
      -webkit-appearance: none;
      width: 22px; height: 22px;
      border-radius: 50%; background: white;
      cursor: pointer; box-shadow: 0 0 4px rgba(0,0,0,0.4);
    }}
    #gyro-btn {{
      position: fixed; bottom: 90px; left: 50%;
      transform: translateX(-50%);
      background: rgba(255,255,255,0.15); color: white;
      border: 2px solid rgba(255,255,255,0.6);
      padding: 12px 28px; border-radius: 30px;
      font-size: 15px; font-family: sans-serif;
      cursor: pointer; z-index: 100; display: none;
    }}
  </style>
</head>
<body>

<div id="pano-container"><canvas id="canvas"></canvas></div>
<div id="status">Loading...</div>
<div id="zoom-bar">
  <span>🔭</span>
  <input id="zoom-slider" type="range" min="30" max="110" value="75" step="1">
  <span id="zoom-label">75°</span>
</div>
<button id="gyro-btn" onclick="enableGyro()">📱 Enable Gyroscope</button>

<script>
const statusEl   = document.getElementById('status');
const zoomBar    = document.getElementById('zoom-bar');
const zoomSlider = document.getElementById('zoom-slider');
const zoomLabel  = document.getElementById('zoom-label');
const gyroBtn    = document.getElementById('gyro-btn');
const log = msg => {{ statusEl.textContent = msg; console.log(msg); }};

function loadScript(url, ok, fail) {{
  const s = document.createElement('script');
  s.src = url; s.onload = ok; s.onerror = fail;
  document.head.appendChild(s);
}}

log("Loading Three.js...");
loadScript(
  "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js",
  () => {{ log("Initialising viewer..."); initViewer(); }},
  () => loadScript(
    "https://cdn.jsdelivr.net/npm/three@0.128/build/three.min.js",
    () => {{ log("Initialising viewer..."); initViewer(); }},
    () => log("❌ Three.js failed to load — check internet")
  )
);

function initViewer() {{
  const canvas = document.getElementById('canvas');

  const renderer = new THREE.WebGLRenderer({{ canvas, antialias: true }});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);

  const scene  = new THREE.Scene();
  let   fov    = 75;
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

  // ── Zoom (slider + pinch + scroll) ───────────────────
  function applyFov(v) {{
    fov = Math.max(30, Math.min(110, v));
    camera.fov = fov;
    camera.updateProjectionMatrix();
    zoomSlider.value = fov;
    zoomLabel.textContent = Math.round(fov) + '°';
  }}
  zoomSlider.addEventListener('input', () => applyFov(+zoomSlider.value));
  applyFov(75);

  // ── Mouse ────────────────────────────────────────────
  canvas.addEventListener('mousedown', e => {{ drag=true; pm={{x:e.clientX,y:e.clientY}}; }});
  window.addEventListener('mouseup',   () => drag=false);
  window.addEventListener('mousemove', e => {{
    if (!drag) return;
    lon -= (e.clientX-pm.x)*0.2;
    lat += (e.clientY-pm.y)*0.2;
    lat = Math.max(-85,Math.min(85,lat));
    pm = {{x:e.clientX,y:e.clientY}};
  }});
  canvas.addEventListener('wheel', e => {{
    e.preventDefault();
    applyFov(fov + e.deltaY*0.05);
  }}, {{passive:false}});

  // ── Touch ────────────────────────────────────────────
  canvas.addEventListener('touchstart', e => {{
    e.preventDefault();
    if (e.touches.length===1) {{ pt={{x:e.touches[0].clientX,y:e.touches[0].clientY}}; pd=null; }}
    else if (e.touches.length===2) {{
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

  // ── Gyro ─────────────────────────────────────────────
  function onGyro(e) {{
    if (!gyroOn || e.alpha==null) return;
    if (aOff===null) aOff=e.alpha;
    const portrait = window.innerHeight > window.innerWidth;
    lon = -(e.alpha-aOff);
    lat = portrait ? -(e.beta-90) : -e.gamma;
    lat = Math.max(-85,Math.min(85,lat));
  }}

  function setupControls() {{
    const isIOS     = /iPhone|iPad|iPod/i.test(navigator.userAgent);
    const isAndroid = /Android/i.test(navigator.userAgent);
    if (isAndroid) {{
      window.addEventListener('deviceorientation', onGyro, true);
      gyroOn=true;
    }} else if (isIOS) {{
      gyroBtn.style.display='block';
    }}
  }}

  window.enableGyro = function() {{
    gyroBtn.style.display='none';
    if (typeof DeviceOrientationEvent.requestPermission==='function') {{
      DeviceOrientationEvent.requestPermission()
        .then(r => {{
          if (r==='granted') {{
            window.addEventListener('deviceorientation', onGyro, true);
            gyroOn=true;
          }}
        }}).catch(()=>{{}});
    }} else {{
      window.addEventListener('deviceorientation', onGyro, true);
      gyroOn=true;
    }}
  }};

  // ── Render loop ──────────────────────────────────────
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
