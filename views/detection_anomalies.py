"""views/detection_anomalies.py — Detection d'anomalies au niveau quotidien (V1).

Deux graphiques empiles :
  1) ecart relatif quotidien + moyennes glissantes 7j/30j + 3 seuils calibres ;
  2) frise des niveaux de surveillance (-1 a 5), un jour = une barre coloree.

Lecture seule. Aucun calcul d'anomalie ici : tout provient des fichiers du notebook.
Couleurs et libelles centralises dans src/theme.py.
"""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from src import data_loader as dl
from src import labels
from src import theme


def _ticks_mensuels(dates):
    if len(dates) == 0:
        return [], []
    dmin = pd.Timestamp(dates.min()).normalize().replace(day=1)
    dmax = pd.Timestamp(dates.max()).normalize()
    mois = pd.date_range(dmin, dmax, freq="MS")
    return list(mois), [m.strftime("%m/%Y") for m in mois]


def _seuil(thresholds, mot_cle):
    ligne = thresholds[thresholds["indicator"].str.contains(mot_cle, case=False, na=False)]
    return float(ligne["threshold_percent"].iloc[0])


st.title("🚦 Détection d'anomalies")
st.caption(
    "Classification quotidienne de la sous-performance relative au modèle de référence figé. "
    "Un jour est signalé lorsque l'écart relatif (ou sa moyenne glissante) descend sous un "
    "seuil calibré sur la période 2020–2022, en tenant compte de la persistance temporelle."
)

# ------------------------------------------------------------------
# Donnees
# ------------------------------------------------------------------
df = dl.load_daily_classification()
thresholds = dl.load_thresholds()
latest = dl.load_latest_status()

seuil_jour = _seuil(thresholds, "Daily")
seuil_7j = _seuil(thresholds, "7-day")
seuil_30j = _seuil(thresholds, "30-day")

# ------------------------------------------------------------------
# Filtre par annee
# ------------------------------------------------------------------
annees = ["Tout"] + [str(a) for a in sorted(df["year"].unique())]
choix = st.radio("Année affichée", annees, horizontal=True)
filtre_actif = choix != "Tout"
vue = df if not filtre_actif else df[df["year"] == int(choix)]

# ------------------------------------------------------------------
# Indicateurs
# ------------------------------------------------------------------
jours_total = len(vue)
jours_valides = int(vue["monitoring_valid_day"].sum())
jours_signales = int((vue["anomaly_level"] >= 1).sum())
part_signales = (jours_signales / jours_valides * 100) if jours_valides else 0.0

c1, c2, c3 = st.columns(3)
c1.metric("Jours analysés", f"{jours_total}")
c2.metric("Jours valides (couverture ≥ 80 %)", f"{jours_valides}")
c3.metric(
    "Jours signalés par le monitoring — niveau ≥ 1",
    f"{jours_signales}  ({part_signales:.1f} %)",
)

# ------------------------------------------------------------------
# Dernier niveau fiable
# ------------------------------------------------------------------
if filtre_actif:
    # Dernier jour valide de la periode selectionnee.
    sous_valides = vue[vue["monitoring_valid_day"]].sort_values("date")
    if sous_valides.empty:
        st.info("Aucun jour valide sur la période sélectionnée.")
        st.stop()
    ligne = sous_valides.iloc[-1]
    titre_niveau = "Dernier niveau fiable de la période sélectionnée"
    niveau = int(ligne["anomaly_level"])
    jour_fiable = pd.Timestamp(ligne["date"])
    ecart_j = float(ligne["relative_energy_gap_percent"])
    ecart_7 = float(ligne["rolling_7d_relative_gap_percent"])
    ecart_30 = float(ligne["rolling_30d_relative_gap_percent"])
    persist_30 = int(ligne["rolling_30d_alert_streak_days"])
    statut = labels.traduire(ligne["anomaly_status"])
else:
    titre_niveau = "Dernier niveau fiable"
    niveau = int(latest["anomaly_level"].iloc[0])
    jour_fiable = pd.to_datetime(latest["latest_valid_monitoring_date"].iloc[0])
    ecart_j = float(latest["relative_energy_gap_percent"].iloc[0])
    ecart_7 = float(latest["rolling_7d_relative_gap_percent"].iloc[0])
    ecart_30 = float(latest["rolling_30d_relative_gap_percent"].iloc[0])
    persist_30 = int(latest["rolling_30d_alert_streak_days"].iloc[0])
    statut = labels.traduire(latest["anomaly_status"].iloc[0])

st.subheader(titre_niveau)
st.markdown(
    f"### Niveau {niveau} — {theme.NIVEAUX.get(niveau, '?')}  \n"
    f"**Dernier jour fiable :** {jour_fiable:%d/%m/%Y} — {statut}"
)
m1, m2, m3, m4 = st.columns(4)
m1.metric("Écart quotidien", f"{ecart_j:+.3f} %")
m2.metric("Moyenne glissante 7 j", f"{ecart_7:+.3f} %")
m3.metric("Moyenne glissante 30 j", f"{ecart_30:+.3f} %")
m4.metric("Persistance 30 j", f"{persist_30} j")

# ------------------------------------------------------------------
# Graphique 1 : ecart + moyennes glissantes + seuils
# ------------------------------------------------------------------
st.subheader("Écart relatif et moyennes glissantes")

