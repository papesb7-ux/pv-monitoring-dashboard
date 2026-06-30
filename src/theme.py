"""src/theme.py — Definitions communes : libelles FR et palette unique des niveaux.

Ce module ne contient aucune donnee lourde. Il centralise :
  - NIVEAUX  : libelle francais de chaque niveau de surveillance (-1 a 5)
  - COULEURS : couleur associee a chaque niveau (palette unique du dashboard)
"""

# Libelles francais des niveaux de surveillance (de -1 a 5).
NIVEAUX = {
    -1: "Données insuffisantes",
    0: "Normal",
    1: "Alerte quotidienne",
    2: "Surveillance glissante",
    3: "Avertissement soutenu",
    4: "Critique persistante",
    5: "Sous-performance sévère persistante",
}

# Palette unique : du gris (donnees insuffisantes) au rouge fonce (severe).
COULEURS = {
    -1: "#b0b0b0",  # gris
    0: "#2e7d32",   # vert
    1: "#fbc02d",   # jaune
    2: "#fb8c00",   # orange clair
    3: "#f4511e",   # orange
    4: "#e53935",   # rouge
    5: "#8e0000",   # rouge fonce
}


def libelle_niveau(niveau):
    """Renvoie 'n — Libelle' pour un niveau entier (ex. '5 — Sous-performance severe...')."""
    try:
        n = int(niveau)
    except (TypeError, ValueError):
        return str(niveau)
    return f"{n} — {NIVEAUX.get(n, '?')}"
