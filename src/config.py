"""
src/config.py
Chargement centralise de la configuration du projet.

Trois fichiers YAML dans config/ :
  - app_config.yaml      : identite de l'app, cadrage dataset, seuils, persistance
  - site_metadata.yaml   : metadonnees du site (DKASC)
  - data_manifest.yaml   : emplacement de tous les fichiers de resultats

Ce module ne lit AUCUNE donnee lourde : seulement les YAML.
Il expose des fonctions simples utilisees partout dans le dashboard.
"""

from pathlib import Path
import yaml

# Racine du projet = dossier parent de src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"


def _load_yaml(filename):
    """Charge un fichier YAML depuis config/ et renvoie un dictionnaire."""
    path = CONFIG_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            "Fichier de configuration introuvable : "
            + str(path)
            + "\nVerifie que config/" + filename + " existe."
        )
    with open(path, mode="r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if data is None:
        raise ValueError(
            "Le fichier config/" + filename + " est vide ou invalide."
        )
    return data


def load_app_config():
    """Configuration generale de l'application."""
    return _load_yaml("app_config.yaml")


def load_site_metadata():
    """Metadonnees du site (localisation, systeme, etc.)."""
    return _load_yaml("site_metadata.yaml")


def load_data_manifest():
    """Manifeste : emplacement de tous les fichiers de resultats."""
    return _load_yaml("data_manifest.yaml")


def resolve_path(relative_path):
    """
    Transforme un chemin relatif du manifeste (ex. 'data/monitoring/x.parquet')
    en chemin absolu base sur la racine du projet.
    """
    return PROJECT_ROOT / relative_path


def get_manifest_path(section, key):
    """
    Renvoie le chemin absolu d'un fichier declare dans le manifeste.

    Exemple : get_manifest_path("monitoring", "final_daily_classification")
    Leve une erreur explicite si la section ou la cle n'existe pas.
    """
    manifest = load_data_manifest()
    if section not in manifest:
        raise KeyError(
            "Section absente du manifeste : '" + section + "'. "
            "Sections disponibles : " + str(list(manifest.keys()))
        )
    if key not in manifest[section]:
        raise KeyError(
            "Cle '" + key + "' absente de la section '" + section + "'. "
            "Cles disponibles : " + str(list(manifest[section].keys()))
        )
    return resolve_path(manifest[section][key])
