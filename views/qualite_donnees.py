"""views/qualite_donnees.py — Qualite et disponibilite des donnees (V1).

Reconstruit le calendrier complet de la periode d'evaluation et distingue quatre
categories de jours :
  - jours calendaires attendus (toute la periode, jour par jour) ;
  - jours presents dans les resultats du monitoring ;
  - jours valides (couverture >= 80 %) ;
  - jours presents mais a couverture insuffisante (< 80 %) ;
  - jours totalement absents (aucune donnee).

Lecture seule. Tout est calcule dynamiquement a partir de la table quotidienne :
aucun effectif n'est code en dur.
"""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from src import data_loader as dl

# Couverture : 288 observations theoriques par jour (pas de 5 minutes -> 24*60/5).
OBS_THEORIQUES_PAR_JOUR = 288
SEUIL_COUVERTURE = 80.0  # %

# Code couleur PROPRE A CETTE PAGE (disponibilite des donnees).
C_VALIDE = "#2e7d32"       # vert : jour valide
C_INSUFFISANT = "#b0b0b0"  # gris : present mais couverture insuffisante
C_ABSENT = "#e53935"       # rouge : totalement absent (aucune donnee)


def _ticks_mensuels(dates):
    if len(dates) == 0:
        return [], []
    dmin = pd.Timestamp(dates.min()).normalize().replace(day=1)
    dmax = pd.Timestamp(dates.max()).normalize()
    mois = pd.date_range(dmin, dmax, freq="MS")
    return list(mois), [m.strftime("%m/%Y") for m in mois]


st.title("🗓️ Qualité des données")
st.caption(
    "Disponibilité et couverture des données sur la période d'évaluation. La couverture "
    f"d'une journée vaut 100 × (horodatages uniques) / {OBS_THEORIQUES_PAR_JOUR}, soit la "
    f"part des {OBS_THEORIQUES_PAR_JOUR} relevés théoriques (pas de 5 minutes). Une journée "
    f"est considérée comme valide lorsque sa couverture atteint au moins {SEUIL_COUVERTURE:.0f} %."
)

# ------------------------------------------------------------------
# Donnees et reconstruction du calendrier complet
# ------------------------------------------------------------------
daily = dl.load_daily_classification()
d = daily.sort_values("date").copy()

cal_debut = pd.Timestamp(d["date"].min()).normalize()
cal_fin = pd.Timestamp(d["date"].max()).normalize()
calendrier = pd.date_range(cal_debut, cal_fin, freq="D")

# Fusion calendrier complet <- table quotidienne (les jours absents auront NaN).
cal_df = pd.DataFrame({"date": calendrier})
m = cal_df.merge(
    d[["date", "daily_coverage_ratio", "monitoring_valid_day"]],
    on="date", how="left",
)
m["present"] = m["daily_coverage_ratio"].notna()
m["valide"] = m["present"] & m["monitoring_valid_day"].fillna(False).astype(bool)
m["insuffisant"] = m["present"] & (~m["valide"])
m["absent"] = ~m["present"]
# Couverture en %, plafonnee a 100 (les doublons ne depassent pas 100 %).
m["couverture_pct"] = (m["daily_coverage_ratio"] * 100).clip(upper=100)

# Effectifs (tous dynamiques).
attendus = int(len(m))
presents = int(m["present"].sum())
valides = int(m["valide"].sum())
insuffisants = int(m["insuffisant"].sum())
absents = int(m["absent"].sum())

taux_present = (valides / presents * 100) if presents else 0.0
taux_calendaire = (valides / attendus * 100) if attendus else 0.0

# ------------------------------------------------------------------
# Indicateurs
# ------------------------------------------------------------------
st.subheader("Décompte des journées")
st.markdown(
    f"Période reconstruite : du **{cal_debut:%d/%m/%Y}** au **{cal_fin:%d/%m/%Y}**."
)

a1, a2, a3 = st.columns(3)
a1.metric("Jours calendaires attendus", f"{attendus}")
a2.metric("Jours présents dans les résultats", f"{presents}")
a3.metric("Jours totalement absents", f"{absents}")

b1, b2 = st.columns(2)
b1.metric("Jours valides (couverture ≥ 80 %)", f"{valides}")
b2.metric("Jours présents mais insuffisants (< 80 %)", f"{insuffisants}")

st.markdown(
    f"**Deux taux de jours valides, selon le dénominateur retenu :**  \n"
    f"- **{taux_present:.1f} %** rapporté aux **{presents}** jours présents dans les résultats "
    f"({valides} / {presents}) ;  \n"
    f"- **{taux_calendaire:.1f} %** rapporté aux **{attendus}** jours calendaires attendus "
    f"({valides} / {attendus}).  \n"
    "Le second taux est plus prudent : il considère qu'un jour totalement absent est, lui aussi, "
    "un jour sans information de monitoring exploitable."
)

