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


def telecharger(url: str, destination: Path, forcer: bool = False) -> Path:
    """Télécharge un fichier si absent du cache local.

    Parameters
    ----------
    url : str
        Adresse du fichier.
    destination : Path
        Chemin local du fichier.
    forcer : bool
        Retélécharge même si le fichier existe déjà.

    Returns
    -------
    Path
        Chemin du fichier local.
    """
    destination = Path(destination)
    if destination.exists() and not forcer:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    with session().get(url, stream=True, timeout=120) as reponse:
        reponse.raise_for_status()
        temporaire = destination.with_suffix(destination.suffix + ".part")
        with open(temporaire, "wb") as fichier:
            fichier.writelines(reponse.iter_content(chunk_size=1 << 20))
    temporaire.replace(destination)
    return destination


def telecharger_baac(
    annees: range | list[int] = range(2010, 2025), dossier: Path = DOSSIER_RAW / "baac"
) -> pd.DataFrame:
    """Télécharge les 4 tables BAAC de chaque année dans ``dossier/<annee>/<table>.csv``.

    Returns
    -------
    pd.DataFrame
        La liste des fichiers avec une colonne ``chemin`` vers la copie locale.
    """
    fichiers = lister_fichiers_baac(annees)
    fichiers["chemin"] = [
        telecharger(f.url, Path(dossier) / str(f.annee) / f"{f.table}.csv") for f in fichiers.itertuples()
    ]
    return fichiers


@avec_cache_local("radars")
def charger_radars() -> pd.DataFrame:
    """Charge la liste des radars fixes (dernière version publiée sur data.gouv.fr).

    Returns
    -------
    pd.DataFrame
        Colonnes ``id_radar``, ``type_radar``, ``date_mise_en_service``, ``vma``,
        ``lat``, ``lon``.
    """
    try:
        ressources = lister_ressources(DATASET_RADARS).query("format == 'csv'")
        url = ressources.sort_values("modifie").iloc[-1]["url"]
    except requests.RequestException:
        warnings.warn("API data.gouv.fr injoignable : URL des radars de décembre 2025.", stacklevel=2)
        url = URL_RADARS_SECOURS
    chemin = telecharger(url, DOSSIER_RAW / "radars" / Path(url).name)
    radars = pd.read_csv(chemin, sep=";", encoding="latin-1", dtype=str)
    radars.columns = ["id_radar", "type_radar", "date_mise_en_service", "vma", "lat", "lon"]
    radars["date_mise_en_service"] = pd.to_datetime(
        radars["date_mise_en_service"], format="%d/%m/%Y %H:%M", errors="coerce"
    )
    for col in ("vma", "lat", "lon"):
        radars[col] = pd.to_numeric(radars[col].str.strip(), errors="coerce")
    return radars


@avec_cache_local("population")
def charger_population() -> pd.DataFrame:
    """Récupère la population au 1er janvier par département (INSEE, API Melodi).

    Returns
    -------
    pd.DataFrame
        Colonnes ``code_dep``, ``annee``, ``population``.
    """
    reponse = session().get(URL_MELODI_POPULATION, timeout=60)
    reponse.raise_for_status()
    observations = reponse.json()["observations"]
    population = pd.DataFrame(
        {
            "code_dep": [o["dimensions"]["GEO"].split("-")[-1] for o in observations],
            "annee": [int(o["dimensions"]["TIME_PERIOD"]) for o in observations],
            "population": [o["measures"]["OBS_VALUE_NIVEAU"]["value"] for o in observations],
        }
    )
    return population.sort_values(["code_dep", "annee"]).reset_index(drop=True)


@avec_cache_local("carburants")
def charger_carburants() -> pd.DataFrame:
    """Récupère les ventes annuelles de carburants routiers par département (SDES).

    Sert d'indicateur indirect du trafic local, notamment pour neutraliser 2020.

    Returns
    -------
    pd.DataFrame
        Colonnes ``code_dep``, ``annee``, ``carburants_routiers_m3`` et le détail par produit.
    """
    reponse = session().get(URL_CARBURANTS_SDES, timeout=60)
    reponse.raise_for_status()
    brut = pd.read_csv(io.StringIO(reponse.text), sep=";", dtype={"DEPARTEMENT_CODE": str})
    carburants = brut.rename(columns={"DEPARTEMENT_CODE": "code_dep", "ANNEE": "annee"})
    carburants["carburants_routiers_m3"] = carburants[CARBURANTS_ROUTIERS].fillna(0).sum(axis=1)
    return carburants[["code_dep", "annee", "carburants_routiers_m3", *CARBURANTS_ROUTIERS]]


@avec_cache_local("contours")
def charger_contours(annee: int = 2022):
    """Récupère les contours des départements de France entière via ``cartiflette``.

    Returns
    -------
    geopandas.GeoDataFrame
        Colonnes ``code_dep``, ``nom_dep``, ``geometry`` (WGS84).
    """
    from cartiflette import carti_download

    contours = carti_download(
        values="France",
        crs=4326,
        borders="DEPARTEMENT",
        vectorfile_format="geojson",
        simplification=50,
        filter_by="FRANCE_ENTIERE",
        source="EXPRESS-COG-CARTO-TERRITOIRE",
        year=annee,
    )
    return contours.rename(columns={"INSEE_DEP": "code_dep", "LIBELLE_DEPARTEMENT": "nom_dep"})[
        ["code_dep", "nom_dep", "geometry"]
    ]


def charger_departements_90() -> pd.DataFrame:
    """Charge la table construite des départements revenus aux 90 km/h (versionnée dans le dépôt)."""
    return pd.read_csv(
        RACINE / "data" / "departements_90.csv",
        dtype={"code_dep": str},
        parse_dates=["date_releve"],
    )


# --- Cache S3 (SSP Cloud / MinIO) -------------------------------------------------


def systeme_fichiers_s3():
    """Ouvre une connexion S3 à partir des variables d'environnement du SSP Cloud.

    Renvoie ``None`` si les identifiants ne sont pas disponibles.
    """
    if not os.environ.get("AWS_ACCESS_KEY_ID"):
        return None
    import s3fs

    endpoint = os.environ.get("AWS_S3_ENDPOINT", "minio.lab.sspcloud.fr")
    return s3fs.S3FileSystem(
        client_kwargs={"endpoint_url": f"https://{endpoint}"},
        key=os.environ["AWS_ACCESS_KEY_ID"],
        secret=os.environ["AWS_SECRET_ACCESS_KEY"],
        token=os.environ.get("AWS_SESSION_TOKEN"),
    )


def lire_parquet_s3(chemin_s3: str) -> pd.DataFrame | None:
    """Lit un Parquet sur S3 ; renvoie ``None`` si S3 ou le fichier est indisponible."""
    fs = systeme_fichiers_s3()
    if fs is None or not fs.exists(chemin_s3):
        return None
    with fs.open(chemin_s3, "rb") as fichier:
        return pd.read_parquet(fichier)


def ecrire_parquet_s3(df: pd.DataFrame, chemin_s3: str) -> bool:
    """Écrit un DataFrame en Parquet sur S3 ; renvoie ``False`` si S3 est indisponible."""
    fs = systeme_fichiers_s3()
    if fs is None:
        return False
    with fs.open(chemin_s3, "wb") as fichier:
        df.to_parquet(fichier, index=False)
    return True


if __name__ == "__main__":
    fichiers = telecharger_baac()
    print(f"{len(fichiers)} fichiers BAAC disponibles dans {DOSSIER_RAW / 'baac'}")
