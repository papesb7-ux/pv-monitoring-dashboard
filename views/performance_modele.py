"""views/performance_modele.py — Performance et justification du modele de reference (V1).

Le modele de reference (Random Forest) estime la puissance attendue au meme instant.
La detection de sous-performance est RELATIVE a ce modele : sa qualite conditionne
la fiabilite des ecarts observes. Le modele reste GELE apres la calibration : aucune
selection ni reglage n'est refait en fonction des resultats 2023-2025.

Lecture seule. Les metriques annuelles, le nuage et la distribution des residus sont
des agregations des predictions existantes (oot_predictions), pas un reentrainement.
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from src import data_loader as dl


def _fmt(x, nd=3):
    try:
        return f"{float(x):.{nd}f}"
    except (TypeError, ValueError):
        return "n/a"


def _metriques(sub):
    """MAE, RMSE, R2, residu moyen sur un sous-ensemble (mesure vs prediction)."""
    if len(sub) == 0:
        return dict(n=0, mae=np.nan, rmse=np.nan, r2=np.nan, res=np.nan)
    y = sub["measured_active_power_kw"].to_numpy(dtype=float)
    p = sub["predicted_active_power_kw"].to_numpy(dtype=float)
    err = y - p
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    ss_res = float(np.sum(err ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else np.nan
    return dict(n=len(sub), mae=mae, rmse=rmse, r2=r2, res=float(err.mean()))


st.title("📊 Performance du modèle de référence")
st.caption(
    "Le modèle de référence (Random Forest) estime la puissance attendue au même instant, "
    "à partir de l'irradiance et des variables disponibles. La détection de sous-performance "
    "est définie RELATIVEMENT à ce modèle : sa qualité conditionne la fiabilité des écarts observés."
)

selection = dl.load_model_selection()
oot = dl.load_oot_metrics()
importance = dl.load_feature_importance()
registry = dl.load_model_registry()
pred = dl.load_oot_predictions()

selected_name = registry.get("selected_model_name", "MODEL 3 — Random Forest")

# ------------------------------------------------------------------
# Modele retenu (calibration)
# ------------------------------------------------------------------
st.subheader("Modèle retenu")
st.markdown(
    f"**{selected_name}.** Critère principal : **RMSE diurne minimal sur la calibration "
    "2020–2022**. En cas de performances proches, le RMSE sur l'ensemble des observations "
    "et la MAE diurne sont utilisés comme critères secondaires. Le modèle est ensuite **gelé** : "
    "il n'est ni réentraîné ni recalibré sur la période d'évaluation."
)

cal_mae = registry.get("selected_daylight_mae_kw")
cal_rmse = registry.get("selected_daylight_rmse_kw")
cal_r2 = registry.get("selected_daylight_r2")

m1, m2, m3 = st.columns(3)
m1.metric("RMSE diurne — calibration", _fmt(cal_rmse))
m2.metric("MAE diurne — calibration", _fmt(cal_mae))
m3.metric("R² diurne — calibration", _fmt(cal_r2))

# ------------------------------------------------------------------
# Comparaison des modeles (calibration)
# ------------------------------------------------------------------
st.subheader("Comparaison des modèles (calibration)")
comp = selection.sort_values("selection_rank")
couleurs = ["#1f77b4" if m == selected_name else "#c7c7c7" for m in comp["model"]]
figc = go.Figure()
figc.add_trace(go.Bar(
    x=comp["model"], y=comp["daylight_rmse_kw"], marker_color=couleurs,
    text=[f"{v:.3f}" for v in comp["daylight_rmse_kw"]], textposition="outside",
))
figc.update_layout(
    height=360, margin=dict(l=10, r=10, t=30, b=40),
    yaxis_title="RMSE diurne (kW)", xaxis_title=None, showlegend=False,
)
st.plotly_chart(figc, use_container_width=True)
st.caption(
    "Plus le RMSE diurne est faible, meilleur est l'ajustement. Le modèle retenu est en bleu. "
    "Sélection effectuée sur la calibration 2020–2022, avant toute évaluation temporelle."
)
with st.expander("Tableau détaillé de la comparaison (calibration)"):
    st.dataframe(comp, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------
# Generalisation out-of-time
# ------------------------------------------------------------------
st.subheader("Évaluation temporelle out-of-time post-sélection — 2023–2025")
st.caption(
    "Cette période a déjà été examinée pendant l'analyse exploratoire et ne constitue donc "
    "pas un test totalement aveugle. Les métriques ci-dessous portent sur le sous-ensemble diurne."
)

day_row = oot[oot["evaluation_subset"].astype(str).str.contains("day", case=False, na=False)]
row = day_row.iloc[0] if len(day_row) else oot.iloc[0]

o1, o2, o3, o4 = st.columns(4)
o1.metric("MAE diurne (kW)", _fmt(row.get("mae_kw")))
o2.metric("RMSE diurne (kW)", _fmt(row.get("rmse_kw")))
o3.metric("R² diurne", _fmt(row.get("r2")))
obs = row.get("observation_count")
o4.metric("Observations", f"{int(obs):,}".replace(",", " ") if pd.notna(obs) else "n/a")

# Comparaison calibration vs OOT (MAE, RMSE, R2).
oot_mae = float(row.get("mae_kw"))
oot_rmse = float(row.get("rmse_kw"))
oot_r2 = float(row.get("r2"))
hausse_rmse = (oot_rmse / float(cal_rmse) - 1) * 100 if cal_rmse else np.nan

st.markdown("**Calibration 2020–2022 vs évaluation temporelle 2023–2025 (diurne)**")
figcmp = go.Figure()
figcmp.add_trace(go.Bar(
    name="Calibration 2020–2022", x=["MAE", "RMSE", "R²"],
    y=[float(cal_mae), float(cal_rmse), float(cal_r2)], marker_color="#1f77b4",
    text=[_fmt(cal_mae), _fmt(cal_rmse), _fmt(cal_r2)], textposition="outside",
))
figcmp.add_trace(go.Bar(
    name="Évaluation 2023–2025", x=["MAE", "RMSE", "R²"],
    y=[oot_mae, oot_rmse, oot_r2], marker_color="#e53935",
    text=[_fmt(oot_mae), _fmt(oot_rmse), _fmt(oot_r2)], textposition="outside",
))
figcmp.update_layout(
    barmode="group", height=360, margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    yaxis_title=None, xaxis_title=None,
)
st.plotly_chart(figcmp, use_container_width=True)

if pd.notna(hausse_rmse):
    st.metric("Augmentation du RMSE diurne (calibration → évaluation)", f"+{hausse_rmse:.1f} %")

st.warning(
    "La différence entre calibration et évaluation temporelle combine l'erreur de "
    "généralisation du modèle ET la sous-performance relative du système. Elle ne doit pas "
    "être attribuée uniquement à une dégradation du modèle."
)
with st.expander("Métriques out-of-time détaillées (sous-ensembles complet et diurne)"):
    st.dataframe(oot, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------
# Nuage mesure / predite (diurne + complet, echantillonne)
# ------------------------------------------------------------------
st.subheader("Nuage des points : puissance mesurée vs prédite")
sous_ensemble = st.radio(
    "Sous-ensemble", ["Diurne", "Complet"], horizontal=True, key="nuage_sub"
)
base = pred[pred["daylight_flag"] == 1] if sous_ensemble == "Diurne" else pred
n_max = 8000
echant = base.sample(n=min(n_max, len(base)), random_state=42) if len(base) > n_max else base

vmax = float(max(echant["measured_active_power_kw"].max(),
                 echant["predicted_active_power_kw"].max()))
fig_sc = go.Figure()
fig_sc.add_trace(go.Scattergl(
    x=echant["predicted_active_power_kw"], y=echant["measured_active_power_kw"],
    mode="markers", marker=dict(size=3, color="#1f77b4", opacity=0.35), name="Observations",
))
fig_sc.add_trace(go.Scattergl(
    x=[0, vmax], y=[0, vmax], mode="lines",
    line=dict(color="#e53935", width=1.5, dash="dash"), name="y = x",
))
fig_sc.update_layout(
    height=460, margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    xaxis_title="Puissance prédite (kW)", yaxis_title="Puissance mesurée (kW)",
)
st.plotly_chart(fig_sc, use_container_width=True)
st.caption(
    f"Sous-ensemble {sous_ensemble.lower()} — échantillon reproductible de "
    f"{len(echant):,}".replace(",", " ") + " points. Les points sous la diagonale y = x "
    "correspondent à une puissance mesurée inférieure à la prédiction."
)

# ------------------------------------------------------------------
# Distribution des residus (diurne + complet)
# ------------------------------------------------------------------
st.subheader("Distribution des résidus")
sous_ensemble_r = st.radio(
    "Sous-ensemble ", ["Diurne", "Complet"], horizontal=True, key="resid_sub"
)
base_r = pred[pred["daylight_flag"] == 1] if sous_ensemble_r == "Diurne" else pred
res = base_r["residual_kw"].to_numpy(dtype=float)
moy = float(np.mean(res))
med = float(np.median(res))

fig_h = go.Figure()
fig_h.add_trace(go.Histogram(x=res, nbinsx=80, marker_color="#6a1b9a", name="Résidu"))
fig_h.add_vline(x=0, line_dash="dash", line_color="#444444", line_width=1.2)
fig_h.add_vline(x=moy, line_dash="dot", line_color="#1f77b4", line_width=1.5,
                annotation_text=f"Moyenne {moy:+.3f}", annotation_position="top right")
fig_h.add_vline(x=med, line_dash="dot", line_color="#2e7d32", line_width=1.5,
                annotation_text=f"Médiane {med:+.3f}", annotation_position="top left")
fig_h.update_layout(
    height=360, margin=dict(l=10, r=10, t=30, b=10), showlegend=False,
    xaxis_title="Résidu (kW)", yaxis_title="Nombre d'observations",
)
st.plotly_chart(fig_h, use_container_width=True)
st.caption(
    f"Sous-ensemble {sous_ensemble_r.lower()}. Moyenne {moy:+.3f} kW, médiane {med:+.3f} kW. "
    "Un centre décalé vers les valeurs négatives traduit une sous-performance relative au modèle."
)

# ------------------------------------------------------------------
# Metriques annuelles (diurne + complet)
# ------------------------------------------------------------------
st.subheader("Métriques par année")
st.caption(
    "Calculées à partir des prédictions out-of-time (agrégation, pas de réentraînement). "
    "L'année 2025 est partielle (arrêtée fin août)."
)

lignes = []
for an in sorted(pred["year"].unique()):
    sous_an = pred[pred["year"] == an]
    diurne = _metriques(sous_an[sous_an["daylight_flag"] == 1])
    complet = _metriques(sous_an)
    label_an = f"{int(an)} (partielle)" if int(an) == int(pred["year"].max()) else f"{int(an)}"
    lignes.append({
        "Année": label_an,
        "MAE diurne": _fmt(diurne["mae"]),
        "RMSE diurne": _fmt(diurne["rmse"]),
        "R² diurne": _fmt(diurne["r2"]),
        "Résidu moyen diurne": _fmt(diurne["res"]),
        "MAE complet": _fmt(complet["mae"]),
        "RMSE complet": _fmt(complet["rmse"]),
        "R² complet": _fmt(complet["r2"]),
    })
st.dataframe(pd.DataFrame(lignes), use_container_width=True, hide_index=True)
st.caption(
    "Le R² complet inclut les heures de nuit (mesurée ≈ prédite ≈ 0) : il est proche de 1 et "
    "peu informatif. Le sous-ensemble diurne est l'indicateur pertinent pour la performance."
)

# ------------------------------------------------------------------
# Importance interne des variables
# ------------------------------------------------------------------
st.subheader("Importance interne des variables du Random Forest")
imp = importance.sort_values("importance", ascending=True)
figi = go.Figure()
figi.add_trace(go.Bar(
    x=imp["importance"], y=imp["feature"], orientation="h", marker_color="#6a1b9a",
    text=[f"{v:.3f}" for v in imp["importance"]], textposition="outside",
))
figi.update_layout(
    height=340, margin=dict(l=10, r=10, t=30, b=10),
    xaxis_title="Importance (réduction d'impureté)", yaxis_title=None,
)
st.plotly_chart(figi, use_container_width=True)
st.info(
    "Ces importances sont fondées sur la réduction d'impureté des arbres. Elles décrivent "
    "l'utilisation des variables par le modèle, mais ne mesurent pas leur effet causal. "
    "Global_Horizontal_Radiation et ghi_squared étant fortement corrélées, leurs importances "
    "doivent être interprétées conjointement. Une importance interne faible (par exemple "
    "daylight_flag) ne signifie pas que la variable est inutile."
)

st.caption(
    "Sources : 12H_final_model_selection_on_calibration.csv, "
    "12I_selected_random_forest_oot_overall_metrics.csv, "
    "12F_model_03_random_forest_feature_importance.csv, "
    "model_03_random_forest_oot_predictions.parquet."
)
