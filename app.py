import streamlit as st
import streamlit.components.v1 as components
import requests
import base64
import io

st.set_page_config(layout="wide")

FILE_ID = "18JMqRl4agEJwJo5YVIi2NTEDDr_-CIpg"

@st.cache_data(show_spinner="Downloading panorama from Google Drive...")
def load_image_as_base64(file_id):
    # Step 1: try direct download
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    session = requests.Session()
    response = session.get(url, stream=True)

    # Step 2: handle large-file confirmation page
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            url = f"https://drive.google.com/uc?export=download&confirm={value}&id={file_id}"
            response = session.get(url, stream=True)
            break

    # Read image bytes
    image_bytes = b"".join(response.iter_content(chunk_size=1024 * 1024))
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return b64

b64 = load_image_as_base64(FILE_ID)
image_data_url = f"data:image/jpeg;base64,{b64}"

html_code = f"""
<!DOCTYPE html>
<html>
<head>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ background: #111; color: white; font-family: sans-serif; }}
    #pano-container {{
      width: 100%;
      height: 600px;
      position: relative;
      overflow: hidden;
      cursor: grab;
    }}
    #pano-container:active {{ cursor: grabbing; }}
    canvas {{ display: block; }}
    #debug {{
      position: absolute;
      top: 10px; left: 10px;
      background: rgba(0,0,0,0.7);
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 13px;
      z-index: 10;
      pointer-events: none;
    }}
  </style>
</head>
<body>

<div id="pano-container">
  <div id="debug">Loading Three.js...</div>
  <canvas id="canvas"></canvas>
</div>

<script>
const debug = document.getElementById('debug');
const log = msg => {{ debug.textContent = msg; console.log(msg); }};

const script = document.createElement('script');
script.src = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js";
script.onload = () => initPanorama();
script.onerror = () => {{
  const s2 = document.createElement('script');
  s2.src = "https://cdn.jsdelivr.net/npm/three@0.128/build/three.min.js";
  s2.onload = () => initPanorama();
  s2.onerror = () => log("ERROR: Could not load Three.js from any CDN.");
  document.head.appendChild(s2);
}};
document.head.appendChild(script);

function initPanorama() {{
  log("Initialising viewer...");

  const container = document.getElementById('pano-container');
  const canvas = document.getElementById('canvas');
  const W = container.clientWidth;
  const H = container.clientHeight;

  const renderer = new THREE.WebGLRenderer({{ canvas, antialias: true }});
  renderer.setSize(W, H);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(80, W / H, 0.1, 1000);
  camera.position.set(0, 0, 0.01);

  const geometry = new THREE.SphereGeometry(500, 60, 40);
  geometry.scale(-1, 1, 1);

  const image = new Image();
  image.onload = () => {{
    log("✓ Panorama loaded! Drag to look around.");
    setTimeout(() => debug.style.display = 'none', 2000);
    const texture = new THREE.Texture(image);
    texture.needsUpdate = true;
    const material = new THREE.MeshBasicMaterial({{ map: texture }});
    const sphere = new THREE.Mesh(geometry, material);
    scene.add(sphere);
    animate();
  }};
  image.onerror = () => log("ERROR: Failed to decode image.");
  image.src = "{image_data_url}";

  let isDragging = false;
  let prevMouse = {{ x: 0, y: 0 }};
  let lon = 0, lat = 0;

  container.addEventListener('mousedown', e => {{ isDragging = true; prevMouse = {{ x: e.clientX, y: e.clientY }}; }});
  container.addEventListener('mouseup', () => isDragging = false);
  container.addEventListener('mousemove', e => {{
    if (!isDragging) return;
    lon -= (e.clientX - prevMouse.x) * 0.2;
    lat += (e.clientY - prevMouse.y) * 0.2;
    lat = Math.max(-85, Math.min(85, lat));
    prevMouse = {{ x: e.clientX, y: e.clientY }};
  }});

  container.addEventListener('touchstart', e => {{ isDragging = true; prevMouse = {{ x: e.touches[0].clientX, y: e.touches[0].clientY }}; }});
  container.addEventListener('touchend', () => isDragging = false);
  container.addEventListener('touchmove', e => {{
    if (!isDragging) return;
    lon -= (e.touches[0].clientX - prevMouse.x) * 0.2;
    lat += (e.touches[0].clientY - prevMouse.y) * 0.2;
    lat = Math.max(-85, Math.min(85, lat));
    prevMouse = {{ x: e.touches[0].clientX, y: e.touches[0].clientY }};
  }});

  container.addEventListener('wheel', e => {{
    camera.fov = Math.max(30, Math.min(120, camera.fov + e.deltaY * 0.05));
    camera.updateProjectionMatrix();
  }});

  function animate() {{
    requestAnimationFrame(animate);
    const phi = THREE.MathUtils.degToRad(90 - lat);
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

components.html(html_code, height=620)
