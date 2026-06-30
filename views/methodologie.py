"""views/methodologie.py — Methodologie et cadrage du dispositif de monitoring (V1).

Page de reference, essentiellement textuelle (st.markdown + st.latex). Elle definit le
perimetre, le vocabulaire, les definitions formelles et les limites d'interpretation.
Les seuils sont lus dans le fichier de calibration ; aucune autre valeur n'est calculee.
Lecture seule.
"""

import streamlit as st

from src import data_loader as dl

OBS_THEORIQUES_PAR_JOUR = 288
SEUIL_COUVERTURE = 80


def _seuil(thresholds, mot_cle):
    ligne = thresholds[thresholds["indicator"].str.contains(mot_cle, case=False, na=False)]
    return float(ligne["threshold_percent"].iloc[0])


st.title("📘 Méthodologie et cadrage")
st.caption(
    "Cette page précise ce que le dispositif mesure, ce qu'il ne mesure pas, et les "
    "précautions d'interprétation. Elle sert de référence pour la lecture de toutes les "
    "autres pages."
)

thresholds = dl.load_thresholds()
seuil_jour = _seuil(thresholds, "Daily")
seuil_7j = _seuil(thresholds, "7-day")
seuil_30j = _seuil(thresholds, "30-day")

# ------------------------------------------------------------------
st.subheader("Principe général")
st.markdown(
    "Le dispositif compare la production électrique **mesurée** d'un système photovoltaïque "
    "à une production **attendue**, estimée par un modèle de référence. L'écart entre les "
    "deux — le **résidu** — est suivi dans le temps. Une dérive persistante de cet écart vers "
    "des valeurs négatives constitue un signalement de **sous-performance relative au modèle**. "
    "Le tableau de bord indique *où* et *quand* la production s'écarte de l'attendu ; il ne "
    "détermine pas *pourquoi*."
)

# ------------------------------------------------------------------
st.subheader("Jeu de données et son rôle")
st.markdown(
    "- **Source** : DKASC (Desert Knowledge Australia Solar Centre), Alice Springs, Australie. "
    "Données publiques au pas de 5 minutes.\n"
    "- **Rôle** : DKASC sert de **terrain d'essai réaliste** pour développer et éprouver la "
    "méthode de monitoring sur des données de terrain. Les signalements obtenus sur ce site "
    "**ne valident pas définitivement la nature technique** des anomalies — cela demanderait "
    "un accès aux journaux d'exploitation et de maintenance. Ils démontrent la capacité de la "
    "méthode à repérer des écarts persistants.\n"
    "- **Transposition** : appliquer la méthode à un autre système (par exemple une "
    "installation cible) consisterait à **réapprendre et recalibrer localement** sur ses "
    "propres données, et non à transférer les résultats chiffrés de DKASC."
)

# ------------------------------------------------------------------
st.subheader("Découpage temporel")
st.markdown(
    "- **Entraînement** du modèle : 2009–2019.\n"
    "- **Calibration**, sélection du modèle et fixation des seuils : 2020–2022.\n"
    "- **Évaluation temporelle out-of-time post-sélection** : 2023–2025.\n\n"
    "L'évaluation porte sur une période **postérieure** à celle ayant servi au choix et à la "
    "calibration. Ce n'est toutefois pas un **test totalement aveugle** : cette période a été "
    "observée pendant l'analyse exploratoire. La formulation reste donc prudente — "
    "« évaluation out-of-time post-sélection »."
)

