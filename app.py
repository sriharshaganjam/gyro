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
    html, body {{
      width: 100%; height: 100%;
      background: #000; overflow: hidden;
    }}
    #pano-container {{
      width: 100vw; height: 100vh;
      position: fixed; top: 0; left: 0;
    }}
    canvas {{
      position: absolute; top: 0; left: 0;
      width: 100% !important; height: 100% !important;
    }}
    #status {{
      position: fixed; top: 0; left: 0; right: 0; bottom: 0;
      display: flex; align-items: center; justify-content: center;
      color: white; font-size: 16px; font-family: sans-serif;
      background: #000; z-index: 50;
      text-align: center; padding: 20px;
    }}
    #gyro-btn {{
      position: fixed; bottom: 40px; left: 50%;
      transform: translateX(-50%);
      background: rgba(255,255,255,0.2); color: white;
      border: 2px solid rgba(255,255,255,0.6);
      padding: 14px 32px; border-radius: 30px;
      font-size: 16px; font-family: sans-serif;
      cursor: pointer; z-index: 100;
      display: none;
    }}
  </style>
</head>
<body>
<div id="pano-container"><canvas id="canvas"></canvas></div>
<div id="status">Loading Three.js...</div>
<button id="gyro-btn" onclick="enableGyro()">📱 Enable Gyroscope</button>

<script>
const status = document.getElementById('status');
const gyroBtn = document.getElementById('gyro-btn');
const log = msg => {{ status.textContent = msg; console.log(msg); }};

function loadScript(url, cb, errcb) {{
  const s = document.createElement('script');
  s.src = url;
  s.onload = cb;
  s.onerror = errcb;
  document.head.appendChild(s);
}}

log("Loading Three.js from cdnjs...");
loadScript(
  "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js",
  () => {{ log("Three.js loaded ✓. Decoding image..."); initViewer(); }},
  () => {{
    log("cdnjs failed, trying jsdelivr...");
    loadScript(
      "https://cdn.jsdelivr.net/npm/three@0.128/build/three.min.js",
      () => {{ log("Three.js loaded ✓. Decoding image..."); initViewer(); }},
      () => log("❌ Three.js failed to load from both CDNs. Check internet connection.")
    );
  }}
);

function initViewer() {{
  const canvas    = document.getElementById('canvas');
  const container = document.getElementById('pano-container');
  const W = window.innerWidth;
  const H = window.innerHeight;

  const renderer = new THREE.WebGLRenderer({{ canvas: canvas, antialias: true }});
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(W, H);

  const scene  = new THREE.Scene();
  const aspect = W / H;
  // Fixed 90deg vertical FOV — feels natural on all screen sizes
  const camera = new THREE.PerspectiveCamera(90, aspect, 0.1, 1000);
  camera.position.set(0, 0, 0.01);

  window.addEventListener('resize', () => {{
    const w = window.innerWidth, h = window.innerHeight;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }});

  const geo = new THREE.SphereGeometry(500, 60, 40);
  geo.scale(-1, 1, 1);

  log("Decoding panorama image...");
  const tex = new THREE.TextureLoader().load(
    "{image_data_url}",
    (t) => {{
      scene.add(new THREE.Mesh(geo, new THREE.MeshBasicMaterial({{ map: t }})));
      status.style.display = 'none';
      setupControls();
      animate();
    }},
    undefined,
    () => log("❌ Failed to decode image texture.")
  );

  // ── state ──────────────────────────────────────────
  let lon = 0, lat = 0, baseFov = 90;
  let drag = false, pm = {{x:0,y:0}};
  let pt = null, pd = null;
  let gyroOn = false, aOff = null;

  // ── mouse ──────────────────────────────────────────
  canvas.addEventListener('mousedown', e => {{ drag=true; pm={{x:e.clientX,y:e.clientY}}; }});
  window.addEventListener('mouseup',   () => drag=false);
  window.addEventListener('mousemove', e => {{
    if (!drag) return;
    lon -= (e.clientX-pm.x)*0.2; lat += (e.clientY-pm.y)*0.2;
    lat = Math.max(-85,Math.min(85,lat)); pm={{x:e.clientX,y:e.clientY}};
  }});
  canvas.addEventListener('wheel', e => {{
    e.preventDefault();
    baseFov = Math.max(40,Math.min(120,baseFov+e.deltaY*0.05));
    camera.fov=baseFov; camera.updateProjectionMatrix();
  }}, {{passive:false}});

  // ── touch ──────────────────────────────────────────
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
  canvas.addEventListener('touchend',  e => {{ e.preventDefault(); if(e.touches.length<2)pd=null; if(e.touches.length===0)pt=null; }},{{passive:false}});
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
      baseFov=Math.max(40,Math.min(120,baseFov+(pd-d)*0.15));
      camera.fov=baseFov; camera.updateProjectionMatrix(); pd=d;
    }}
  }},{{passive:false}});

  // ── gyro ───────────────────────────────────────────
  function onGyro(e) {{
    if (!gyroOn || e.alpha==null) return;
    if (aOff===null) aOff = e.alpha;
    const portrait = window.innerHeight > window.innerWidth;
    lon = -(e.alpha - aOff);
    lat = portrait ? -(e.beta - 90) : -e.gamma;
    lat = Math.max(-85,Math.min(85,lat));
  }}

  function setupControls() {{
    const isIOS     = /iPhone|iPad|iPod/i.test(navigator.userAgent);
    const isAndroid = /Android/i.test(navigator.userAgent);
    if (isAndroid) {{
      window.addEventListener('deviceorientation', onGyro, true);
      gyroOn = true;
    }} else if (isIOS) {{
      gyroBtn.style.display = 'block';
    }}
  }}

  window.enableGyro = function() {{
    gyroBtn.style.display = 'none';
    if (typeof DeviceOrientationEvent.requestPermission === 'function') {{
      DeviceOrientationEvent.requestPermission().then(r => {{
        if (r==='granted') {{ window.addEventListener('deviceorientation', onGyro, true); gyroOn=true; }}
      }}).catch(()=>{{}});
    }} else {{
      window.addEventListener('deviceorientation', onGyro, true);
      gyroOn = true;
    }}
  }};

  // ── render ─────────────────────────────────────────
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
