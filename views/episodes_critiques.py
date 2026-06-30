"""views/episodes_critiques.py — Episodes operationnels critiques (niveaux 4 et 5).

Regroupe les journees consecutives de niveau 4-5 en evenements datees. Pour chacun :
duree, gravite maximale, ecarts moyens, et energie estimee non produite RELATIVE au
modele de reference. Un detail par episode (5 min + quotidien) est disponible via un
selecteur.

Lecture seule. Aucune valorisation economique ici (elle depend du net-metering et
releve d'une analyse separee). Couleurs et libelles centralises dans src/theme.py.
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src import data_loader as dl
from src import labels
from src import theme


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _seuil(thresholds, mot_cle):
    ligne = thresholds[thresholds["indicator"].str.contains(mot_cle, case=False, na=False)]
    return float(ligne["threshold_percent"].iloc[0])


def _fmt_kwh(x):
    try:
        return f"{abs(float(x)):,.0f}".replace(",", " ") + " kWh"
    except (TypeError, ValueError):
        return "n/a"


def _ticks_episode(timestamps):
    """Graduations adaptees a la duree d'un episode (JJ/MM si court, sinon MM/AAAA)."""
    if len(timestamps) == 0:
        return [], []
    tmin = pd.Timestamp(timestamps.min()).normalize()
    tmax = pd.Timestamp(timestamps.max()).normalize()
    span = (tmax - tmin).days
    if span <= 45:
        jours = pd.date_range(tmin, tmax, freq="D")
        pas = max(1, len(jours) // 12)
        jours = jours[::pas]
        return list(jours), [j.strftime("%d/%m") for j in jours]
    mois = pd.date_range(tmin.replace(day=1), tmax, freq="MS")
    return list(mois), [m.strftime("%m/%Y") for m in mois]


# ------------------------------------------------------------------
# En-tete
# ------------------------------------------------------------------
st.title("📅 Épisodes opérationnels critiques — niveaux 4 et 5")
st.caption(
    "Un épisode regroupe des journées consécutives classées au niveau 4 (critique "
    "persistante) ou 5 (sous-performance sévère persistante). Une journée invalide ou de "
    "niveau inférieur interrompt l'épisode. L'énergie indiquée est une estimation relative "
    "au modèle de référence, et non une perte mesurée au compteur."
)

# ------------------------------------------------------------------
# Donnees
# ------------------------------------------------------------------
df = dl.load_episodes().copy()
daily = dl.load_daily_classification()
pred = dl.load_oot_predictions()
thresholds = dl.load_thresholds()

seuil_jour = _seuil(thresholds, "Daily")
seuil_7j = _seuil(thresholds, "7-day")
seuil_30j = _seuil(thresholds, "30-day")

df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce")
df = df.sort_values("start_date").reset_index(drop=True)

# Etat actif / cloture (robuste bool ou texte).
df["actif"] = df["active_on_latest_valid_day"].astype(str).str.lower().isin(
    ["true", "1", "yes"]
)

# ------------------------------------------------------------------
# Indicateurs (toujours sur l'ensemble des episodes)
# ------------------------------------------------------------------
nb_episodes = len(df)
jours_critiques = int(df["critical_day_count"].sum())
plus_long_op = int(df["duration_calendar_days"].max())
deficit_total = df["estimated_model_relative_shortfall_kwh"].sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Épisodes critiques", f"{nb_episodes}")
c2.metric("Jours de niveau 4-5 cumulés", f"{jours_critiques}")
c3.metric("Épisode le plus long", f"{plus_long_op} j")
c4.metric("Déficit énergétique estimé relatif au modèle", _fmt_kwh(deficit_total))

st.warning(
    "Le déficit énergétique affiché est une **estimation relative au modèle de référence** "
    "(énergie attendue non produite). Ce n'est ni une perte contractuelle, ni la preuve "
    "d'une panne. Il ne doit pas être additionné aux écarts quotidien, 7 jours et 30 jours, "
    "qui décrivent les mêmes journées sous d'autres angles."
)

# Note 102 j (operationnel) vs serie brute du seuil 30 j (calcul dynamique).
serie_brute_30j = int(daily["rolling_30d_alert_streak_days"].max())
st.info(
    f"Les durées sont **opérationnelles** : un épisode regroupe des journées consécutives de "
    f"niveau 4 ou 5, et une journée invalide ou de niveau inférieur l'interrompt. Cette durée "
    f"peut différer d'un simple comptage du franchissement brut du seuil glissant 30 jours "
    f"(plus longue série observée : {serie_brute_30j} jours), car le passage en niveau critique "
    f"exige une persistance minimale : les premiers jours d'une série restent classés à un "
    f"niveau inférieur avant la bascule en critique."
)

# ------------------------------------------------------------------
# Filtres (agissent sur la frise, le tableau et le selecteur)
# ------------------------------------------------------------------
st.subheader("Filtres")
f1, f2, f3, f4 = st.columns(4)

with f1:
    annees = ["Toutes"] + [str(a) for a in sorted(
        pd.concat([df["start_date"].dt.year, df["end_date"].dt.year]).unique()
    )]
    f_annee = st.selectbox("Année", annees)
with f2:
    niveaux_dispo = sorted(df["maximum_anomaly_level"].unique())
    f_niveau = st.selectbox(
        "Gravité maximale", ["Toutes"] + [f"Niveau {n}" for n in niveaux_dispo]
    )
with f3:
    f_etat = st.selectbox("État", ["Tous", "Actif", "Clôturé"])
with f4:
    duree_max = int(df["duration_calendar_days"].max())
    f_duree = st.slider("Durée minimale (jours)", 0, duree_max, 0)

vue = df.copy()
if f_annee != "Toutes":
    an = int(f_annee)
    vue = vue[(vue["start_date"].dt.year <= an) & (vue["end_date"].dt.year >= an)]
if f_niveau != "Toutes":
    niv = int(f_niveau.split()[-1])
    vue = vue[vue["maximum_anomaly_level"] == niv]
if f_etat == "Actif":
    vue = vue[vue["actif"]]
elif f_etat == "Clôturé":
    vue = vue[~vue["actif"]]
vue = vue[vue["duration_calendar_days"] >= f_duree]

# ------------------------------------------------------------------
# Frise des episodes
# ------------------------------------------------------------------
st.subheader("Frise des épisodes")

if vue.empty:
    st.info("Aucun épisode ne correspond aux filtres sélectionnés.")
else:
    v = vue.copy()
    v["niveau_label"] = v["maximum_anomaly_level"].map(theme.libelle_niveau)
    v["end_affichage"] = v["end_date"] + pd.Timedelta(days=1)  # visibilite des episodes courts
    v["frise"] = "Épisodes"
    v["debut_txt"] = v["start_date"].dt.strftime("%d/%m/%Y")
    v["fin_txt"] = v["end_date"].dt.strftime("%d/%m/%Y")
    v["statut_fr"] = v["maximum_status"].map(labels.traduire)
    v["deficit_abs"] = v["estimated_model_relative_shortfall_kwh"].abs()

    niveaux_vue = sorted(v["maximum_anomaly_level"].unique())
    color_map = {theme.libelle_niveau(n): theme.COULEURS.get(int(n), "#888888") for n in niveaux_vue}
    ordre = [theme.libelle_niveau(n) for n in niveaux_vue]

    fig = px.timeline(
        v,
        x_start="start_date", x_end="end_affichage", y="frise",
        color="niveau_label", color_discrete_map=color_map,
        category_orders={"niveau_label": ordre},
        hover_data={
            "frise": False, "niveau_label": False,
            "critical_episode_id": True, "debut_txt": True, "fin_txt": True,
            "duration_calendar_days": True, "critical_day_count": True,
            "statut_fr": True, "deficit_abs": ":,.0f",
        },
        labels={
            "critical_episode_id": "Épisode", "debut_txt": "Début", "fin_txt": "Fin",
            "duration_calendar_days": "Durée (j calendaires)",
            "critical_day_count": "Jours critiques", "statut_fr": "Statut maximal",
            "deficit_abs": "Déficit estimé (kWh)", "niveau_label": "Gravité maximale",
        },
    )
    fig.update_layout(
        height=240, margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis_title=None,
    )
    fig.update_yaxes(title=None)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"{len(vue)} épisode(s) affiché(s) selon les filtres. Chaque segment est coloré par la "
        "gravité maximale atteinte ; survolez-le pour le détail. La largeur est arrondie au jour "
        "supérieur pour rendre les épisodes courts visibles."
    )

