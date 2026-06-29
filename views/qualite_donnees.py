"""
views/qualite_donnees.py
Qualite et couverture des donnees sur la periode out-of-time.
Un jour n'est "valide" pour le monitoring que si sa couverture (part des
288 pas de 5 min effectivement observes en journee) atteint un seuil minimal.
Cette page explique notamment les jours non evaluables (couverture insuffisante).
Lecture seule.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src import data_loader as dl
from src import config


# --- Seuil de couverture, lu depuis app_config.yaml (robuste fraction/pourcent) ---
def _seuil_couverture_pct():
    dq = config.load_app_config().get("data_quality", {})
    for cle in ("min_daily_coverage", "min_coverage", "min_daily_coverage_ratio",
                "min_daily_coverage_percent", "coverage_min"):
        if cle in dq and dq[cle] is not None:
            val = float(dq[cle])
            return val * 100.0 if val <= 1.0 else val
    return 80.0  # valeur de repli si la cle n'est pas trouvee


seuil_pct = _seuil_couverture_pct()

st.title("🧮 Qualite des donnees")
st.caption(
    "Couverture quotidienne des mesures et part des jours exploitables pour le "
    "monitoring. Un jour dont la couverture est insuffisante n'est pas classe "
    "(niveau 'Donnees insuffisantes') : il ne traduit ni performance normale, "
    "ni anomalie, seulement une mesure incomplete."
)

df = dl.load_daily_classification().copy()

# Couverture en pourcentage (daily_coverage_ratio est une fraction 0..1).
df["couverture_pct"] = df["daily_coverage_ratio"] * 100.0

# --- Indicateurs globaux ---
total = len(df)
valides = int(df["monitoring_valid_day"].sum())
insuffisants = total - valides
part_valide = (valides / total * 100) if total else 0.0
couv_mediane = df["couverture_pct"].median()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Jours au total", f"{total}")
c2.metric("Jours exploitables", f"{valides}  ({part_valide:.0f} %)")
c3.metric("Jours insuffisants", f"{insuffisants}")
c4.metric("Couverture mediane", f"{couv_mediane:.0f} %")

st.info(
    f"Seuil de validite : couverture >= {seuil_pct:.0f} % des pas de mesure de la "
    f"journee. En dessous, le jour est marque 'Donnees insuffisantes' et exclu de "
    f"la classification d'anomalie."
)

# --- Graphique 1 : couverture quotidienne dans le temps ---
st.subheader("Couverture quotidienne dans le temps")

valid_mask = df["monitoring_valid_day"]
fig1 = go.Figure()
fig1.add_trace(go.Scattergl(
    x=df.loc[valid_mask, "date"], y=df.loc[valid_mask, "couverture_pct"],
    mode="markers", name=f"Jour valide (>= {seuil_pct:.0f} %)",
    marker=dict(size=4, color="#2e7d32", opacity=0.6),
))
fig1.add_trace(go.Scattergl(
    x=df.loc[~valid_mask, "date"], y=df.loc[~valid_mask, "couverture_pct"],
    mode="markers", name=f"Jour insuffisant (< {seuil_pct:.0f} %)",
    marker=dict(size=4, color="#b0b0b0", opacity=0.7),
))
fig1.add_hline(y=seuil_pct, line_dash="dash", line_color="#e53935", line_width=1.5)
fig1.update_layout(
    height=360, margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified",
    xaxis_title=None, yaxis_title="Couverture quotidienne (%)",
)
fig1.update_yaxes(range=[0, 105])
st.plotly_chart(fig1, use_container_width=True)
st.caption(
    "Chaque point est une journee. La ligne rouge marque le seuil de validite. "
    "Les points gris sous la ligne sont les jours non evaluables."
)

# --- Graphique 2 : repartition mensuelle valides / insuffisants ---
st.subheader("Repartition mensuelle des jours")

df["mois"] = df["date"].dt.to_period("M").dt.to_timestamp()
par_mois = (
    df.groupby("mois")["monitoring_valid_day"]
    .agg(valides="sum", total="count")
    .reset_index()
)
par_mois["insuffisants"] = par_mois["total"] - par_mois["valides"]

fig2 = go.Figure()
fig2.add_trace(go.Bar(
    x=par_mois["mois"], y=par_mois["valides"],
    name="Jours valides", marker_color="#2e7d32",
))
fig2.add_trace(go.Bar(
    x=par_mois["mois"], y=par_mois["insuffisants"],
    name="Jours insuffisants", marker_color="#b0b0b0",
))
fig2.update_layout(
    barmode="stack",
    height=340, margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    xaxis_title=None, yaxis_title="Nombre de jours",
)
st.plotly_chart(fig2, use_container_width=True)
st.caption(
    "Repartition par mois. Les periodes a forte proportion grise concentrent "
    "les lacunes de mesure et expliquent les jours non classes sur la frise "
    "de detection d'anomalies."
)

st.caption(
    "Source : model_03_random_forest_final_daily_anomaly_classification.parquet "
    "(colonnes daily_coverage_ratio, monitoring_valid_day)."
)
