"""
views/performance_modele.py
Performance et justification du modele de reference.
Le modele definit la production "attendue" : la detection de sous-performance
est RELATIVE a ce modele, donc sa qualite borne la fiabilite de la detection.
Lecture seule. Toutes les valeurs viennent des fichiers du notebook 02.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src import data_loader as dl


def _fmt(x, nd=3):
    try:
        return f"{float(x):.{nd}f}"
    except (TypeError, ValueError):
        return "n/a"


st.title("📊 Performance du modele de reference")
st.caption(
    "Le modele de reference (Random Forest) estime la production attendue a "
    "partir de l'irradiance et de variables temporelles. La detection de "
    "sous-performance est definie RELATIVEMENT a ce modele : sa qualite "
    "conditionne donc la fiabilite des ecarts observes."
)

selection = dl.load_model_selection()
oot = dl.load_oot_metrics()
importance = dl.load_feature_importance()
registry = dl.load_model_registry()

selected_name = registry.get("selected_model_name", "MODEL 3 — Random Forest")
criterion = registry.get("selection_criterion", "RMSE en heures de jour (calibration)")

# --- Modele retenu : metriques cles (calibration) ---
st.subheader("Modele retenu")
st.write("**" + str(selected_name) + "** — critere de selection : " + str(criterion) + ".")

m1, m2, m3 = st.columns(3)
m1.metric("RMSE (jour, calibration)", _fmt(registry.get("selected_daylight_rmse_kw")))
m2.metric("MAE (jour, calibration)", _fmt(registry.get("selected_daylight_mae_kw")))
m3.metric("R2 (jour, calibration)", _fmt(registry.get("selected_daylight_r2")))

# --- Comparaison des 5 modeles (calibration) ---
st.subheader("Comparaison des modeles (calibration)")
comp = selection.sort_values("selection_rank")
couleurs = ["#1f77b4" if m == selected_name else "#c7c7c7" for m in comp["model"]]

figc = go.Figure()
figc.add_trace(go.Bar(
    x=comp["model"], y=comp["daylight_rmse_kw"],
    marker_color=couleurs,
    text=[f"{v:.3f}" for v in comp["daylight_rmse_kw"]],
    textposition="outside",
))
figc.update_layout(
    height=360, margin=dict(l=10, r=10, t=30, b=40),
    yaxis_title="RMSE en heures de jour (kW)", xaxis_title=None,
    showlegend=False,
)
st.plotly_chart(figc, use_container_width=True)
st.caption(
    "Plus le RMSE est faible, meilleur est l'ajustement. Le modele retenu "
    "est mis en evidence en bleu. Selection effectuee sur la calibration "
    "2020-2022, avant toute evaluation out-of-time (modele ensuite fige)."
)

with st.expander("Tableau detaille de la comparaison (calibration)"):
    st.dataframe(comp, use_container_width=True, hide_index=True)

# --- Generalisation out-of-time ---
st.subheader("Generalisation hors echantillon (out-of-time 2023-2025)")
day_row = oot[oot["evaluation_subset"].astype(str).str.contains("day", case=False, na=False)]
row = day_row.iloc[0] if len(day_row) else oot.iloc[0]

o1, o2, o3, o4 = st.columns(4)
o1.metric("MAE (kW)", _fmt(row.get("mae_kw")))
o2.metric("RMSE (kW)", _fmt(row.get("rmse_kw")))
o3.metric("R2", _fmt(row.get("r2")))
obs = row.get("observation_count")
o4.metric("Observations", f"{int(obs):,}".replace(",", " ") if pd.notna(obs) else "n/a")

st.warning(
    "Interpretation prudente : les metriques out-of-time sont calculees sur une "
    "periode qui contient elle-meme la sous-performance detectee. Un R2 plus "
    "faible qu'en calibration melange donc l'erreur propre du modele ET la "
    "derive reelle du systeme — ce n'est pas uniquement une degradation du modele."
)

with st.expander("Metriques out-of-time detaillees (sous-ensembles complet et jour)"):
    st.dataframe(oot, use_container_width=True, hide_index=True)

# --- Importance des variables ---
st.subheader("Importance des variables")
imp = importance.sort_values("importance", ascending=True)

figi = go.Figure()
figi.add_trace(go.Bar(
    x=imp["importance"], y=imp["feature"],
    orientation="h", marker_color="#6a1b9a",
    text=[f"{v:.3f}" for v in imp["importance"]],
    textposition="outside",
))
figi.update_layout(
    height=340, margin=dict(l=10, r=10, t=30, b=10),
    xaxis_title="Importance (Random Forest)", yaxis_title=None,
)
st.plotly_chart(figi, use_container_width=True)
st.caption(
    "Importance des 7 variables d'entree. Une forte dependance a l'irradiance "
    "(Global_Horizontal_Radiation) est attendue physiquement."
)

st.caption(
    "Sources : 12H_final_model_selection_on_calibration.csv, "
    "12I_selected_random_forest_oot_overall_metrics.csv, "
    "12F_model_03_random_forest_feature_importance.csv."
)
