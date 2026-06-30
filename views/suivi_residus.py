"""views/suivi_residus.py — Suivi des residus (V1).

Trace, sur la periode out-of-time 2023-2025 :
  - la puissance mesuree vs predite et le residu, au pas de 5 minutes ;
  - le monitoring quotidien (energie mesuree/predite, ecart, seuil) ;
  - la surveillance de la persistance (ecart + moyennes glissantes 7j/30j + seuils).

Lecture seule. Aucun calcul d'anomalie ici : tout provient des fichiers du notebook.
Convention : residu = puissance mesuree - puissance predite.
Un residu negatif = puissance mesuree inferieure a l'attendu du modele.
"""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from src import data_loader as dl

# Limite de la vue detaillee 5 min, et largeur par defaut.
MAX_JOURS_5MIN = 30
DEFAUT_JOURS_5MIN = 7


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _ticks_mensuels(dates):
    """Graduations mensuelles etiquetees MM/AAAA (dates francaises sur l'axe x)."""
    if len(dates) == 0:
        return [], []
    dmin = pd.Timestamp(dates.min()).normalize().replace(day=1)
    dmax = pd.Timestamp(dates.max()).normalize()
    mois = pd.date_range(dmin, dmax, freq="MS")
    return list(mois), [m.strftime("%m/%Y") for m in mois]


