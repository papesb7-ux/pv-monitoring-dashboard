"""
src/labels.py
Traduction FR des libelles anglais, pour AFFICHAGE uniquement.
Les fichiers de donnees sources ne sont jamais modifies.
"""

_TRADUCTIONS_FR = {
    "Within calibration monitoring range": "Dans la plage de calibration",
    "Daily underperformance alert": "Alerte de sous-performance journaliere",
    "Rolling underperformance watch": "Surveillance de sous-performance (glissante)",
    "Sustained underperformance warning": "Avertissement de sous-performance soutenue",
    "Persistent underperformance alert": "Alerte de sous-performance persistante",
    "Severe persistent underperformance": "Sous-performance severe persistante",
    "Insufficient data": "Donnees insuffisantes",
    "Data insufficient": "Donnees insuffisantes",
    "Continue routine monitoring.": "Poursuivre la surveillance de routine.",
    "Review daily performance.": "Examiner la performance journaliere.",
    "Monitor rolling trend.": "Surveiller la tendance glissante.",
    "Investigate sustained deviation.": "Investiguer l ecart soutenu.",
    "Schedule a technical inspection.": "Planifier une inspection technique.",
    "Escalate the technical inspection and perform root-cause analysis before model retraining.":
        "Escalader l inspection technique et mener une analyse de cause racine avant tout reentrainement du modele.",
}


def traduire(valeur):
    if valeur is None:
        return valeur
    return _TRADUCTIONS_FR.get(str(valeur).strip(), valeur)
