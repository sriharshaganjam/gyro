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
      background: rgba(0,0,0,0.7); color: white;
      padding: 8px 18px; border-radius: 20px;
      font-size: 13px; font-family: sans-serif;
      z-index: 100; pointer-events: none; white-space: nowrap;
    }}
    #gyro-btn {{
      position: fixed; bottom: 40px; left: 50%;
      transform: translateX(-50%);
      background: rgba(255,255,255,0.15); color: white;
      border: 2px solid rgba(255,255,255,0.6);
      padding: 14px 32px; border-radius: 30px;
      font-size: 16px; font-family: sans-serif;
      cursor: pointer; z-index: 100;
      backdrop-filter: blur(8px); display: none;
    }}
  </style>
</head>
<body>
<div id="pano-container"><canvas id="canvas"></canvas></div>
<div id="debug">Loading...</div>
<button id="gyro-btn" onclick="enableGyro()">📱 Enable Gyroscope</button>

<script>
const debug   = document.getElementById('debug');
const gyroBtn = document.getElementById('gyro-btn');
const log = msg => {{ debug.textContent = msg; console.log(msg); }};

// Load Three.js
const s = document.createElement('script');
s.src = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js";
s.onload = init;
s.onerror = () => {{
  const s2 = document.createElement('script');
  s2.src = "https://cdn.jsdelivr.net/npm/three@0.128/build/three.min.js";
  s2.onload = init; s2.onerror = () => log("Three.js failed");
  document.head.appendChild(s2);
}};
document.head.appendChild(s);

