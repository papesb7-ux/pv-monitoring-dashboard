"""
views/episodes_critiques.py
Episodes critiques de sous-performance persistante.
Regroupe les journees en evenements datees, avec pour chacun : duree, gravite
maximale, et energie estimee non produite RELATIVE au modele de reference.
La valorisation economique (dependante du net-metering) n'est PAS traitee ici :
elle releve d'une analyse separee. Lecture seule.
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from src import data_loader as dl
from src import labels

NIVEAUX = {
    -1: "Donnees insuffisantes",
    0: "Normal",
    1: "Alerte journaliere",
    2: "Surveillance (7j)",
    3: "Avertissement soutenu",
    4: "Critique persistant",
    5: "Critique severe persistant",
}
COULEURS = {
    -1: "#b0b0b0", 0: "#2e7d32", 1: "#fbc02d", 2: "#fb8c00",
    3: "#f4511e", 4: "#e53935", 5: "#8e0000",
}


def _fmt_kwh(x):
    try:
        return f"{abs(float(x)):,.0f}".replace(",", " ") + " kWh"
    except (TypeError, ValueError):
        return "n/a"


st.title("📅 Episodes critiques")
st.caption(
    "Periodes de sous-performance persistante regroupees en evenements. Pour "
    "chaque episode : duree, gravite maximale atteinte, et energie estimee non "
    "produite par rapport au modele de reference. Cette energie est une estimation "
    "RELATIVE au modele, pas une perte mesuree ; sa valorisation economique "
    "(dependante du regime de comptage) est traitee separement."
)

df = dl.load_episodes().copy()

# Dates en datetime.
df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce")
df = df.sort_values("start_date").reset_index(drop=True)

# Magnitude d'energie (valeur absolue, pour lecture ; le tableau garde le signe brut).
df["shortfall_abs"] = df["estimated_model_relative_shortfall_kwh"].abs()

# Etat "actif au dernier jour fiable" (robuste bool / texte).
actif_bool = df["active_on_latest_valid_day"].astype(str).str.lower().isin(["true", "1", "yes"])

# --- Indicateurs ---
nb_episodes = len(df)
jours_critiques = int(df["critical_day_count"].sum())
idx_long = df["duration_calendar_days"].idxmax()
plus_long = df.loc[idx_long]
energie_totale = df["estimated_model_relative_shortfall_kwh"].sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Episodes critiques", f"{nb_episodes}")
c2.metric("Jours critiques cumules", f"{jours_critiques}")
c3.metric("Episode le plus long", f"{int(plus_long['duration_calendar_days'])} j")
c4.metric("Energie estimee non produite (cumul)", _fmt_kwh(energie_totale))

info = (
    "Episode le plus long : " + str(plus_long["critical_episode_id"])
    + " du " + plus_long["start_date"].strftime("%d/%m/%Y")
    + " au " + plus_long["end_date"].strftime("%d/%m/%Y")
    + " (" + str(int(plus_long["duration_calendar_days"])) + " jours calendaires, "
    + str(int(plus_long["critical_day_count"])) + " jours critiques)."
)
if actif_bool.any():
    info += " Un episode etait encore actif au dernier jour fiable."
st.info(info)

# --- Frise temporelle ---
st.subheader("Frise des episodes")

df["niveau_label"] = df["maximum_anomaly_level"].map(
    lambda l: "Niveau " + str(l) + " — " + NIVEAUX.get(l, "?")
)
color_map = {
    "Niveau " + str(l) + " — " + NIVEAUX.get(l, "?"): COULEURS.get(l, "#888888")
    for l in sorted(df["maximum_anomaly_level"].unique())
}
ordre_labels = [
    "Niveau " + str(l) + " — " + NIVEAUX.get(l, "?")
    for l in sorted(df["maximum_anomaly_level"].unique())
]

df["frise"] = "Episodes"
df["end_affichage"] = df["end_date"] + pd.Timedelta(days=1)  # visibilite des episodes courts
df["debut_txt"] = df["start_date"].dt.strftime("%d/%m/%Y")
df["fin_txt"] = df["end_date"].dt.strftime("%d/%m/%Y")

fig = px.timeline(
    df,
    x_start="start_date",
    x_end="end_affichage",
    y="frise",
    color="niveau_label",
    color_discrete_map=color_map,
    category_orders={"niveau_label": ordre_labels},
    hover_data={
        "frise": False,
        "niveau_label": False,
        "debut_txt": True,
        "fin_txt": True,
        "duration_calendar_days": True,
        "critical_day_count": True,
        "shortfall_abs": ":,.0f",
    },
    labels={
        "debut_txt": "Debut",
        "fin_txt": "Fin",
        "duration_calendar_days": "Duree (j calendaires)",
        "critical_day_count": "Jours critiques",
        "shortfall_abs": "Energie estimee non produite (kWh)",
        "niveau_label": "Gravite maximale",
    },
)
fig.update_layout(
    height=220, margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    xaxis_title=None,
)
fig.update_yaxes(title=None)
st.plotly_chart(fig, use_container_width=True)
st.caption(
    "Chaque segment est un episode critique, colore par la gravite maximale "
    "atteinte. Survolez un segment pour le detail. (Largeur affichee arrondie "
    "au jour superieur pour la lisibilite des episodes courts.)"
)

# --- Tableau detaille ---
st.subheader("Detail des episodes")

disp = pd.DataFrame({
    "Episode": df["critical_episode_id"],
    "Debut": df["start_date"].dt.strftime("%d/%m/%Y"),
    "Fin": df["end_date"].dt.strftime("%d/%m/%Y"),
    "Duree (j)": df["duration_calendar_days"],
    "Jours critiques": df["critical_day_count"],
    "Gravite max": df["maximum_anomaly_level"],
    "Statut max": df["maximum_status"].map(labels.traduire),
    "Ecart moyen (%)": df["mean_daily_gap_percent"].round(1),
    "Energie non produite (kWh)": df["estimated_model_relative_shortfall_kwh"].round(0),
})
st.dataframe(disp, use_container_width=True, hide_index=True, height=520)

st.caption(
    "Source : 12L_final_critical_anomaly_episodes.csv. L'energie non produite est "
    "estimee comme l'ecart cumule a la production attendue par le modele "
    "(grandeur model-relative, non mesuree au compteur)."
)
