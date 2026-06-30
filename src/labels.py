"""src/labels.py — Traduction FR des libelles anglais, pour AFFICHAGE uniquement.

Les fichiers de donnees sources ne sont jamais modifies : on traduit a la volee.
Si un libelle n'est pas dans la table, la valeur d'origine est renvoyee inchangee.
"""

_TRADUCTIONS_FR = {
    # Statuts (anomaly_status / maximum_status)
    "Within calibration monitoring range": "Dans la plage de surveillance calibrée",
    "Daily underperformance alert": "Alerte de sous-performance quotidienne",
    "Rolling underperformance watch": "Surveillance glissante de sous-performance",
    "Sustained underperformance warning": "Avertissement de sous-performance soutenue",
    "Persistent underperformance alert": "Alerte de sous-performance persistante",
    "Severe persistent underperformance": "Sous-performance sévère persistante",
    "Insufficient data": "Données insuffisantes",
    "Data insufficient": "Données insuffisantes",
    # Actions recommandees (recommended_action)
    "Continue routine monitoring.": "Poursuivre la surveillance de routine.",
    "Review daily performance.": "Examiner la performance quotidienne.",
    "Monitor rolling trend.": "Surveiller la tendance glissante.",
    "Investigate sustained deviation.": "Investiguer l'écart soutenu.",
    "Schedule a technical inspection.": "Planifier une investigation technique.",
    "Escalate the technical inspection and perform root-cause analysis before model retraining.":
        "Déclencher une inspection technique prioritaire et rechercher la cause de la "
        "sous-performance avant tout réentraînement du modèle.",
}


def traduire(valeur):
    """Traduit un libelle anglais en francais pour l'affichage."""
    if valeur is None:
        return valeur
    return _TRADUCTIONS_FR.get(str(valeur).strip(), valeur)