# ------------------------------------------------------------------
st.subheader("Modèle de référence et signification de son gel")
st.markdown(
    "Le modèle retenu (**Random Forest**) est sélectionné sur la période de calibration, "
    "selon l'erreur en heures de jour, **puis figé** : il n'est ni réentraîné ni recalibré "
    "sur la période d'évaluation."
)
st.markdown(
    "Le gel garantit une **référence stable** : les écarts de 2023–2025 sont mesurés contre "
    "un comportement de référence inchangé. Une dérive persistante des résidus indique donc "
    "un **changement par rapport au régime de calibration** — mais ce changement **peut "
    "provenir de plusieurs sources**, que le dispositif ne permet pas, à lui seul, de "
    "départager :\n"
    "- le **système photovoltaïque** lui-même (salissure, ombrage, défaut d'onduleur, "
    "vieillissement) ;\n"
    "- les **capteurs** (irradiance, puissance) ;\n"
    "- la **qualité ou la complétude des données** ;\n"
    "- un **changement de distribution** des conditions (météo, saisonnalité) non couvert par "
    "la calibration ;\n"
    "- les **limites propres du modèle** de référence.\n\n"
    "Trancher entre ces causes nécessite une **investigation technique**, hors du périmètre "
    "de ce tableau de bord."
)
st.markdown(
    "Le modèle fournit une **estimation de la puissance attendue au même instant**, à partir "
    "de l'irradiance et de variables temporelles mesurées simultanément. Il ne s'agit donc "
    "**pas d'une prévision** (projection à l'avance) : le modèle n'anticipe pas, il estime "
    "une valeur concurrente de la mesure. Le terme « prévision » serait impropre ici."
)

# ------------------------------------------------------------------
st.subheader("Définitions formelles")

st.markdown("**Résidu instantané** (au pas de 5 minutes) :")
st.latex(r"e_t = P^{\mathrm{mes}}_t - P^{\mathrm{att}}_t")
st.markdown(
    "où $P^{\\mathrm{mes}}_t$ est la puissance mesurée et $P^{\\mathrm{att}}_t$ la puissance "
    "attendue (estimée par le modèle) à l'instant $t$. Un résidu négatif traduit une mesure "
    "inférieure à l'attendu."
)

st.markdown("**Écart énergétique quotidien relatif** (en %) :")
st.latex(r"G_d = 100 \times \frac{E^{\mathrm{mes}}_d - E^{\mathrm{att}}_d}{E^{\mathrm{att}}_d}")
st.markdown(
    "où $E^{\\mathrm{mes}}_d$ et $E^{\\mathrm{att}}_d$ sont les énergies mesurée et attendue "
    "du jour $d$ (intégrales des puissances). Les moyennes glissantes 7 jours et 30 jours de "
    "$G_d$ servent à distinguer un creux ponctuel d'une dérive installée."
)

st.markdown("**Couverture journalière** (en %) :")
st.latex(r"C_d = 100 \times \frac{N_d}{288}")
st.markdown(
    f"où $N_d$ est le nombre d'horodatages **uniques** observés le jour $d$, rapporté aux "
    f"**{OBS_THEORIQUES_PAR_JOUR}** relevés théoriques d'une journée au pas de 5 minutes "
    f"($24 \\times 60 / 5 = {OBS_THEORIQUES_PAR_JOUR}$). Les éventuels doublons ne portent pas "
    f"$C_d$ au-delà de 100 %. Un jour est **valide** si $C_d \\geq {SEUIL_COUVERTURE}$ %."
)

st.markdown("**Calibration des seuils** :")
st.latex(r"S = Q_{0{,}05}\left(\{G\}_{\,2020\text{–}2022}\right)")
st.markdown(
    "Chaque seuil $S$ est le **quantile inférieur à 5 %** de la distribution de l'indicateur "
    "correspondant sur la calibration 2020–2022, calculé **séparément** pour l'écart "
    "quotidien, la moyenne 7 jours et la moyenne 30 jours. Valeurs retenues, lues dans le "
    f"fichier de calibration : **quotidien {seuil_jour:.2f} %**, **7 jours {seuil_7j:.2f} %**, "
    f"**30 jours {seuil_30j:.2f} %**."
)

