"""views/accueil.py — Vue d'ensemble du PV Monitoring Dashboard (V1).

Synthese en lecture seule des resultats de monitoring precalcules.
Toutes les valeurs affichees sont lues dans les fichiers (aucune valeur codee en dur).
"""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from src import data_loader as dl
from src import labels
from src import theme

st.title("☀️ PV Monitoring Dashboard")
st.caption(
    "Surveillance de la sous-performance relative au modèle de référence — site DKASC. "
    "Évaluation temporelle out-of-time post-sélection 2023–2025. "
    "Tableau de bord en lecture seule."
)

# ------------------------------------------------------------------
# Donnees
# ------------------------------------------------------------------
classification = dl.load_daily_classification()
latest = dl.load_latest_status()

date_min = classification["date"].min()
date_max = classification["date"].max()
nb_jours = len(classification)
nb_valides = int(classification["monitoring_valid_day"].sum())

# Couverture du dernier jour observe (note sur l'annee 2025 partielle).
couv_dernier = float(
    classification.loc[classification["date"] == date_max, "daily_coverage_ratio"].iloc[0] * 100.0
)

# ------------------------------------------------------------------
# Vue d'ensemble
# ------------------------------------------------------------------
st.header("Vue d'ensemble")

st.markdown(
    f"**Période évaluée :** du {date_min:%d/%m/%Y} au {date_max:%d/%m/%Y}  \n"
    f"*2023–2025 — l'année 2025 est partielle, arrêtée au {date_max:%d/%m/%Y}.*"
)

c1, c2, c3 = st.columns(3)
c1.metric("Modèle de référence", "Random Forest")
c2.metric("Jours analysés", f"{nb_jours}")
c3.metric("Jours valides (couverture ≥ 80 %)", f"{nb_valides}")

# ------------------------------------------------------------------
# Dernier statut de monitoring fiable
# ------------------------------------------------------------------
st.header("Dernier statut de monitoring fiable")

niveau = int(latest["anomaly_level"].iloc[0])
statut = labels.traduire(latest["anomaly_status"].iloc[0])
action = labels.traduire(latest["recommended_action"].iloc[0])
jour_fiable = pd.to_datetime(latest["latest_valid_monitoring_date"].iloc[0])

ecart_j = float(latest["relative_energy_gap_percent"].iloc[0])
ecart_7 = float(latest["rolling_7d_relative_gap_percent"].iloc[0])
ecart_30 = float(latest["rolling_30d_relative_gap_percent"].iloc[0])
persist_30 = int(latest["rolling_30d_alert_streak_days"].iloc[0])

st.markdown(f"### Niveau {niveau} — {theme.NIVEAUX.get(niveau, '?')}")
st.markdown(f"**Dernier jour fiable :** {jour_fiable:%d/%m/%Y}")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Écart quotidien", f"{ecart_j:+.3f} %")
m2.metric("Moyenne glissante 7 j", f"{ecart_7:+.3f} %")
m3.metric("Moyenne glissante 30 j", f"{ecart_30:+.3f} %")
m4.metric("Persistance 30 j", f"{persist_30} j")

st.info(
    f"**Statut :** {statut} — relative au modèle de référence.  \n"
    f"**Action recommandée :** {action}"
)

st.warning(
    "Un niveau élevé signale une sous-performance **relative au modèle de référence figé**, "
    "et non une panne matérielle confirmée. La cause (système photovoltaïque, capteurs, "
    "qualité des données, conditions d'exploitation ou limites du modèle) reste à vérifier "
    "par une investigation technique."
)

st.caption(
    f"Le dernier jour observé ({date_max:%d/%m/%Y}) présente une couverture insuffisante "
    f"(≈ {couv_dernier:.2f} %) et n'est pas interprété comme une anomalie de production ; "
    f"le dernier jour fiable retenu est le {jour_fiable:%d/%m/%Y}."
)

# ------------------------------------------------------------------
# Repartition des niveaux de surveillance
# ------------------------------------------------------------------
st.header("Répartition des niveaux de surveillance")

total = nb_jours
denom_valides = int((classification["anomaly_level"] >= 0).sum())
counts = classification["anomaly_level"].value_counts().sort_index()

lignes = []
for niv in sorted(counts.index):
    n = int(counts[niv])
    if niv < 0:
        pct = (n / total * 100.0) if total else 0.0
        base = f"{total} jours présents"
    else:
        pct = (n / denom_valides * 100.0) if denom_valides else 0.0
        base = f"{denom_valides} jours valides"
    lignes.append({
        "Niveau": theme.libelle_niveau(niv),
        "Nombre de jours": n,
        "Pourcentage": f"{pct:.1f} %",
        "Base de calcul": base,
    })

tableau = pd.DataFrame(lignes)
st.dataframe(tableau, use_container_width=True, hide_index=True)

st.caption(
    "Dénominateurs : le niveau « Données insuffisantes » est rapporté aux "
    f"{total} jours présents dans les résultats ; les niveaux 0 à 5 sont rapportés "
    f"aux {denom_valides} jours valides (couverture ≥ 80 %)."
)

# ------------------------------------------------------------------
# Histogramme horizontal du nombre de jours par niveau
# ------------------------------------------------------------------
st.subheader("Nombre de jours par niveau")

ordre = [theme.libelle_niveau(i) for i in sorted(counts.index)]
fig = go.Figure()
for niv in sorted(counts.index):
    n = int(counts[niv])
    fig.add_trace(go.Bar(
        x=[n],
        y=[theme.libelle_niveau(niv)],
        orientation="h",
        marker_color=theme.COULEURS.get(niv, "#888888"),
        text=[n],
        textposition="outside",
        name=theme.libelle_niveau(niv),
    ))
fig.update_layout(
    height=380,
    margin=dict(l=10, r=10, t=30, b=10),
    xaxis_title="Nombre de jours",
    yaxis_title=None,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)
fig.update_yaxes(categoryorder="array", categoryarray=ordre)
st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Source : model_03_random_forest_final_daily_anomaly_classification.parquet "
    "— généré par le notebook de modélisation."
)
