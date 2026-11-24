"""
Nettoyage et fusion des données BAAC (caractéristiques, lieux, usagers, véhicules).

Lit les fichiers téléchargés par scripts/collecte.py dans data/raw/baac/<annee>/,
harmonise les formats qui changent selon les années, agrège usagers et véhicules
au niveau de l'accident (Num_Acc), puis fusionne les quatre tables.
Le résultat est enregistré dans data/processed/accidents.parquet.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_BAAC_DIR = ROOT_DIR / "data" / "raw" / "baac"
PROCESSED_DATA_DIR = ROOT_DIR / "data" / "processed"

YEARS = range(2010, 2025)

CARAC_COLUMNS = ["Num_Acc", "annee", "date", "heure", "lum", "agg",
                 "int", "atm", "col", "dep", "lat", "long"]
LIEUX_COLUMNS = ["Num_Acc", "catr", "circ", "nbv", "prof", "plan", "surf", "vma"]


def read_baac_file(category: str, year: int) -> pd.DataFrame | None:
    """Lit un fichier BAAC brut dans data/raw/baac/<year>/<category>.csv."""
    path = RAW_BAAC_DIR / str(year) / f"{category}.csv"

    if not path.exists():
        print(f"Fichier manquant : {path}")
        return None

    with path.open(encoding="latin-1") as file:
        header = file.readline()
    separator = ";" if ";" in header else "\t" if "\t" in header else ","

    try:
        df = pd.read_csv(path, sep=separator, dtype=str, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(path, sep=separator, dtype=str, encoding="latin-1")

    df = df.apply(lambda column: column.str.strip())
    return df.rename(columns={"Accident_Id": "Num_Acc"})


def to_code(column: pd.Series) -> pd.Series:
    """Convertit une colonne de codes en entiers ; -1 signifie 'non renseigné'."""
    values = pd.to_numeric(column, errors="coerce")
    return values.replace(-1, np.nan).astype("Int64")


def clean_departement(dep: pd.Series) -> pd.Series:
    """Met les codes département au format récent ('59', '2A', '971')."""
    dep = dep.str.upper()
    dep = dep.replace({"201": "2A", "202": "2B"})
    old_format = dep.str.len().eq(3) & dep.str.endswith("0")
    return dep.where(~old_format, dep.str[:2]).str.zfill(2)


def clean_caracteristiques(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Nettoie la table des caractéristiques d'une année."""
    df = df.copy()
    df["annee"] = year

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

    for column in ["lat", "long"]:
        values = pd.to_numeric(
            df[column].str.replace(",", ".", regex=False),
            errors="coerce",
        )
        if year < 2019:
            values = values / 100_000
        values = values.replace(0, np.nan)
        if column == "lat":
            values = values.where(values.between(-22, 52))
        else:
            values = values.where(values.between(-63, 10))
        df[column] = values

    return df[CARAC_COLUMNS].drop_duplicates(subset="Num_Acc")


def clean_lieux(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoie la table des lieux d'une année."""
    df = df.reindex(columns=LIEUX_COLUMNS).copy()
    for column in LIEUX_COLUMNS[1:]:
        df[column] = to_code(df[column])

    valid_speed = df["vma"].between(10, 130).fillna(False)
    df["vma"] = df["vma"].where(valid_speed)
    return df.drop_duplicates(subset="Num_Acc")


def clean_usagers(df: pd.DataFrame) -> pd.DataFrame:
    """Agrège les usagers par accident (1=Indemne, 2=Tué, 3=Blessé hosp., 4=Blessé léger)."""
    df = df.copy()
    df["grav"] = to_code(df["grav"])

    return df.groupby("Num_Acc", as_index=False).agg(
        nb_usagers=("grav", "size"),
        nb_tues=("grav", lambda s: (s == 2).sum()),
        nb_blesses_hosp=("grav", lambda s: (s == 3).sum()),
        nb_blesses_legers=("grav", lambda s: (s == 4).sum()),
    )


def clean_vehicules(df: pd.DataFrame) -> pd.DataFrame:
    """Agrège les véhicules impliqués par accident."""
    df = df.copy()
    df["catv"] = to_code(df["catv"])

    return df.groupby("Num_Acc", as_index=False).agg(
        nb_vehicules=("catv", "size"),
        implique_2rm=("catv", lambda s: s.isin([2, 30, 31, 32, 33, 34]).any()),
        implique_pl=("catv", lambda s: s.isin([13, 14, 15]).any()),
    )


def build_dataset(years: range = YEARS) -> pd.DataFrame:
    """Nettoie et fusionne les 4 tables BAAC pour toutes les années."""
    yearly_tables = []

    for year in years:
        carac = read_baac_file("caracteristiques", year)
        lieux = read_baac_file("lieux", year)
        usagers = read_baac_file("usagers", year)
        vehicules = read_baac_file("vehicules", year)

        if any(t is None for t in (carac, lieux, usagers, vehicules)):
            continue

        accidents = (
            clean_caracteristiques(carac, year)
            .merge(clean_lieux(lieux), on="Num_Acc", how="left", validate="one_to_one")
            .merge(clean_usagers(usagers), on="Num_Acc", how="left", validate="one_to_one")
            .merge(clean_vehicules(vehicules), on="Num_Acc", how="left", validate="one_to_one")
        )
        yearly_tables.append(accidents)
        print(f"{year} : {len(accidents)} accidents | {accidents['nb_tues'].sum()} tués")

    if not yearly_tables:
        raise FileNotFoundError(
            f"Aucun fichier BAAC dans {RAW_BAAC_DIR}. Lancer d'abord scripts/collecte.py"
        )

    accidents = pd.concat(yearly_tables, ignore_index=True)

    # Périmètre principal du 80 km/h : routes nationales (2) ou départementales (3),
    # hors agglomération (agg == 1), à double sens (circ == 2)
    # Type booléen « nullable » : accepte pd.NA (indispensable avec pandas 3)
    accidents["reseau_80"] = (
        accidents["catr"].isin([2, 3])
        & accidents["agg"].eq(1)
        & accidents["circ"].eq(2)
    ).astype("boolean")
    incomplet = accidents["catr"].isna() | accidents["agg"].isna() | accidents["circ"].isna()
    accidents.loc[incomplet, "reseau_80"] = pd.NA

    # Périmètre de contrôle ONISR : hors agglomération (agg == 1) et hors autoroute (catr != 1)
    accidents["hors_agg_hors_autoroute"] = accidents["agg"].eq(1) & accidents["catr"].ne(1)

    return accidents


if __name__ == "__main__":
    accidents = build_dataset()

    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    destination = PROCESSED_DATA_DIR / "accidents.parquet"
    accidents.to_parquet(destination, index=False)

    print(f"\n{len(accidents)} accidents enregistrés dans {destination}")