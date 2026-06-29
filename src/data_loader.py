"""
src/data_loader.py
Lecture des fichiers de resultats pre-calcules (notebook 02), via le manifeste.
Lecture seule. Cache Streamlit. Normalisation des colonnes. Traduction FR pour affichage.
"""

import json
import pandas as pd

from src import config

try:
    import streamlit as st
    cache_data = st.cache_data
except Exception:
    def cache_data(func=None, **kwargs):
        if func is None:
            def wrapper(inner):
                return inner
            return wrapper
        return func


def _read_parquet(section, key):
    path = config.get_manifest_path(section, key)
    if not path.exists():
        raise FileNotFoundError("Fichier introuvable : " + str(path))
    return pd.read_parquet(path)


def _read_csv(section, key):
    path = config.get_manifest_path(section, key)
    if not path.exists():
        raise FileNotFoundError("Fichier introuvable : " + str(path))
    return pd.read_csv(path)


def _require_columns(df, required, source_name):
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(
            "Colonnes manquantes dans " + source_name + " : " + str(missing)
            + "\nColonnes presentes : " + str(list(df.columns))
        )


_LATEST_STATUS_RENAME = {
    "daily_relative_gap_percent": "relative_energy_gap_percent",
    "rolling_7d_gap_percent": "rolling_7d_relative_gap_percent",
    "rolling_30d_gap_percent": "rolling_30d_relative_gap_percent",
}


@cache_data
def load_oot_predictions():
    df = _read_parquet("monitoring", "oot_predictions")
    _require_columns(
        df,
        ["timestamp", "measured_active_power_kw", "predicted_active_power_kw",
         "residual_kw", "daylight_flag"],
        "oot_predictions",
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df


@cache_data
def load_daily_classification():
    df = _read_parquet("monitoring", "final_daily_classification")
    _require_columns(
        df,
        ["date", "relative_energy_gap_percent", "rolling_7d_relative_gap_percent",
         "rolling_30d_relative_gap_percent", "monitoring_valid_day", "anomaly_level",
         "anomaly_status", "daily_alert_streak_days", "rolling_7d_alert_streak_days",
         "rolling_30d_alert_streak_days"],
        "final_daily_classification",
    )
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


@cache_data
def load_oot_daily_monitoring():
    df = _read_parquet("monitoring", "oot_daily_monitoring")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


@cache_data
def load_calibration_daily_monitoring():
    df = _read_parquet("monitoring", "calibration_daily_monitoring")
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


@cache_data
def load_thresholds():
    return _read_csv("reports", "thresholds")


@cache_data
def load_episodes():
    return _read_csv("reports", "episodes")


@cache_data
def load_latest_status():
    df = _read_csv("reports", "latest_status")
    return df.rename(columns=_LATEST_STATUS_RENAME)


@cache_data
def load_rulebook():
    return _read_csv("reports", "rulebook")


@cache_data
def load_model_selection():
    return _read_csv("reports", "model_selection")


@cache_data
def load_oot_metrics():
    return _read_csv("reports", "oot_metrics")


@cache_data
def load_feature_importance():
    return _read_csv("reports", "feature_importance")


@cache_data
def load_model_registry():
    path = config.get_manifest_path("metadata", "model_registry")
    if not path.exists():
        raise FileNotFoundError("Fichier introuvable : " + str(path))
    with open(path, mode="r", encoding="utf-8") as handle:
        return json.load(handle)


# --- Traduction FR pour AFFICHAGE (les fichiers sources sont intacts) ---
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
    "Investigate sustained deviation.": "Investiguer l'ecart soutenu.",
    "Schedule a technical inspection.": "Planifier une inspection technique.",
    "Escalate the technical inspection and perform root-cause analysis before model retraining.":
        "Escalader l'inspection technique et mener une analyse de cause racine avant tout reentrainement du modele.",
}


def traduire(valeur):
    """Traduit un libelle anglais en francais pour l affichage.
    Renvoie la valeur d origine si elle n est pas dans la table."""
    if valeur is None:
        return valeur
    return _TRADUCTIONS_FR.get(str(valeur).strip(), valeur)