function init() {{
  log("Loading image...");
  const container = document.getElementById('pano-container');
  const canvas    = document.getElementById('canvas');

  const renderer = new THREE.WebGLRenderer({{ canvas, antialias: true }});
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(window.innerWidth, window.innerHeight);

  const scene  = new THREE.Scene();
  // 180 deg horizontal FOV — widest natural view
  const FOV_H  = 180;
  function vFov() {{
    const aspect = window.innerWidth / window.innerHeight;
    return (2 * Math.atan(Math.tan(FOV_H * Math.PI / 360) / aspect) * 180 / Math.PI);
  }}
  const camera = new THREE.PerspectiveCamera(vFov(), window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.set(0, 0, 0.01);

  window.addEventListener('resize', () => {{
    renderer.setSize(window.innerWidth, window.innerHeight);
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.fov = vFov(); baseFov = vFov();
    camera.updateProjectionMatrix();
  }});

  const geo = new THREE.SphereGeometry(500, 60, 40);
  geo.scale(-1, 1, 1);

  const img = new Image();
  img.onload = () => {{
    const tex = new THREE.Texture(img);
    tex.needsUpdate = true;
    scene.add(new THREE.Mesh(geo, new THREE.MeshBasicMaterial({{ map: tex }})));
    log("✓ Drag to look around");
    setTimeout(() => debug.style.display = 'none', 3000);
    setupControls();
    animate();
  }};
  img.onerror = () => log("ERROR decoding image");
  img.src = "{image_data_url}";

  // ── state ───────────────────────────────────────────
  let lon = 0, lat = 0;          // start dead centre
  let baseFov = vFov();
  let isDragging = false, prevMouse = {{x:0,y:0}};
  let prevTouch = null, prevPinchDist = null;
  let gyroOn = false, aOff = null, bOff = null;

  // ── mouse ────────────────────────────────────────────
  canvas.addEventListener('mousedown', e => {{ isDragging=true; prevMouse={{x:e.clientX,y:e.clientY}}; }});
  window.addEventListener('mouseup',   () => isDragging=false);
  window.addEventListener('mousemove', e => {{
    if (!isDragging) return;
    lon -= (e.clientX - prevMouse.x) * 0.15;
    lat += (e.clientY - prevMouse.y) * 0.15;
    lat  = Math.max(-85, Math.min(85, lat));
    prevMouse = {{x:e.clientX, y:e.clientY}};
  }});
  canvas.addEventListener('wheel', e => {{
    e.preventDefault();
    baseFov = Math.max(30, Math.min(180, baseFov + e.deltaY * 0.05));
    camera.fov = baseFov; camera.updateProjectionMatrix();
  }}, {{passive:false}});

  // ── touch ────────────────────────────────────────────
  canvas.addEventListener('touchstart', e => {{
    e.preventDefault();
    if (e.touches.length === 1) {{
      prevTouch = {{x:e.touches[0].clientX, y:e.touches[0].clientY}};
      prevPinchDist = null;
    }} else if (e.touches.length === 2) {{
      prevTouch = null;
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      prevPinchDist = Math.sqrt(dx*dx+dy*dy);
    }}
  }}, {{passive:false}});
  canvas.addEventListener('touchend', e => {{
    e.preventDefault();
    if (e.touches.length < 2) prevPinchDist = null;
    if (e.touches.length === 0) prevTouch = null;
  }}, {{passive:false}});
  canvas.addEventListener('touchmove', e => {{
    e.preventDefault();
    if (e.touches.length === 1 && prevTouch) {{
      lon -= (e.touches[0].clientX - prevTouch.x) * 0.2;
      lat += (e.touches[0].clientY - prevTouch.y) * 0.2;
      lat  = Math.max(-85, Math.min(85, lat));
      prevTouch = {{x:e.touches[0].clientX, y:e.touches[0].clientY}};
    }} else if (e.touches.length === 2 && prevPinchDist !== null) {{
      const dx   = e.touches[0].clientX - e.touches[1].clientX;
      const dy   = e.touches[0].clientY - e.touches[1].clientY;
      const dist = Math.sqrt(dx*dx+dy*dy);
      baseFov = Math.max(30, Math.min(180, baseFov + (prevPinchDist - dist) * 0.15));
      camera.fov = baseFov; camera.updateProjectionMatrix();
      prevPinchDist = dist;
    }}
  }}, {{passive:false}});

  // ── gyro: listen DIRECTLY — works on Android ─────────
  // On Android the iframe DOES receive deviceorientation
  // On iOS we still need the button for permission
  function onGyro(e) {{
    if (!gyroOn || e.alpha == null) return;
    if (aOff === null) {{ aOff = e.alpha; bOff = e.beta; }}
    const portrait = window.innerHeight > window.innerWidth;
    lon = -(e.alpha - aOff);
    // beta=90 means phone held upright portrait → looking straight ahead
    lat = portrait ? -(e.beta - 90) : -e.gamma;
    lat = Math.max(-85, Math.min(85, lat));
  }}

  function setupControls() {{
    const isIOS     = /iPhone|iPad|iPod/i.test(navigator.userAgent);
    const isAndroid = /Android/i.test(navigator.userAgent);

    if (isAndroid) {{
      // Android iframes receive deviceorientation directly
      window.addEventListener('deviceorientation', onGyro, true);
      gyroOn = true;
      log("📱 Gyroscope active — drag to pan");
      setTimeout(() => debug.style.display = 'none', 3000);
    }} else if (isIOS) {{
      gyroBtn.style.display = 'block';
    }}
  }}

  // iOS button tap
  window.enableGyro = function() {{
    gyroBtn.style.display = 'none';
    if (typeof DeviceOrientationEvent !== 'undefined' &&
        typeof DeviceOrientationEvent.requestPermission === 'function') {{
      DeviceOrientationEvent.requestPermission()
        .then(res => {{
          if (res === 'granted') {{
            window.addEventListener('deviceorientation', onGyro, true);
            gyroOn = true;
            log("📱 Gyroscope active");
            setTimeout(() => debug.style.display = 'none', 2000);
          }} else {{
            log("Permission denied — drag to pan");
          }}
        }})
        .catch(() => log("Gyro unavailable — drag to pan"));
    }} else {{
      // Older iOS — no permission API needed
      window.addEventListener('deviceorientation', onGyro, true);
      gyroOn = true;
      log("📱 Gyroscope active");
      setTimeout(() => debug.style.display = 'none', 2000);
    }}
  }};

  // ── render ───────────────────────────────────────────
  function animate() {{
    requestAnimationFrame(animate);
    const phi   = THREE.MathUtils.degToRad(90 - lat);
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
