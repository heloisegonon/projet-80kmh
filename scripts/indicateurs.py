"""
Construction du panel départemental mensuel et affectation des groupes (G80 / G90).

Croise data/processed/accidents.parquet avec data/departements_90.csv
et les sources de contexte (population, carburants, radars) pour produire
data/processed/panel_dep.parquet.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from collecte import (
    charger_carburants,
    charger_departements_90,
    charger_population,
    charger_radars,
)

RACINE = Path(__file__).resolve().parents[1]
DOSSIER_PROCESSED = RACINE / "data" / "processed"

DATE_REFORME_80 = pd.Timestamp("2018-07-01")
FIN_PERIODE_BAAC = pd.Timestamp("2024-12-31")

# 96 départements de France métropolitaine (hors DOM)
DEPS_METRO = [f"{i:02d}" for i in range(1, 96) if i != 20] + ["2A", "2B"]


def affecter_groupes(dep_90: pd.DataFrame) -> pd.DataFrame:
    """Définit le groupe (G80, G90_partiel, G90_total) et la date effective sur 2010-2024.

    Les départements relevés après le 31/12/2024 (ex: Morbihan, Eure) sont classés G80.
    """
    df = dep_90.copy()
    df["code_dep"] = df["code_dep"].str.zfill(2)

    releve_sur_periode = df["releve"].fillna(False) & (df["date_releve"] <= FIN_PERIODE_BAAC)
    df["date_releve_eff"] = df["date_releve"].where(releve_sur_periode, pd.NaT)

    df["groupe"] = np.select(
        [
            releve_sur_periode & (df["etendue"] == "total"),
            releve_sur_periode & (df["etendue"] == "partiel"),
        ],
        ["G90_total", "G90_partiel"],
        default="G80",
    )
    return df


def verifier_coherence_onisr(accidents: pd.DataFrame, dep_90: pd.DataFrame) -> pd.DataFrame:
    """Compare les tués hors agglomération hors autoroute (2019 et 2022) aux chiffres ONISR."""
    ha = accidents[accidents["hors_agg_hors_autoroute"] & accidents["dep"].isin(DEPS_METRO)]

    tues_calc = (
        ha[ha["annee"].isin([2019, 2022])]
        .groupby(["dep", "annee"])["nb_tues"]
        .sum()
        .unstack(fill_value=0)
        .rename(columns={2019: "tues_2019_calc", 2022: "tues_2022_calc"})
    )

    comp = dep_90[["code_dep", "nom_dep", "tues_ha_2019_onisr", "tues_ha_2022_onisr"]].merge(
        tues_calc, left_on="code_dep", right_index=True, how="left"
    )
    comp["ecart_2019"] = comp["tues_2019_calc"] - comp["tues_ha_2019_onisr"]
    comp["ecart_2022"] = comp["tues_2022_calc"] - comp["tues_ha_2022_onisr"]
    return comp


def compter_radars_actifs(radars: pd.DataFrame, grille: pd.DataFrame) -> pd.DataFrame:
    """Compte le nombre de radars fixes en service par département et par mois."""
    rad = radars.dropna(subset=["date_mise_en_service"]).copy()
    # Extraction du code département depuis les 2 premiers caractères de id_radar si dispo,
    # sinon rattachement spatial via contours cartiflette
    from collecte import charger_contours
    import geopandas as gpd

    contours = charger_contours()
    gdf_rad = gpd.GeoDataFrame(
        rad,
        geometry=gpd.points_from_xy(rad["lon"], rad["lat"]),
        crs=4326,
    )
    rad_dep = gpd.sjoin(gdf_rad, contours[["code_dep", "geometry"]], how="inner", predicate="within")
    rad_dep["mois_service"] = rad_dep["date_mise_en_service"].dt.to_period("M").dt.to_timestamp()

    # Cumul mensuel par département
    ajouts = (
        rad_dep.groupby(["code_dep", "mois_service"])
        .size()
        .rename("nouveaux_radars")
        .reset_index()
    )
    panel_rad = grille[["code_dep", "date_mois"]].merge(
        ajouts, left_on=["code_dep", "date_mois"], right_on=["code_dep", "mois_service"], how="left"
    )
    panel_rad["nouveaux_radars"] = panel_rad["nouveaux_radars"].fillna(0)
    panel_rad["nb_radars_actifs"] = panel_rad.groupby("code_dep")["nouveaux_radars"].cumsum()
    return panel_rad[["code_dep", "date_mois", "nb_radars_actifs"]]


def construire_panel(accidents: pd.DataFrame) -> pd.DataFrame:
    """Construit le panel mensuel (code_dep, date_mois) sur 2010-2024."""
    acc = accidents[accidents["dep"].isin(DEPS_METRO)].copy()
    acc["date_mois"] = acc["date"].dt.to_period("M").dt.to_timestamp()

    # Grille complète 96 départements x 180 mois (2010-01 à 2024-12)
    mois_range = pd.date_range("2010-01-01", "2024-12-01", freq="MS")
    grille = pd.MultiIndex.from_product(
        [DEPS_METRO, mois_range], names=["code_dep", "date_mois"]
    ).to_frame(index=False)
    grille["annee"] = grille["date_mois"].dt.year
    grille["mois"] = grille["date_mois"].dt.month

    # 1. Agrégation sur le réseau cible (routes bidirectionnelles hors agglo)
    cible = (
        acc[acc["reseau_80"].fillna(False)]
        .groupby(["dep", "date_mois"], as_index=False)
        .agg(
            accidents_80=("Num_Acc", "size"),
            tues_80=("nb_tues", "sum"),
            blesses_hosp_80=("nb_blesses_hosp", "sum"),
            victimes_graves_80=("nb_tues", lambda s: s.sum()),  # complété juste après
        )
    )
    cible["victimes_graves_80"] = cible["tues_80"] + cible["blesses_hosp_80"]

    # 2. Agrégation sur le réseau témoin (autoroutes + agglomération)
    temoin = (
        acc[~acc["reseau_80"].fillna(True)]
        .groupby(["dep", "date_mois"], as_index=False)
        .agg(
            accidents_temoin=("Num_Acc", "size"),
            tues_temoin=("nb_tues", "sum"),
            blesses_hosp_temoin=("nb_blesses_hosp", "sum"),
        )
    )
    temoin["victimes_graves_temoin"] = temoin["tues_temoin"] + temoin["blesses_hosp_temoin"]

    panel = (
        grille
        .merge(cible, left_on=["code_dep", "date_mois"], right_on=["dep", "date_mois"], how="left")
        .drop(columns="dep")
        .merge(temoin, left_on=["code_dep", "date_mois"], right_on=["dep", "date_mois"], how="left")
        .drop(columns="dep")
    )

    cols_comptage = [
        "accidents_80", "tues_80", "blesses_hosp_80", "victimes_graves_80",
        "accidents_temoin", "tues_temoin", "blesses_hosp_temoin", "victimes_graves_temoin",
    ]
    panel[cols_comptage] = panel[cols_comptage].fillna(0).astype(int)

    # 3. Ajout des groupes G80 / G90 et variables de traitement
    dep_90 = affecter_groupes(charger_departements_90())
    panel = panel.merge(
        dep_90[["code_dep", "nom_dep", "typologie_cerema", "groupe", "etendue", "part_releve", "date_releve_eff"]],
        on="code_dep",
        how="left",
    )

    panel["post_80"] = (panel["date_mois"] >= DATE_REFORME_80).astype(int)
    panel["post_90"] = (
        panel["date_releve_eff"].notna() & (panel["date_mois"] >= panel["date_releve_eff"])
    ).astype(int)
    panel["traite_90_total"] = ((panel["groupe"] == "G90_total") & (panel["post_90"] == 1)).astype(int)

    # 4. Variables de contexte (population, carburants, radars)
    pop = charger_population()
    carb = charger_carburants()[["code_dep", "annee", "carburants_routiers_m3"]]
    radars = compter_radars_actifs(charger_radars(), grille)

    panel = (
        panel
        .merge(pop, on=["code_dep", "annee"], how="left")
        .merge(carb, on=["code_dep", "annee"], how="left")
        .merge(radars, on=["code_dep", "date_mois"], how="left")
    )

    # Taux pour 100 000 habitants
    panel["taux_tues_80"] = 100_000 * panel["tues_80"] / panel["population"]
    panel["taux_graves_80"] = 100_000 * panel["victimes_graves_80"] / panel["population"]

    return panel


if __name__ == "__main__":
    accidents = pd.read_parquet(DOSSIER_PROCESSED / "accidents.parquet")
    dep_90 = charger_departements_90()

    comp = verifier_coherence_onisr(accidents, dep_90)
    print("Écart médian vs ONISR (2019 / 2022) :", comp["ecart_2019"].median(), "/", comp["ecart_2022"].median())
    print("Total tués HA 2019 (nous vs ONISR) :", comp["tues_2019_calc"].sum(), "vs", comp["tues_ha_2019_onisr"].sum())
    print("Total tués HA 2022 (nous vs ONISR) :", comp["tues_2022_calc"].sum(), "vs", comp["tues_ha_2022_onisr"].sum())

    panel = construire_panel(accidents)
    destination = DOSSIER_PROCESSED / "panel_dep.parquet"
    panel.to_parquet(destination, index=False)
    print(f"\nPanel enregistré : {panel.shape} dans {destination}")