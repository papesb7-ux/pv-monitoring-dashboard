"""
views/methodologie.py
Cadrage methodologique du dispositif de monitoring (V1).
Page de texte : definit le perimetre, le vocabulaire, et les limites
d'interpretation. Aucune donnee calculee ici. Lecture seule.
"""

import streamlit as st

st.title("📘 Methodologie et cadrage")
st.caption(
    "Cette page precise ce que le dispositif mesure, ce qu'il ne mesure pas, "
    "et les precautions d'interpretation. Elle vaut reference pour la lecture "
    "de toutes les autres pages."
)

st.subheader("Principe general")
st.markdown(
    "Le dispositif compare la production electrique **mesuree** d'un systeme "
    "photovoltaique a une production **attendue**, estimee par un modele de "
    "reference a partir de l'irradiance et de variables temporelles. L'ecart "
    "entre les deux (le **residu**) est suivi dans le temps. Une derive "
    "persistante de cet ecart vers des valeurs negatives signale une "
    "**sous-performance relative au modele**."
)

st.subheader("Jeu de donnees")
st.markdown(
    "- **Source** : DKASC (Desert Knowledge Australia Solar Centre), Alice "
    "Springs, Australie. Donnees publiques au pas de 5 minutes.\n"
    "- **Role** : ce jeu sert de **terrain d'essai realiste** pour developper "
    "et valider la methode de monitoring. Il n'est pas le systeme cible final.\n"
    "- **Decoupage temporel** : entrainement (2009-2019), **calibration** des "
    "seuils (2020-2022), **evaluation out-of-time** (2023-2025)."
)

st.subheader("Modele de reference")
st.markdown(
    "- Le modele retenu (**Random Forest**) est selectionne sur la periode de "
    "calibration, selon l'erreur en heures de jour, **puis fige**.\n"
    "- Une fois fige, il n'est **ni reentraine, ni recalibre** sur la periode "
    "d'evaluation. C'est cette stabilite qui permet d'interpreter une derive "
    "des residus comme un changement du **systeme**, et non du modele.\n"
    "- Le modele estime une production **concurrente** (a partir de l'irradiance "
    "mesuree au meme instant). Il ne s'agit donc pas d'une **prevision** "
    "(au sens d'une projection a l'avance) : ce terme serait impropre ici."
)

st.subheader("Vocabulaire : ce que disent (et ne disent pas) les termes employes")
st.markdown(
    "- **Sous-performance relative au modele** : la production mesuree est "
    "inferieure a l'attendu du modele. Cela **ne prouve pas** une panne "
    "materielle : l'origine physique (salissure, ombrage, defaut onduleur, "
    "vieillissement, ou simple limite du modele) releve d'une **inspection "
    "technique**, hors perimetre de ce tableau de bord.\n"
    "- **Evaluation out-of-time post-selection** : les performances sont "
    "mesurees sur une periode posterieure a celle ayant servi a choisir et "
    "calibrer le modele. Ce n'est pas un **test a l'aveugle** au sens strict, "
    "puisque la periode a ete observee lors de l'analyse ; la formulation reste "
    "donc prudente.\n"
    "- **Energie estimee non produite** : ecart cumule a la production attendue "
    "par le modele. C'est une grandeur **relative au modele**, et non une perte "
    "mesuree au compteur."
)

st.subheader("Logique de classification")
st.markdown(
    "- Trois seuils sont calibres sur 2020-2022 (5e percentile des ecarts "
    "journalier, glissant 7 jours, glissant 30 jours).\n"
    "- Un jour est **non evaluable** (`Donnees insuffisantes`) si sa couverture "
    "de mesure est insuffisante : il ne traduit alors **ni** performance "
    "normale **ni** anomalie.\n"
    "- Les niveaux d'anomalie combinent le franchissement des seuils et la "
    "**persistance** (series de jours consecutifs), pour distinguer un creux "
    "ponctuel d'une derive installee."
)

st.subheader("Perimetre de cette version (V1)")
col1, col2 = st.columns(2)
with col1:
    st.markdown(
        "**Ce que fait le tableau de bord**\n"
        "- Visualise des resultats **pre-calcules** (lecture seule).\n"
        "- Affiche residus, ecarts, niveaux, episodes, qualite des donnees, "
        "performance du modele.\n"
        "- Simule des notifications a partir des statuts."
    )
with col2:
    st.markdown(
        "**Ce qu'il ne fait pas (V1)**\n"
        "- Pas de reentrainement ni de recalibration du modele.\n"
        "- Pas d'import de nouveaux jeux de donnees.\n"
        "- Pas de connexion onduleur en temps reel, pas d'alerte reelle.\n"
        "- Pas de diagnostic automatique de la cause physique."
    )

st.subheader("Separation des questions de recherche")
st.markdown(
    "La **capacite de detection** (le dispositif repere-t-il une "
    "sous-performance ?) et la **valeur economique de la detection precoce** "
    "(que represente l'energie preservee par une intervention rapide ?) sont "
    "traitees **separement**. Melanger les deux conduirait a un raisonnement "
    "circulaire ; la valorisation economique, dependante du regime de comptage "
    "(net-metering), fait l'objet d'une analyse dediee et n'est pas conduite "
    "dans ce tableau de bord."
)

st.info(
    "En resume : ce tableau de bord est un **outil de visualisation et de "
    "surveillance**, pas un outil de diagnostic. Il signale ou et quand la "
    "production s'ecarte de l'attendu d'un modele fige ; l'explication physique "
    "et la decision d'intervention restent du ressort de l'expertise humaine."
)