# ------------------------------------------------------------------
# Tableau detaille
# ------------------------------------------------------------------
st.subheader("Tableau des épisodes")

if not vue.empty:
    disp = pd.DataFrame({
        "Épisode": vue["critical_episode_id"],
        "Début": vue["start_date"].dt.strftime("%d/%m/%Y"),
        "Fin": vue["end_date"].dt.strftime("%d/%m/%Y"),
        "Durée (j)": vue["duration_calendar_days"],
        "Jours critiques": vue["critical_day_count"],
        "Gravité max": vue["maximum_anomaly_level"].map(lambda n: f"Niveau {int(n)}"),
        "Statut max": vue["maximum_status"].map(labels.traduire),
        "Écart quotidien moyen (%)": vue["mean_daily_gap_percent"].round(2),
        "Écart 30 j moyen (%)": vue["mean_rolling_30d_gap_percent"].round(2),
        "Déficit estimé (kWh)": vue["estimated_model_relative_shortfall_kwh"].abs().round(0),
        "État": vue["actif"].map(lambda a: "Actif" if a else "Clôturé"),
    })
    st.dataframe(disp, use_container_width=True, hide_index=True, height=520)
    st.caption(
        "« Écart 30 j moyen » correspond à la moyenne glissante 30 jours moyenne sur l'épisode "
        "(le fichier ne contient pas d'écart minimal). Le déficit est une estimation relative "
        "au modèle, en valeur absolue."
    )