# ------------------------------------------------------------------
# Couverture quotidienne reconstituee
# ------------------------------------------------------------------
st.subheader("Couverture quotidienne reconstituée")

jours_valides = m[m["valide"]]
jours_insuff = m[m["insuffisant"]]
jours_absents = m[m["absent"]]

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=jours_valides["date"], y=jours_valides["couverture_pct"],
    mode="markers", name="Jour valide (≥ 80 %)",
    marker=dict(size=4, color=C_VALIDE, opacity=0.75),
))
fig.add_trace(go.Scatter(
    x=jours_insuff["date"], y=jours_insuff["couverture_pct"],
    mode="markers", name="Jour présent, couverture insuffisante (< 80 %)",
    marker=dict(size=4, color=C_INSUFFISANT, opacity=0.8),
))
fig.add_trace(go.Scatter(
    x=jours_absents["date"], y=[0] * len(jours_absents),
    mode="markers", name="Jour totalement absent (aucune donnée)",
    marker=dict(size=7, color=C_ABSENT, symbol="x"),
))
fig.add_hline(
    y=SEUIL_COUVERTURE, line_dash="dash", line_color="#444444", line_width=1.2,
    annotation_text=f"Seuil de validité {SEUIL_COUVERTURE:.0f} %",
    annotation_position="bottom right",
)
tv, tt = _ticks_mensuels(m["date"])
fig.update_layout(
    height=420, margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    hovermode="x unified", xaxis_title=None, yaxis_title="Couverture (%)",
)
fig.update_yaxes(range=[-5, 105])
fig.update_xaxes(tickvals=tv, ticktext=tt)
st.plotly_chart(fig, use_container_width=True)
st.caption(
    "Les couleurs décrivent la disponibilité des données, et non la sévérité d'une anomalie. "
    "Un jour totalement absent (croix rouge) est distinct d'un jour présent à très faible "
    "couverture (point gris) : le premier ne figure pas du tout dans les résultats."
)

# ------------------------------------------------------------------
# Repartition mensuelle
# ------------------------------------------------------------------
st.subheader("Répartition mensuelle des journées")

m["ym"] = m["date"].dt.to_period("M")
grp = m.groupby("ym", sort=True)
mois = pd.DataFrame({
    "valide": grp["valide"].sum(),
    "insuffisant": grp["insuffisant"].sum(),
    "absent": grp["absent"].sum(),
    "attendus": grp.size(),
}).reset_index()
mois["label"] = mois["ym"].dt.strftime("%m/%Y")

fig_m = go.Figure()
fig_m.add_trace(go.Bar(
    x=mois["label"], y=mois["valide"], name="Jours valides", marker_color=C_VALIDE,
))
fig_m.add_trace(go.Bar(
    x=mois["label"], y=mois["insuffisant"], name="Jours insuffisants", marker_color=C_INSUFFISANT,
))
fig_m.add_trace(go.Bar(
    x=mois["label"], y=mois["absent"], name="Jours absents", marker_color=C_ABSENT,
    marker_pattern_shape="/",
))
fig_m.update_layout(
    barmode="stack", height=420, margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    xaxis_title=None, yaxis_title="Nombre de jours", xaxis_type="category",
)
st.plotly_chart(fig_m, use_container_width=True)

dernier_mois = mois["label"].iloc[-1]
st.caption(
    f"Chaque barre totalise le nombre de jours calendaires attendus du mois. Le dernier mois "
    f"({dernier_mois}) est partiel : la période d'évaluation s'arrête au {cal_fin:%d/%m/%Y}, "
    f"sa barre ne compte donc que les jours jusqu'à cette date."
)

with st.expander("Tableau mensuel détaillé"):
    table = mois[["label", "attendus", "valide", "insuffisant", "absent"]].rename(columns={
        "label": "Mois", "attendus": "Attendus", "valide": "Valides",
        "insuffisant": "Insuffisants", "absent": "Absents",
    })
    st.dataframe(table, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------
# Avertissement
# ------------------------------------------------------------------
st.warning(
    "Une journée à couverture insuffisante ou totalement absente n'est ni normale ni anormale "
    "du point de vue de la performance : elle traduit une indisponibilité des données. Ces "
    "journées ne sont pas classées sur l'échelle de sous-performance et interrompent les "
    "séquences de persistance (elles ne prolongent pas un épisode et n'en démarrent pas un)."
)

st.caption(
    "Source : model_03_random_forest_final_daily_anomaly_classification.parquet "
    "(colonnes date, daily_coverage_ratio, monitoring_valid_day), calendrier reconstruit à l'affichage."
)
