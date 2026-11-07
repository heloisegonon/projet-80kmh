"""Collecte des données brutes depuis les sources publiques.

Toutes les données sont récupérées par le code à partir d'URL publiques :

- BAAC (accidents corporels) et radars fixes : API de data.gouv.fr ;
- population départementale : API Melodi de l'INSEE (sans clé) ;
- consommation de carburants par département : API DiDo du SDES ;
- contours des départements : ``cartiflette``.

Les fichiers téléchargés sont mis en cache dans ``data/raw/`` (non versionné).
"""

from __future__ import annotations

import io
import os
import re
import warnings
from functools import cache, wraps
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

RACINE = Path(__file__).resolve().parents[1]
DOSSIER_RAW = RACINE / "data" / "raw"
# Copies locales des données de contexte, relues si la source en ligne est injoignable.
DOSSIER_CACHE = RACINE / "data" / "processed" / "contexte"
# Liste versionnée des URL des fichiers BAAC, utilisée si l'API data.gouv.fr est injoignable.
MANIFESTE_BAAC = RACINE / "data" / "sources_baac.csv"

API_DATAGOUV = "https://www.data.gouv.fr/api/1/datasets/{}/"
DATASET_BAAC = "53698f4ca3a729239d2036df"
DATASET_RADARS = "6712583387af110196942793"
URL_RADARS_SECOURS = (
    "https://static.data.gouv.fr/resources/liste-des-radars-fixes-en-france/"
    "20251230-134204/jeu-de-donnees-liste-des-radars-fixes-en-france-12-2025.csv"
)
URL_MELODI_POPULATION = (
    "https://api.insee.fr/melodi/data/DS_ESTIMATION_POPULATION"
    "?GEO=DEP&SEX=_T&AGE=_T&EP_MEASURE=POP_JAN_1ST&maxResult=10000"
)
URL_CARBURANTS_SDES = (
    "https://data.statistiques.developpement-durable.gouv.fr/dido/api/v1/"
    "datafiles/445d1fbb-4ebd-48b0-b566-7d97f21a871e/csv?withColumnName=true"
)

TABLES_BAAC = ("caracteristiques", "lieux", "vehicules", "usagers")
# Les titres des ressources BAAC ne sont pas homogènes : « Caract_2024 »,
# « carcteristiques-2022 », « caracteristiques_2016 »…
_MOTIF_BAAC = re.compile(
    r"^(?P<table>caract\w*|carct\w*|lieux|vehicules|usagers)[-_](?P<annee>\d{4})\.csv$",
    re.IGNORECASE,
)

# Produits pétroliers routiers dans le fichier SDES (en m3).
CARBURANTS_ROUTIERS = [
    "GAZOLE",
    "GPL",
    "SUPER_ETH_E85",
    "SUPER_SANS_PLOMB_95",
    "SUPER_SANS_PLOMB_95_E10",
    "SUPER_SANS_PLOMB_98",
    "SUPER_SANS_PLOMB",
    "SUPER_PLOMBE",
]


@cache
def session() -> requests.Session:
    """Session HTTP qui relance automatiquement les requêtes en échec.

    Couvre les refus de connexion et erreurs serveur passagers (5 essais,
    attente croissante de 1 à 16 s).
    """
    relances = Retry(
        total=5,
        connect=5,
        read=3,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    sess = requests.Session()
    sess.mount("https://", HTTPAdapter(max_retries=relances))
    return sess


def avec_cache_local(nom: str):
    """Garde une copie Parquet du résultat et la relit si la source en ligne échoue.

    Après chaque chargement réussi, le résultat est écrit dans
    ``data/processed/contexte/<nom>.parquet``. Si le chargement échoue (réseau
    bloqué, site en panne) et qu'une copie existe, elle est renvoyée avec un
    avertissement ; sinon l'erreur d'origine est levée.
    """

    def decorateur(fonction):
        @wraps(fonction)
        def enveloppe(*args, **kwargs):
            chemin = DOSSIER_CACHE / f"{nom}.parquet"
            try:
                resultat = fonction(*args, **kwargs)
            except Exception as erreur:
                if not chemin.exists():
                    raise
                warnings.warn(
                    f"{nom} : source injoignable ({type(erreur).__name__}), copie locale {chemin.name} utilisée.",
                    stacklevel=2,
                )
                if nom == "contours":
                    import geopandas

                    return geopandas.read_parquet(chemin)
                return pd.read_parquet(chemin)
            chemin.parent.mkdir(parents=True, exist_ok=True)
            resultat.to_parquet(chemin, index=False)
            return resultat

        return enveloppe

    return decorateur


def lister_ressources(dataset_id: str) -> pd.DataFrame:
    """Renvoie les ressources d'un jeu de données data.gouv.fr.

    Parameters
    ----------
    dataset_id : str
        Identifiant (ou slug) du jeu de données.

    Returns
    -------
    pd.DataFrame
        Une ligne par ressource : ``titre``, ``url``, ``format``, ``modifie``.
    """
    reponse = session().get(API_DATAGOUV.format(dataset_id), timeout=30)
    reponse.raise_for_status()
    return pd.DataFrame(
        [
            {
                "titre": r["title"],
                "url": r["url"],
                "format": r.get("format"),
                "modifie": r.get("last_modified"),
            }
            for r in reponse.json()["resources"]
        ]
    )


def lister_fichiers_baac(annees: range | list[int] = range(2010, 2025)) -> pd.DataFrame:
    """Liste les fichiers BAAC (4 tables par an) disponibles sur data.gouv.fr.

    Les fichiers « véhicules immatriculés » et les bases agrégées sont ignorés.
    Si une même table apparaît deux fois pour une année, la version la plus
    récente est conservée. Si l'API est injoignable, la liste versionnée
    ``data/sources_baac.csv`` est utilisée à la place.

    Parameters
    ----------
    annees : iterable of int
        Années à conserver.

    Returns
    -------
    pd.DataFrame
        Colonnes ``annee``, ``table``, ``url``, triées par année puis table.
    """
    try:
        ressources = lister_ressources(DATASET_BAAC)
    except requests.RequestException as erreur:
        warnings.warn(
            f"API data.gouv.fr injoignable ({type(erreur).__name__}) : "
            f"utilisation de la liste versionnée {MANIFESTE_BAAC.name}.",
            stacklevel=2,
        )
        return pd.read_csv(MANIFESTE_BAAC).query("annee in @annees").reset_index(drop=True)
    lignes = []
    for res in ressources.itertuples():
        match = _MOTIF_BAAC.match(res.titre.strip())
        if match is None:
            continue
        table = match["table"].lower()
        if table.startswith(("caract", "carct")):
            table = "caracteristiques"
        lignes.append({"annee": int(match["annee"]), "table": table, "url": res.url, "modifie": res.modifie})
    fichiers = (
        pd.DataFrame(lignes)
        .query("annee in @annees")
        .sort_values("modifie")
        .drop_duplicates(["annee", "table"], keep="last")
        .sort_values(["annee", "table"])
        .drop(columns="modifie")
        .reset_index(drop=True)
    )
    manquants = {(a, t) for a in annees for t in TABLES_BAAC} - set(zip(fichiers["annee"], fichiers["table"]))
    if manquants:
        raise ValueError(f"Fichiers BAAC introuvables : {sorted(manquants)}")
    return fichiers