# ------------------------------------------------------------------
# Detail d'un episode
# ------------------------------------------------------------------
st.subheader("Détail d'un épisode")

choix = st.selectbox(
    "Épisode à examiner",
    df["critical_episode_id"].tolist(),
    index=len(df) - 1,  # par defaut le plus recent
)
ep = df[df["critical_episode_id"] == choix].iloc[0]
ep_start = pd.Timestamp(ep["start_date"]).normalize()
ep_end = pd.Timestamp(ep["end_date"]).normalize()

st.markdown(
    f"### {choix} — {theme.libelle_niveau(int(ep['maximum_anomaly_level']))}  \n"
    f"**Du {ep_start:%d/%m/%Y} au {ep_end:%d/%m/%Y}** — "
    f"{int(ep['duration_calendar_days'])} jours calendaires, "
    f"{int(ep['critical_day_count'])} jours critiques. État : "
    f"{'actif au dernier jour fiable' if ep['actif'] else 'clôturé'}."
)
d1, d2, d3 = st.columns(3)
d1.metric("Écart quotidien moyen", f"{float(ep['mean_daily_gap_percent']):+.2f} %")
d2.metric("Écart 30 j moyen", f"{float(ep['mean_rolling_30d_gap_percent']):+.2f} %")
d3.metric("Déficit estimé relatif au modèle", _fmt_kwh(ep["estimated_model_relative_shortfall_kwh"]))

st.info(
    "La **température du module** n'est pas disponible dans le jeu de données de monitoring "
    "(les prédictions ne contiennent que l'irradiance globale horizontale et la puissance). "
    "Le détail ci-dessous repose donc sur l'irradiance, la puissance et les écarts."
)

# Sous-ensemble 5 min de l'episode.
opt_jour = st.checkbox("Heures de jour uniquement", value=True, key="ep_jour")
masque = (pred["timestamp"] >= ep_start) & (pred["timestamp"] < ep_end + pd.Timedelta(days=1))
if opt_jour:
    masque = masque & (pred["daylight_flag"] == 1)
fen = pred.loc[masque].sort_values("timestamp")

# Sous-ensemble quotidien de l'episode.
djour = daily[(daily["date"] >= ep_start) & (daily["date"] <= ep_end)].sort_values("date").copy()

if fen.empty:
    st.warning("Aucune observation 5 minutes sur cet épisode (essayez de décocher le filtre jour).")
else:
    tickvals, ticktext = _ticks_episode(fen["timestamp"])

    # Graphique A : puissance mesuree / predite + irradiance (axe secondaire).
    st.markdown("**Puissance mesurée vs prédite, et irradiance**")
    figA = make_subplots(specs=[[{"secondary_y": True}]])
    figA.add_trace(go.Scattergl(
        x=fen["timestamp"], y=fen["Global_Horizontal_Radiation"],
        mode="lines", name="Irradiance (GHI)",
        line=dict(width=1, color="#fbc02d"), opacity=0.5,
    ), secondary_y=True)
    figA.add_trace(go.Scattergl(
        x=fen["timestamp"], y=fen["predicted_active_power_kw"],
        mode="lines", name="Prédite", line=dict(width=1, color="#e53935"),
    ), secondary_y=False)
    figA.add_trace(go.Scattergl(
        x=fen["timestamp"], y=fen["measured_active_power_kw"],
        mode="lines", name="Mesurée", line=dict(width=1, color="#1f77b4"),
    ), secondary_y=False)
    figA.update_layout(
        height=380, margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified", xaxis_title=None,
    )
    figA.update_yaxes(title_text="Puissance (kW)", secondary_y=False)
    figA.update_yaxes(title_text="Irradiance (W/m²)", secondary_y=True, showgrid=False)
    figA.update_xaxes(tickvals=tickvals, ticktext=ticktext)
    st.plotly_chart(figA, use_container_width=True)

    # Graphique B : residu.
    st.markdown("**Résidu (mesurée − prédite)**")
    figB = go.Figure()
    figB.add_trace(go.Scattergl(
        x=fen["timestamp"], y=fen["residual_kw"],
        mode="lines", name="Résidu", line=dict(width=1, color="#6a1b9a"),
    ))
    figB.add_hline(y=0, line_dash="dash", line_width=1.2, line_color="#444444")
    figB.update_layout(
        height=300, margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False, hovermode="x unified", xaxis_title=None, yaxis_title="Résidu (kW)",
    )
    figB.update_xaxes(tickvals=tickvals, ticktext=ticktext)
    st.plotly_chart(figB, use_container_width=True)

