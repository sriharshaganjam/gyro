import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(layout="wide")

# Clean full-screen layout
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
    </style>
""", unsafe_allow_html=True)

# ✅ Your Google Drive direct link
IMAGE_URL = "https://drive.google.com/uc?export=view&id=18JMqRl4agEJwJo5YVIi2NTEDDr_-CIpg"

html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">

    <link rel="stylesheet" href="https://pannellum.org/css/pannellum.css"/>
    <script src="https://pannellum.org/js/pannellum.js"></script>

    <style>
        html, body {{
            margin: 0;
            height: 100%;
            background: black;
            overflow: hidden;
        }}

        #panorama {{
            width: 100vw;
            height: 100vh;
        }}
    </style>
</head>

<body>

<div id="panorama"></div>

<script>
pannellum.viewer('panorama', {{
    type: "equirectangular",

    panorama: "{IMAGE_URL}",

    autoLoad: true,

    // Gyro
    orientationOnByDefault: true,

    // Clean UI
    showControls: false,

    // Better viewing experience
    hfov: 100,
    minHfov: 50,
    maxHfov: 120,

    pitch: 0,
    yaw: 0
}});
</script>

</body>
</html>
"""

components.html(html_code, height=800, scrolling=False)
