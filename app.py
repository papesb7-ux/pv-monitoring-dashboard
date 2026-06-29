"""
app.py - Point d entree et navigation du PV Monitoring Dashboard (V1).
"""

import streamlit as st

st.set_page_config(
    page_title="PV Monitoring Dashboard",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded",
)

accueil = st.Page("views/accueil.py", title="Vue d ensemble", icon="☀️", default=True)
suivi_residus = st.Page("views/suivi_residus.py", title="Suivi des residus", icon="📉")
detection = st.Page("views/detection_anomalies.py", title="Detection d anomalies", icon="🚦")
qualite = st.Page("views/qualite_donnees.py", title="Qualite des donnees", icon="🧮")
episodes = st.Page("views/episodes_critiques.py", title="Episodes critiques", icon="📅")
performance = st.Page("views/performance_modele.py", title="Performance du modele", icon="📊")
methodologie = st.Page("views/methodologie.py", title="Methodologie", icon="📘")

navigation = st.navigation(
    {
        "Monitoring": [accueil, suivi_residus, detection, qualite, episodes],
        "Modele": [performance],
        "Reference": [methodologie],
    }
)

navigation.run()
