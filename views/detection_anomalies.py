"""
views/detection_anomalies.py
Detection d'anomalies au niveau quotidien sur la periode out-of-time.
Deux graphiques empiles :
  1) ecart relatif quotidien + moyennes glissantes 7j/30j + 3 seuils calibres
  2) frise des niveaux d'anomalie (-1 a 5), un jour = une barre coloree
Lecture seule. Aucun calcul d'anomalie ici : tout vient du notebook 02.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src import data_loader as dl
from src import labels

# Libelles courts des niveaux (coherents avec la page d'accueil).
NIVEAUX = {
    -1: "Donnees insuffisantes",
    0: "Normal",
    1: "Alerte journaliere",
    2: "Surveillance (7j)",
    3: "Avertissement soutenu",
    4: "Critique persistant",
    5: "Critique severe persistant",
}

# Palette par niveau : gris -> vert -> jaune -> orange -> rouge -> rouge fonce.
COULEURS = {
    -1: "#b0b0b0",
    0: "#2e7d32",
    1: "#fbc02d",
    2: "#fb8c00",
    3: "#f4511e",
    4: "#e53935",
    5: "#8e0000",
}

st.title("🚦 Detection d'anomalies")
st.caption(
    "Classification quotidienne de la sous-performance relative au modele de "
    "reference fige. Un jour est signale lorsque l'ecart relatif (ou sa moyenne "
    "glissante) descend sous un seuil calibre sur la periode 2020-2022."
)

# --- Donnees ---
df = dl.load_daily_classification()
thresholds = dl.load_thresholds()
latest = dl.load_latest_status()


# --- Seuils, lus depuis le fichier 12J (jamais codes en dur) ---
def _seuil(mot_cle):
    ligne = thresholds[thresholds["indicator"].str.contains(mot_cle, case=False, na=False)]
    return float(ligne["threshold_percent"].iloc[0])

seuil_jour = _seuil("Daily")
seuil_7j = _seuil("7-day")
seuil_30j = _seuil("30-day")


# --- Filtre par annee ---
annees = ["Tout"] + [str(a) for a in sorted(df["year"].unique())]
choix = st.radio("Annee affichee", annees, horizontal=True)
vue = df if choix == "Tout" else df[df["year"] == int(choix)]

# --- Indicateurs (sur la vue selectionnee) ---
jours_total = len(vue)
jours_valides = int(vue["monitoring_valid_day"].sum())
jours_sousperf = int((vue["anomaly_level"] >= 1).sum())
part_sousperf = (jours_sousperf / jours_valides * 100) if jours_valides else 0.0

niveau_actuel = int(latest["anomaly_level"].iloc[0])
serie_30j = int(latest["rolling_30d_alert_streak_days"].iloc[0])
jour_fiable = latest["latest_valid_monitoring_date"].iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Jours analyses", f"{jours_total}")
c2.metric("Jours valides (couv. ≥ 80%)", f"{jours_valides}")
c3.metric("Jours en sous-performance (niv. ≥ 1)", f"{jours_sousperf}  ({part_sousperf:.0f} %)")
c4.metric("Niveau actuel", f"{niveau_actuel} — {NIVEAUX.get(niveau_actuel, '?')}")

st.info(
    "Au dernier jour fiable (" + str(jour_fiable) + ") : niveau "
    + str(niveau_actuel) + " — " + NIVEAUX.get(niveau_actuel, "?")
    + ", serie persistante (30j) de " + str(serie_30j) + " jours."
)

# --- Graphique 1 : ecart + moyennes glissantes + seuils ---
st.subheader("Ecart relatif et moyennes glissantes")

valides = vue[vue["monitoring_valid_day"]]

fig1 = go.Figure()
fig1.add_trace(go.Scatter(
    x=valides["date"], y=valides["relative_energy_gap_percent"],
    mode="markers", name="Ecart quotidien (jours valides)",
    marker=dict(size=3, color="#b0b0b0", opacity=0.45),
))
fig1.add_trace(go.Scatter(
    x=vue["date"], y=vue["rolling_7d_relative_gap_percent"],
    mode="lines", name="Moyenne glissante 7j",
    line=dict(width=1.5, color="#1f77b4"), connectgaps=False,
))
fig1.add_trace(go.Scatter(
    x=vue["date"], y=vue["rolling_30d_relative_gap_percent"],
    mode="lines", name="Moyenne glissante 30j",
    line=dict(width=2, color="#6a1b9a"), connectgaps=False,
))
fig1.add_hline(y=seuil_jour, line_dash="dot", line_color="#9e9e9e", line_width=1)
fig1.add_hline(y=seuil_7j, line_dash="dot", line_color="#1f77b4", line_width=1)
fig1.add_hline(y=seuil_30j, line_dash="dot", line_color="#6a1b9a", line_width=1)
fig1.update_layout(
    height=380, margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified",
    xaxis_title=None, yaxis_title="Ecart relatif d'energie (%)",
)
st.plotly_chart(fig1, use_container_width=True)
st.caption(
    "Seuils (5e percentile, calibration 2020-2022) : journalier "
    + f"{seuil_jour:.2f} %, 7j {seuil_7j:.2f} %, 30j {seuil_30j:.2f} %. "
    "Un point sous le seuil indique une performance anormalement basse vis-a-vis du modele."
)

# --- Graphique 2 : frise des niveaux d'anomalie ---
st.subheader("Niveau d'anomalie au cours du temps")

fig2 = go.Figure()
for lvl in sorted(vue["anomaly_level"].unique()):
    sous = vue[vue["anomaly_level"] == lvl]
    fig2.add_trace(go.Bar(
        x=sous["date"], y=[1] * len(sous),
        name=str(lvl) + " — " + NIVEAUX.get(lvl, "?"),
        marker_color=COULEURS.get(lvl, "#888888"),
        marker_line_width=0,
        hovertext=sous["date"].dt.strftime("%d/%m/%Y") + " — " + sous["anomaly_status"].astype(str).map(labels.traduire),
        hoverinfo="text",
    ))
fig2.update_layout(
    barmode="stack", bargap=0,
    height=180, margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)
fig2.update_yaxes(visible=False, range=[0, 1], fixedrange=True)
fig2.update_xaxes(title=None)
st.plotly_chart(fig2, use_container_width=True)

# --- Reference : regles de classification ---
with st.expander("Regles de classification (rulebook)"):
    st.dataframe(dl.load_rulebook(), use_container_width=True, hide_index=True)

st.caption(
    "Source : model_03_random_forest_final_daily_anomaly_classification.parquet "
    "et 12J_residual_monitoring_thresholds.csv (notebook de modelisation)."
)