# ------------------------------------------------------------------
st.subheader("Logique de classification — les sept niveaux")
st.markdown(
    "Les niveaux combinent le **franchissement d'un seuil** et la **persistance** (séries de "
    "jours consécutifs valides). Une journée invalide ou manquante **interrompt** les séries. "
    "Le tableau ci-dessous résume la logique ; les règles opérationnelles exactes figurent "
    "dans le « rulebook » consultable sur la page Détection d'anomalies."
)
st.markdown(
    "| Niveau | Libellé | Condition principale | Persistance | Interprétation prudente |\n"
    "|:---:|---|---|:---:|---|\n"
    "| −1 | Données insuffisantes | Couverture < 80 % | — | Jour non évaluable : ni normal ni anormal |\n"
    "| 0 | Normal | Écart dans la plage de calibration | — | Aucun signalement |\n"
    "| 1 | Alerte quotidienne | Écart quotidien sous le seuil quotidien | 1 jour | Écart ponctuel à confirmer |\n"
    "| 2 | Surveillance glissante | Moyenne 7 j sous le seuil 7 j | < 3 jours | Tendance courte à surveiller |\n"
    "| 3 | Avertissement soutenu | Série d'alerte sur la fenêtre 7 j | ≥ 3 jours | Sous-performance soutenue |\n"
    "| 4 | Critique persistante | Série d'alerte sur la fenêtre 30 j | ≥ 7 jours | Sous-performance persistante ; inspection à envisager |\n"
    "| 5 | Sous-performance sévère persistante | Série d'alerte sur la fenêtre 30 j | ≥ 30 jours | Sous-performance sévère installée ; inspection prioritaire |\n"
)

# ------------------------------------------------------------------
st.subheader("Faux positifs et limites de l'évaluation")
st.markdown(
    "Le jeu de données ne comporte **ni journaux de maintenance, ni périodes certifiées "
    "« saines », ni alarmes constructeur, ni défauts étiquetés**. En l'absence de vérité "
    "terrain, il n'est **pas possible de calculer** les métriques de détection classiques "
    "(précision, rappel, taux de faux positifs) : on ne peut confirmer ni qu'un jour signalé "
    "correspond à un vrai problème, ni qu'un jour normal en est exempt."
)
st.markdown(
    "Les signalements doivent donc être traités comme des **écarts à vérifier**, et non comme "
    "des défauts avérés. Un signalement peut correspondre à :\n"
    "- un **vrai problème** du système ;\n"
    "- un **défaut de capteur** ;\n"
    "- un **décalage temporel** (horodatage, synchronisation) ;\n"
    "- des **données incomplètes** ;\n"
    "- des **conditions météorologiques mal représentées** par le modèle ;\n"
    "- une **limite de généralisation** du modèle.\n\n"
    "La quantification des faux positifs et négatifs relève d'un travail dédié (par exemple "
    "par **injection de fautes synthétiques**), hors du périmètre de cette version."
)

# ------------------------------------------------------------------
st.subheader("Périmètre de cette version (V1)")
col1, col2 = st.columns(2)
with col1:
    st.markdown(
        "**Ce que fait le tableau de bord**\n"
        "- Visualise des résultats **pré-calculés** (lecture seule).\n"
        "- Affiche résidus, écarts, niveaux, épisodes, qualité des données et performance du "
        "modèle.\n"
        "- Restitue le dernier statut fiable et les règles de classification."
    )
with col2:
    st.markdown(
        "**Ce qu'il ne fait pas (V1)**\n"
        "- Pas de réentraînement ni de recalibration du modèle.\n"
        "- Pas d'import de nouveaux jeux de données.\n"
        "- Pas de connexion onduleur en temps réel, pas d'alerte réelle.\n"
        "- Pas de diagnostic automatique de la cause physique."
    )

# ------------------------------------------------------------------
st.subheader("Séparation des questions de recherche")
st.markdown(
    "La **capacité de détection** (le dispositif repère-t-il une sous-performance ?) et la "
    "**valeur économique de la détection précoce** (quelle énergie une intervention rapide "
    "permet-elle de préserver ?) sont traitées **séparément**. Les confondre conduirait à un "
    "raisonnement circulaire. La valorisation économique, dépendante du régime de comptage "
    "(net-metering), fait l'objet d'une analyse dédiée et **n'est pas conduite dans ce tableau "
    "de bord**."
)

st.info(
    "En résumé : ce tableau de bord est un **outil de visualisation et de surveillance**, "
    "pas un outil de diagnostic. Il signale où et quand la production s'écarte de l'attendu "
    "d'un modèle figé, en restant prudent sur l'interprétation ; l'explication physique et la "
    "décision d'intervention relèvent de l'expertise humaine."
)
