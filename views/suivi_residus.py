"""
pages/1_Suivi_des_residus.py
Suivi des residus sur la periode out-of-time 2023-2025.
Trace la puissance mesuree vs predite et le residu (mesure - predite),
a partir des predictions 5 min. Lecture seule.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src import data_loader as dl

st.set_page_config(page_title="Suivi des residus", page_icon="📉", layout="wide")

st.title("📉 Suivi des residus")
st.caption(
    "Puissance mesuree vs predite par le modele de reference, et residu "
    "(mesure - predite) au pas de 5 minutes. Un residu negatif signifie une "
    "puissance mesuree inferieure a l'attendu du modele."
)

# --- Donnees ---
pred = dl.load_oot_predictions()

date_min = pred["timestamp"].min().date()
date_max = pred["timestamp"].max().date()

# Fenetre par defaut : 30 derniers jours de la periode disponible.
default_start = max(date_min, (pred["timestamp"].max() - pd.Timedelta(days=30)).date())

# --- Controles ---
col_dates, col_jour = st.columns([3, 1])

with col_dates:
    selection = st.date_input(
        "Plage de dates",
        value=(default_start, date_max),
        min_value=date_min,
        max_value=date_max,
        format="DD/MM/YYYY",
    )

with col_jour:
    jour_seulement = st.checkbox("Heures de jour uniquement", value=True)

# st.date_input peut renvoyer une seule date pendant la selection : on attend deux dates.
if not (isinstance(selection, (tuple, list)) and len(selection) == 2):
    st.info("Selectionne une date de debut ET une date de fin.")
    st.stop()

start_date, end_date = selection
if start_date > end_date:
    st.warning("La date de debut est posterieure a la date de fin.")
    st.stop()

# --- Filtrage ---
masque = (
    (pred["timestamp"].dt.date >= start_date)
    & (pred["timestamp"].dt.date <= end_date)
)
if jour_seulement:
    masque = masque & (pred["daylight_flag"] == 1)

fenetre = pred.loc[masque].sort_values("timestamp")

if fenetre.empty:
    st.warning("Aucune donnee sur cette plage (essaie d'elargir, ou decoche le filtre jour).")
    st.stop()

# --- Indicateurs de la fenetre ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Points affiches", f"{len(fenetre):,}".replace(",", " "))
c2.metric("Residu moyen (kW)", f"{fenetre['residual_kw'].mean():+.3f}")
c3.metric("Residu median (kW)", f"{fenetre['residual_kw'].median():+.3f}")
part_negatif = float((fenetre["residual_kw"] < 0).mean() * 100)
c4.metric("Points en sous-production", f"{part_negatif:.0f} %")

# --- Graphique 1 : mesure vs predite ---
st.subheader("Puissance mesuree vs predite")
fig_p = go.Figure()
fig_p.add_trace(go.Scattergl(
    x=fenetre["timestamp"], y=fenetre["measured_active_power_kw"],
    mode="lines", name="Mesuree", line=dict(width=1),
))
fig_p.add_trace(go.Scattergl(
    x=fenetre["timestamp"], y=fenetre["predicted_active_power_kw"],
    mode="lines", name="Predite", line=dict(width=1),
))
fig_p.update_layout(
    height=380, margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified",
    xaxis_title=None, yaxis_title="Puissance (kW)",
)
st.plotly_chart(fig_p, use_container_width=True)

# --- Graphique 2 : residu ---
st.subheader("Residu (mesure - predite)")
fig_r = go.Figure()
fig_r.add_trace(go.Scattergl(
    x=fenetre["timestamp"], y=fenetre["residual_kw"],
    mode="lines", name="Residu", line=dict(width=1),
))
fig_r.add_hline(y=0, line_dash="dash", line_width=1)
fig_r.update_layout(
    height=320, margin=dict(l=10, r=10, t=10, b=10),
    showlegend=False, hovermode="x unified",
    xaxis_title=None, yaxis_title="Residu (kW)",
)
st.plotly_chart(fig_r, use_container_width=True)

st.caption(
    "Source : model_03_random_forest_oot_predictions.parquet. "
    "Residu = puissance mesuree - puissance predite."
)