# Graphique C : ecart quotidien + moyennes + seuils sur l'episode.
if not djour.empty:
    st.markdown("**Écart énergétique quotidien et moyennes glissantes**")
    ecart_valide = djour["relative_energy_gap_percent"].where(djour["monitoring_valid_day"])
    ecart_invalide = djour["relative_energy_gap_percent"].where(~djour["monitoring_valid_day"])
    tv_d, tt_d = _ticks_episode(djour["date"])

    figC = go.Figure()
    figC.add_trace(go.Scatter(
        x=djour["date"], y=ecart_invalide, mode="markers",
        name="Jour à couverture insuffisante",
        marker=dict(size=6, color="#b0b0b0", opacity=0.7),
    ))
    figC.add_trace(go.Scatter(
        x=djour["date"], y=ecart_valide, mode="markers+lines",
        name="Écart quotidien (jours valides)",
        marker=dict(size=6, color="#1f77b4"), line=dict(width=1, color="#1f77b4"),
        connectgaps=False,
    ))
    figC.add_trace(go.Scatter(
        x=djour["date"], y=djour["rolling_7d_relative_gap_percent"],
        mode="lines", name="Moyenne glissante 7 j", line=dict(width=1.5, color="#fb8c00"),
        connectgaps=False,
    ))
    figC.add_trace(go.Scatter(
        x=djour["date"], y=djour["rolling_30d_relative_gap_percent"],
        mode="lines", name="Moyenne glissante 30 j", line=dict(width=2, color="#8e0000"),
        connectgaps=False,
    ))
    figC.add_hline(y=seuil_jour, line_dash="dot", line_color="#9e9e9e", line_width=1,
                   annotation_text=f"Seuil quotidien {seuil_jour:.2f} %",
                   annotation_position="bottom left")
    figC.add_hline(y=seuil_30j, line_dash="dashdot", line_color="#8e0000", line_width=1,
                   annotation_text=f"Seuil 30 j {seuil_30j:.2f} %",
                   annotation_position="top left")
    figC.update_layout(
        height=360, margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified", xaxis_title=None, yaxis_title="Écart relatif (%)",
    )
    figC.update_xaxes(tickvals=tv_d, ticktext=tt_d)
    st.plotly_chart(figC, use_container_width=True)

    # Graphique D : frise des niveaux quotidiens de l'episode (couverture en survol).
    st.markdown("**Niveau de surveillance jour par jour**")
    djour = djour.copy()
    djour["couverture_pct"] = (djour["daily_coverage_ratio"] * 100).clip(upper=100)
    djour["statut_fr"] = djour["anomaly_status"].map(labels.traduire)

    figD = go.Figure()
    for lvl in sorted(djour["anomaly_level"].unique()):
        sous = djour[djour["anomaly_level"] == lvl]
        survol = (
            "Date : " + sous["date"].dt.strftime("%d/%m/%Y")
            + "<br>Couverture : " + sous["couverture_pct"].round(1).astype(str) + " %"
            + "<br>Niveau : " + theme.libelle_niveau(int(lvl))
            + "<br>Statut : " + sous["statut_fr"].astype(str)
            + "<br>Écart quotidien : " + sous["relative_energy_gap_percent"].round(2).astype(str) + " %"
        )
        figD.add_trace(go.Bar(
            x=sous["date"], y=[1] * len(sous),
            name=theme.libelle_niveau(int(lvl)),
            marker_color=theme.COULEURS.get(int(lvl), "#888888"), marker_line_width=0,
            hovertext=survol, hoverinfo="text",
        ))
    figD.update_layout(
        barmode="stack", bargap=0, height=180, margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    figD.update_yaxes(visible=False, range=[0, 1], fixedrange=True)
    figD.update_xaxes(tickvals=tv_d, ticktext=tt_d)
    st.plotly_chart(figD, use_container_width=True)

st.caption(
    "Sources : 12L_final_critical_anomaly_episodes.csv (épisodes), "
    "model_03_random_forest_final_daily_anomaly_classification.parquet (détail quotidien), "
    "model_03_random_forest_oot_predictions.parquet (détail 5 minutes)."
)