# Jours invalides -> NaN : pas de liaison artificielle entre periodes separees.
ecart_valide = vue["relative_energy_gap_percent"].where(vue["monitoring_valid_day"])

tv, tt = _ticks_mensuels(vue["date"])

fig1 = go.Figure()
fig1.add_trace(go.Scatter(
    x=vue["date"], y=ecart_valide,
    mode="markers", name="Écart quotidien (jours valides)",
    marker=dict(size=3, color="#b0b0b0", opacity=0.45),
))
fig1.add_trace(go.Scatter(
    x=vue["date"], y=vue["rolling_7d_relative_gap_percent"],
    mode="lines", name="Moyenne glissante 7 j",
    line=dict(width=1.5, color="#1f77b4"), connectgaps=False,
))
fig1.add_trace(go.Scatter(
    x=vue["date"], y=vue["rolling_30d_relative_gap_percent"],
    mode="lines", name="Moyenne glissante 30 j",
    line=dict(width=2, color="#6a1b9a"), connectgaps=False,
))
fig1.add_hline(y=seuil_jour, line_dash="dot", line_color="#9e9e9e", line_width=1,
               annotation_text=f"Seuil quotidien {seuil_jour:.2f} %",
               annotation_position="top left")
fig1.add_hline(y=seuil_7j, line_dash="dash", line_color="#1f77b4", line_width=1,
               annotation_text=f"Seuil 7 j {seuil_7j:.2f} %",
               annotation_position="top right")
fig1.add_hline(y=seuil_30j, line_dash="dashdot", line_color="#6a1b9a", line_width=1,
               annotation_text=f"Seuil 30 j {seuil_30j:.2f} %",
               annotation_position="bottom right")
fig1.update_layout(
    height=400, margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    hovermode="x unified", xaxis_title=None, yaxis_title="Écart relatif d'énergie (%)",
)
fig1.update_xaxes(tickvals=tv, ticktext=tt)
st.plotly_chart(fig1, use_container_width=True)
st.caption(
    "Seuils (5ᵉ percentile, calibration 2020–2022, lus dans 12J) : "
    f"quotidien {seuil_jour:.2f} %, 7 j {seuil_7j:.2f} %, 30 j {seuil_30j:.2f} %. "
    "Les interruptions des courbes correspondent à des journées manquantes ou à une "
    "couverture insuffisante : elles ne représentent pas une performance nulle. "
    "Une journée invalide interrompt les séquences de persistance."
)

# ------------------------------------------------------------------
# Graphique 2 : frise des niveaux de surveillance
# ------------------------------------------------------------------
st.subheader("Niveau de surveillance au cours du temps")

vue = vue.copy()
vue["couverture_pct"] = vue["daily_coverage_ratio"] * 100.0
vue["statut_fr"] = vue["anomaly_status"].map(labels.traduire)

fig2 = go.Figure()
for lvl in sorted(vue["anomaly_level"].unique()):
    sous = vue[vue["anomaly_level"] == lvl]
    survol = (
        "Date : " + sous["date"].dt.strftime("%d/%m/%Y")
        + "<br>Couverture : " + sous["couverture_pct"].round(1).astype(str) + " %"
        + "<br>Niveau : " + str(int(lvl)) + " — " + theme.NIVEAUX.get(int(lvl), "?")
        + "<br>Statut : " + sous["statut_fr"].astype(str)
        + "<br>Écart quotidien : " + sous["relative_energy_gap_percent"].round(2).astype(str) + " %"
        + "<br>Moyenne 7 j : " + sous["rolling_7d_relative_gap_percent"].round(2).astype(str) + " %"
        + "<br>Moyenne 30 j : " + sous["rolling_30d_relative_gap_percent"].round(2).astype(str) + " %"
        + "<br>Persistance 30 j : " + sous["rolling_30d_alert_streak_days"].astype(str) + " j"
    )
    fig2.add_trace(go.Bar(
        x=sous["date"], y=[1] * len(sous),
        name=str(int(lvl)) + " — " + theme.NIVEAUX.get(int(lvl), "?"),
        marker_color=theme.COULEURS.get(int(lvl), "#888888"),
        marker_line_width=0,
        hovertext=survol, hoverinfo="text",
    ))
fig2.update_layout(
    barmode="stack", bargap=0,
    height=200, margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)
fig2.update_yaxes(visible=False, range=[0, 1], fixedrange=True)
fig2.update_xaxes(tickvals=tv, ticktext=tt)
st.plotly_chart(fig2, use_container_width=True)

st.warning(
    "Un signalement représente une sous-performance **relative au modèle de référence**. "
    "Il ne confirme pas automatiquement une panne ni sa cause technique : l'origine "
    "(système photovoltaïque, capteurs, qualité des données, conditions d'exploitation ou "
    "limites du modèle) reste à vérifier par une investigation technique."
)

# ------------------------------------------------------------------
# Reference : regles de classification
# ------------------------------------------------------------------
with st.expander("Règles de classification"):
    st.dataframe(dl.load_rulebook(), use_container_width=True, hide_index=True)

st.caption(
    "Source : model_03_random_forest_final_daily_anomaly_classification.parquet "
    "et 12J_residual_monitoring_thresholds.csv (notebook de modélisation)."
)
