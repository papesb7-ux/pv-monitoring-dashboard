"""
app.py — Page d'accueil du PV Monitoring Dashboard (V1).
Synthese en lecture seule des resultats de monitoring pre-calcules.
"""

import streamlit as st
import pandas as pd

from src import data_loader as dl
from src import labels

st.set_page_config(
    page_title="PV Monitoring Dashboard",
    page_icon="☀️",
    layout="wide",
)

# Correspondance niveau entier -> libelle court (issue du rulebook).
NIVEAUX = {
    -1: "Donnees insuffisantes",
    0: "Normal",
    1: "Alerte journaliere",
    2: "Surveillance (7j)",
    3: "Avertissement soutenu",
    4: "Critique persistant",
    5: "Critique severe persistant",
}

st.title("☀️ PV Monitoring Dashboard")
st.caption(
    "Surveillance de la sous-performance relative au modele — "
    "site DKASC, periode d'evaluation out-of-time 2023-2025. "
    "Tableau de bord en lecture seule."
)

# --- Chargement des donnees ---
classification = dl.load_daily_classification()
latest = dl.load_latest_status()
registry = dl.load_model_registry()

# --- Cadrage de la periode ---
date_min = classification["date"].min()
date_max = classification["date"].max()
nb_jours = len(classification)
nb_valides = int(classification["monitoring_valid_day"].sum())

st.header("Vue d'ensemble")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Modele de reference", "Random Forest")
col2.metric("Periode evaluee", f"{date_min:%d/%m/%Y} → {date_max:%d/%m/%Y}")
col3.metric("Jours analyses", f"{nb_jours}")
col4.metric("Jours valides (couv. ≥ 80%)", f"{nb_valides}")

# --- Dernier statut connu ---
st.header("Dernier statut de monitoring fiable")

niveau_actuel = int(latest["anomaly_level"].iloc[0])
statut_actuel = labels.traduire(latest["anomaly_status"].iloc[0])
date_fiable = latest["latest_valid_monitoring_date"].iloc[0]
action = labels.traduire(latest["recommended_action"].iloc[0])

colA, colB = st.columns([1, 2])
colA.metric("Niveau actuel", f"{niveau_actuel} — {NIVEAUX.get(niveau_actuel, '?')}")
colB.metric("Dernier jour fiable", str(date_fiable))

st.info("**Statut :** " + str(statut_actuel) + "  \n**Action recommandee :** " + str(action))

st.warning(
    "Un niveau eleve signale une sous-performance **relative au modele de "
    "reference fige**, et non une panne materielle confirmee. "
    "L'interpretation physique releve d'une inspection technique."
)

# --- Repartition des niveaux ---
st.header("Repartition des niveaux d'anomalie")

repartition = (
    classification["anomaly_level"]
    .map(lambda n: f"{n} — {NIVEAUX.get(n, '?')}")
    .value_counts()
    .sort_index()
    .rename_axis("Niveau")
    .reset_index(name="Nombre de jours")
)

st.dataframe(repartition, use_container_width=True, hide_index=True)

st.caption(
    "Source : model_03_random_forest_final_daily_anomaly_classification.parquet "
    "— genere par le notebook de modelisation (Colab)."
)
