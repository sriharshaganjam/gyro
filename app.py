import streamlit as st

st.set_page_config(layout="wide")

# Clean UI
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
        body { margin: 0; }
    </style>
""", unsafe_allow_html=True)

html_code = """
<div id="panorama" style="width:100vw; height:100vh;"></div>

<link rel="stylesheet" href="https://pannellum.org/css/pannellum.css"/>
<script src="https://pannellum.org/js/pannellum.js"></script>

<script>
setTimeout(function() {
    pannellum.viewer('panorama', {
        type: "equirectangular",

        // ✅ guaranteed working test image
        panorama: "https://pannellum.org/images/alma.jpg",

        autoLoad: true,
        showControls: false,
        orientationOnByDefault: true,

        hfov: 100,
        minHfov: 50,
        maxHfov: 120
    });
}, 500);
</script>
"""

st.html(html_code, height=900)
