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

html_code = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <link rel="stylesheet" href="https://pannellum.org/css/pannellum.css"/>
    <script src="https://pannellum.org/js/pannellum.js"></script>

    <style>
        html, body {
            margin: 0;
            height: 100%;
            background: black;
        }
        #panorama {
            width: 100vw;
            height: 100vh;
        }
    </style>
</head>

<body>

<div id="panorama"></div>

<script>
window.onload = function() {
    pannellum.viewer('panorama', {
        type: "equirectangular",

        // ✅ TEST IMAGE (guaranteed to work)
        panorama: "https://pannellum.org/images/alma.jpg",

        autoLoad: true,

        // Gyro
        orientationOnByDefault: true,

        // Clean UI
        showControls: false,

        // Better viewing feel
        hfov: 100,
        minHfov: 50,
        maxHfov: 120,

        pitch: 0,
        yaw: 0
    });
};
</script>

</body>
</html>
"""

components.html(html_code, height=900)
