"""
Nettoyage des données BAAC (caractéristiques et lieux).

Lit les fichiers téléchargés par get_data.py dans data/raw/,
harmonise les formats qui changent selon les années, puis fusionne
les deux tables sur l'identifiant de l'accident (Num_Acc).
Le résultat est enregistré dans data/processed/accidents.parquet.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DATA_DIR = ROOT_DIR / "data" / "processed"

YEARS = range(2010, 2025)

# Date d'entrée en vigueur du 80 km/h
DATE_REFORME = pd.Timestamp("2018-07-01")

CARAC_COLUMNS = ["Num_Acc", "annee", "date", "heure", "lum", "agg",
                 "int", "atm", "col", "dep", "lat", "long"]
LIEUX_COLUMNS = ["Num_Acc", "catr", "circ", "nbv", "prof", "plan", "surf", "vma"]


def read_baac_file(category, year):
    """Lit un fichier BAAC brut en détectant le séparateur et l'encodage."""

    path = RAW_DATA_DIR / f"{category}_{year}.csv"

    if not path.exists():
        print(f"Fichier manquant : {path.name}")
        return None

    # Le séparateur change selon les années : ',' avant 2019, ';' ensuite
    with path.open(encoding="latin-1") as file:
        header = file.readline()
    separator = ";" if ";" in header else "\t" if "\t" in header else ","

    # Les anciens fichiers sont en latin-1, les récents en utf-8
    try:
        df = pd.read_csv(path, sep=separator, dtype=str, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(path, sep=separator, dtype=str, encoding="latin-1")

    # Supprime les espaces parasites autour des valeurs
    df = df.apply(lambda column: column.str.strip())

    # Depuis 2022, l'identifiant s'appelle Accident_Id dans les caractéristiques
    df = df.rename(columns={"Accident_Id": "Num_Acc"})

    return df


def to_code(column):
    """Convertit une colonne de codes en entiers ; -1 signifie 'non renseigné'."""

    values = pd.to_numeric(column, errors="coerce")
    return values.replace(-1, np.nan).astype("Int64")


def clean_departement(dep):
    """Met les codes département au format récent ('59', '2A', '971')."""

    dep = dep.str.upper()

    # Avant 2019 : 3 chiffres ('590' pour le Nord, '201' pour la Corse-du-Sud)
    dep = dep.replace({"201": "2A", "202": "2B"})
    old_format = dep.str.len().eq(3) & dep.str.endswith("0")

    return dep.where(~old_format, dep.str[:2])


def clean_caracteristiques(df, year):
    """Nettoie la table des caractéristiques d'une année."""

    df = df.copy()
    df["annee"] = year

    # Heure : '1530' ou '830' avant 2019, '15:30' ensuite
    hrmn = df["hrmn"].str.replace(":", "", regex=False).str.zfill(4)
    df["heure"] = pd.to_numeric(hrmn.str[:2], errors="coerce").astype("Int64")

    df["date"] = pd.to_datetime(
        pd.DataFrame({
            "year": df["annee"],
            "month": pd.to_numeric(df["mois"], errors="coerce"),
            "day": pd.to_numeric(df["jour"], errors="coerce"),
        }),
        errors="coerce",
    )

    df["dep"] = clean_departement(df["dep"])

    for column in ["lum", "agg", "int", "atm", "col"]:
        df[column] = to_code(df[column])

    # Coordonnées : entiers multipliés par 100 000 avant 2019,
    # décimaux avec une virgule ensuite. La valeur 0 signifie 'inconnu'.
    for column in ["lat", "long"]:
        values = pd.to_numeric(df[column].str.replace(",", ".", regex=False), errors="coerce")
        if year < 2019:
            values = values / 100_000
        df[column] = values.replace(0, np.nan)

    return df[CARAC_COLUMNS]


def clean_lieux(df):
    """Nettoie la table des lieux d'une année."""

    # La vitesse maximale autorisée (vma) n'existe qu'à partir de 2019 :
    # reindex crée la colonne vide pour les années précédentes
    df = df.reindex(columns=LIEUX_COLUMNS).copy()

    for column in LIEUX_COLUMNS[1:]:
        df[column] = to_code(df[column])

    # On écarte les vitesses aberrantes (0, 500, 900...)
    valid_speed = df["vma"].between(10, 130).fillna(False)
    df["vma"] = df["vma"].where(valid_speed)

    # Quelques accidents apparaissent plusieurs fois : on garde le premier lieu
    return df.drop_duplicates(subset="Num_Acc")


def build_dataset(years=YEARS):
    """Nettoie et fusionne caractéristiques et lieux pour toutes les années."""

    yearly_tables = []

    for year in years:
        caracteristiques = read_baac_file("caracteristiques", year)
        lieux = read_baac_file("lieux", year)

        if caracteristiques is None or lieux is None:
            continue

        accidents = clean_caracteristiques(caracteristiques, year).merge(
            clean_lieux(lieux), on="Num_Acc", how="left", validate="one_to_one"
        )
        yearly_tables.append(accidents)
        print(f"{year} : {len(accidents)} accidents")

    if not yearly_tables:
        raise FileNotFoundError(
            f"Aucun fichier BAAC dans {RAW_DATA_DIR}. Lancer d'abord scripts/get_data.py"
        )

    accidents = pd.concat(yearly_tables, ignore_index=True)

    # Réseau concerné par le 80 km/h : routes nationales ou départementales,
    # hors agglomération, à double sens (vma n'existe pas avant 2019)
    accidents["reseau_80"] = (
        accidents["catr"].isin([2, 3])
        & accidents["agg"].eq(1)
        & accidents["circ"].eq(2)
    ).fillna(False)
    accidents["apres_reforme"] = accidents["date"] >= DATE_REFORME

    return accidents


if __name__ == "__main__":
    accidents = build_dataset()

    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    destination = PROCESSED_DATA_DIR / "accidents.parquet"
    accidents.to_parquet(destination, index=False)

    print(f"\n{len(accidents)} accidents enregistrés dans {destination}")