def _ticks_journaliers(dates):
    """Graduations journalieres etiquetees JJ/MM pour une vue courte (<= 30 jours)."""
    if len(dates) == 0:
        return [], []
    dmin = pd.Timestamp(dates.min()).normalize()
    dmax = pd.Timestamp(dates.max()).normalize()
    jours = pd.date_range(dmin, dmax, freq="D")
    # Limiter le nombre d'etiquettes pour rester lisible.
    pas = max(1, len(jours) // 12)
    jours = jours[::pas]
    return list(jours), [j.strftime("%d/%m") for j in jours]


def _seuil(thresholds, mot_cle):
    """Lit un seuil dans 12J via un mot-cle de l'indicateur (jamais code en dur)."""
    ligne = thresholds[thresholds["indicator"].str.contains(mot_cle, case=False, na=False)]
    return float(ligne["threshold_percent"].iloc[0])


# ------------------------------------------------------------------
# En-tete
# ------------------------------------------------------------------
st.title("📉 Suivi des résidus")
st.caption(
    "Puissance mesurée vs puissance prédite par le modèle de référence, et résidu "
    "(mesurée − prédite) au pas de 5 minutes. Un résidu négatif signifie une puissance "
    "mesurée inférieure à l'attendu du modèle."
)

st.warning(
    "Un résidu négatif isolé ne constitue pas une anomalie. La classification repose "
    "sur l'écart énergétique quotidien, les seuils calibrés et la persistance temporelle."
)

# ------------------------------------------------------------------
# Donnees
# ------------------------------------------------------------------
pred = dl.load_oot_predictions()
daily = dl.load_daily_classification()
thresholds = dl.load_thresholds()

seuil_jour = _seuil(thresholds, "Daily")
seuil_7j = _seuil(thresholds, "7-day")
seuil_30j = _seuil(thresholds, "30-day")

# Dernier jour FIABLE (jour valide) = borne par defaut de la vue detaillee.
jours_valides = daily.loc[daily["monitoring_valid_day"], "date"]
dernier_fiable = pd.Timestamp(jours_valides.max()).normalize()

date_min_data = pred["timestamp"].min().normalize()
date_max_data = pred["timestamp"].max().normalize()

# ==================================================================
# 1) VUE DETAILLEE 5 MINUTES
# ==================================================================
st.header("Vue détaillée au pas de 5 minutes")

defaut_debut = max(date_min_data, dernier_fiable - pd.Timedelta(days=DEFAUT_JOURS_5MIN - 1))

col_dates, col_jour = st.columns([3, 1])
with col_dates:
    selection = st.date_input(
        "Plage de dates (vue détaillée — 30 jours maximum)",
        value=(defaut_debut.date(), dernier_fiable.date()),
        min_value=date_min_data.date(),
        max_value=date_max_data.date(),
        format="DD/MM/YYYY",
    )
with col_jour:
    jour_seulement = st.checkbox("Heures de jour uniquement", value=True)

if not (isinstance(selection, (tuple, list)) and len(selection) == 2):
    st.info("Sélectionne une date de début ET une date de fin.")
    st.stop()

start_date, end_date = selection
if start_date > end_date:
    st.warning("La date de début est postérieure à la date de fin.")
    st.stop()

# Limite de 30 jours pour la vue 5 min.
nb_jours_selection = (pd.Timestamp(end_date) - pd.Timestamp(start_date)).days + 1
if nb_jours_selection > MAX_JOURS_5MIN:
    st.warning(
        f"La vue détaillée 5 minutes est limitée à {MAX_JOURS_5MIN} jours "
        f"(sélection actuelle : {nb_jours_selection} jours). Réduis la plage, ou consulte "
        "la section « Monitoring quotidien » plus bas pour une vue agrégée sur toute la période."
    )
    st.stop()

# Avertissement si le dernier jour observe (couverture insuffisante) est inclus.
if pd.Timestamp(end_date).normalize() > dernier_fiable:
    cov = daily.loc[daily["date"] == date_max_data, "daily_coverage_ratio"]
    cov_txt = f" (≈ {float(cov.iloc[0]) * 100:.2f} %)" if len(cov) else ""
    st.warning(
        f"La plage inclut le {date_max_data:%d/%m/%Y}, dont la couverture est insuffisante"
        f"{cov_txt} (DATA_INSUFFICIENT). Ce jour n'est pas interprété comme une anomalie de "
        f"production. Le dernier jour fiable est le {dernier_fiable:%d/%m/%Y}."
    )

masque = (pred["timestamp"].dt.date >= start_date) & (pred["timestamp"].dt.date <= end_date)
if jour_seulement:
    masque = masque & (pred["daylight_flag"] == 1)
fenetre = pred.loc[masque].sort_values("timestamp")

if fenetre.empty:
    st.warning("Aucune donnée sur cette plage (élargis la plage, ou décoche le filtre jour).")
    st.stop()

# Indicateurs de la fenetre.
c1, c2, c3, c4 = st.columns(4)
c1.metric("Points affichés", f"{len(fenetre):,}".replace(",", " "))
c2.metric("Résidu moyen (kW)", f"{fenetre['residual_kw'].mean():+.3f}")
c3.metric("Résidu médian (kW)", f"{fenetre['residual_kw'].median():+.3f}")
part_negatif = float((fenetre["residual_kw"] < 0).mean() * 100)
c4.metric("Observations avec résidu négatif", f"{part_negatif:.0f} %")

tickvals, ticktext = _ticks_journaliers(fenetre["timestamp"])

# Graphique mesure vs predite (avec zone d'ecart).
st.subheader("Puissance mesurée vs puissance prédite")
fig_p = go.Figure()
fig_p.add_trace(go.Scattergl(
    x=fenetre["timestamp"], y=fenetre["predicted_active_power_kw"],
    mode="lines", name="Prédite", line=dict(width=1, color="#e53935"),
))
fig_p.add_trace(go.Scattergl(
    x=fenetre["timestamp"], y=fenetre["measured_active_power_kw"],
    mode="lines", name="Mesurée", line=dict(width=1, color="#1f77b4"),
    fill="tonexty", fillcolor="rgba(229,57,53,0.10)",
))
fig_p.update_layout(
    height=380, margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified", xaxis_title=None, yaxis_title="Puissance (kW)",
)
fig_p.update_xaxes(tickvals=tickvals, ticktext=ticktext)
st.plotly_chart(fig_p, use_container_width=True)

# Graphique residu.
st.subheader("Résidu (mesurée − prédite)")
fig_r = go.Figure()
fig_r.add_trace(go.Scattergl(
    x=fenetre["timestamp"], y=fenetre["residual_kw"],
    mode="lines", name="Résidu", line=dict(width=1, color="#6a1b9a"),
))
fig_r.add_hline(y=0, line_dash="dash", line_width=1.2, line_color="#444444")
fig_r.update_layout(
    height=320, margin=dict(l=10, r=10, t=10, b=10),
    showlegend=False, hovermode="x unified", xaxis_title=None, yaxis_title="Résidu (kW)",
)
fig_r.update_xaxes(tickvals=tickvals, ticktext=ticktext)
st.plotly_chart(fig_r, use_container_width=True)

st.caption(
    "Source : model_03_random_forest_oot_predictions.parquet. "
    "Résidu = puissance mesurée − puissance prédite."
)

# ==================================================================
# 2) MONITORING QUOTIDIEN (toute la periode)
# ==================================================================
st.header("Monitoring quotidien")
st.caption(
    "Vue agrégée sur toute la période. L'écart quotidien relatif est défini par "
    "100 × (énergie mesurée − énergie prédite) / énergie prédite."
)

d = daily.sort_values("date").copy()
valide = d["monitoring_valid_day"].to_numpy()

# Energie mesuree vs predite.
st.subheader("Énergie quotidienne mesurée vs prédite")
fig_e = go.Figure()
fig_e.add_trace(go.Scatter(
    x=d["date"], y=d["predicted_energy_kwh"],
    mode="lines", name="Énergie prédite", line=dict(width=1.3, color="#e53935"),
    connectgaps=False,
))
fig_e.add_trace(go.Scatter(
    x=d["date"], y=d["measured_energy_kwh"],
    mode="lines", name="Énergie mesurée", line=dict(width=1.3, color="#1f77b4"),
    connectgaps=False,
))
tv_m, tt_m = _ticks_mensuels(d["date"])
fig_e.update_layout(
    height=340, margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified", xaxis_title=None, yaxis_title="Énergie (kWh)",
)
fig_e.update_xaxes(tickvals=tv_m, ticktext=tt_m)
st.plotly_chart(fig_e, use_container_width=True)

# Ecart quotidien : jours valides en couleur, jours insuffisants en gris.
st.subheader("Écart énergétique quotidien")
ecart_valide = d["relative_energy_gap_percent"].where(d["monitoring_valid_day"])
ecart_invalide = d["relative_energy_gap_percent"].where(~d["monitoring_valid_day"])

fig_g = go.Figure()
fig_g.add_trace(go.Scatter(
    x=d["date"], y=ecart_invalide,
    mode="markers", name="Jour à couverture insuffisante",
    marker=dict(size=4, color="#b0b0b0", opacity=0.6),
))
fig_g.add_trace(go.Scatter(
    x=d["date"], y=ecart_valide,
    mode="markers", name="Jour valide",
    marker=dict(size=4, color="#1f77b4", opacity=0.7),
))
fig_g.add_hline(
    y=seuil_jour, line_dash="dot", line_color="#9e9e9e", line_width=1.2,
    annotation_text=f"Seuil quotidien {seuil_jour:.2f} %", annotation_position="bottom right",
)
fig_g.update_layout(
    height=340, margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified", xaxis_title=None, yaxis_title="Écart relatif (%)",
)
fig_g.update_xaxes(tickvals=tv_m, ticktext=tt_m)
st.plotly_chart(fig_g, use_container_width=True)

# ==================================================================
# 3) SURVEILLANCE DE LA PERSISTANCE
# ==================================================================
st.header("Surveillance de la persistance")
st.caption(
    "Les moyennes glissantes permettent de distinguer une fluctuation ponctuelle "
    "d'une sous-performance soutenue ou persistante."
)

# Mettre les ecarts a NaN sur les jours invalides : pas de liaison artificielle.
ecart_j_serie = d["relative_energy_gap_percent"].where(d["monitoring_valid_day"])

fig_p2 = go.Figure()
fig_p2.add_trace(go.Scatter(
    x=d["date"], y=ecart_j_serie,
    mode="markers", name="Écart quotidien (jours valides)",
    marker=dict(size=3, color="#b0b0b0", opacity=0.45),
))
fig_p2.add_trace(go.Scatter(
    x=d["date"], y=d["rolling_7d_relative_gap_percent"],
    mode="lines", name="Moyenne glissante 7 j",
    line=dict(width=1.5, color="#1f77b4"), connectgaps=False,
))
fig_p2.add_trace(go.Scatter(
    x=d["date"], y=d["rolling_30d_relative_gap_percent"],
    mode="lines", name="Moyenne glissante 30 j",
    line=dict(width=2, color="#6a1b9a"), connectgaps=False,
))
fig_p2.add_hline(y=seuil_jour, line_dash="dot", line_color="#9e9e9e", line_width=1,
                 annotation_text=f"Seuil quotidien {seuil_jour:.2f} %",
                 annotation_position="top right")
fig_p2.add_hline(y=seuil_7j, line_dash="dash", line_color="#1f77b4", line_width=1,
                 annotation_text=f"Seuil 7 j {seuil_7j:.2f} %",
                 annotation_position="bottom right")
fig_p2.add_hline(y=seuil_30j, line_dash="dashdot", line_color="#6a1b9a", line_width=1,
                 annotation_text=f"Seuil 30 j {seuil_30j:.2f} %",
                 annotation_position="bottom left")
fig_p2.update_layout(
    height=420, margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified", xaxis_title=None, yaxis_title="Écart relatif (%)",
)
fig_p2.update_xaxes(tickvals=tv_m, ticktext=tt_m)
st.plotly_chart(fig_p2, use_container_width=True)

st.caption(
    "Seuils (5ᵉ percentile, calibration 2020–2022, lus dans 12J_residual_monitoring_thresholds.csv) : "
    f"quotidien {seuil_jour:.2f} %, 7 j {seuil_7j:.2f} %, 30 j {seuil_30j:.2f} %. "
    "Les interruptions des courbes correspondent à des journées invalides ou manquantes ; "
    "elles ne représentent pas une performance nulle."
)
