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

# Périmètres routiers utilisés dans les agrégations (voir masque_perimetre)
PERIMETRES = {
    "reseau_80": "RN et RD bidirectionnelles hors agglomération (réseau concerné par le 80 km/h)",
    "rd": "RD bidirectionnelles hors agglomération (réseau que les départements peuvent relever)",
    "temoin": "Agglomération, autoroutes et autres réseaux non concernés",
}


def masque_perimetre(accidents: pd.DataFrame, perimetre: str) -> pd.Series:
    """Renvoie un masque booléen (sans valeur manquante) des accidents du périmètre demandé.

    Parameters
    ----------
    accidents : pd.DataFrame
        Sortie de ``clean_data.build_dataset``.
    perimetre : str
        ``"reseau_80"``, ``"rd"`` ou ``"temoin"`` (voir ``PERIMETRES``). Un accident dont
        la catégorie de route, la localisation ou le régime de circulation est inconnu
        n'appartient à aucun périmètre.
    """
    if perimetre == "reseau_80":
        masque = accidents["reseau_80"]
    elif perimetre == "rd":
        masque = accidents["catr"].eq(3) & accidents["agg"].eq(1) & accidents["circ"].eq(2)
    elif perimetre == "temoin":
        masque = ~accidents["reseau_80"].astype("boolean")
    else:
        raise ValueError(f"Périmètre inconnu : {perimetre!r} (attendu : {list(PERIMETRES)})")
    return masque.astype("boolean").fillna(False).astype(bool)


def _agreger_par_mois(acc: pd.DataFrame, suffixe: str) -> pd.DataFrame:
    """Accidents, accidents mortels, tués et blessés hospitalisés par département et par mois."""
    acc = acc.assign(
        nb_tues=acc["nb_tues"].fillna(0),
        nb_blesses_hosp=acc["nb_blesses_hosp"].fillna(0),
        mortel=acc["nb_tues"].fillna(0).gt(0).astype(int),
    )
    agregat = acc.groupby(["dep", "date_mois"], as_index=False).agg(
        **{
            f"accidents_{suffixe}": ("Num_Acc", "size"),
            f"accidents_mortels_{suffixe}": ("mortel", "sum"),
            f"tues_{suffixe}": ("nb_tues", "sum"),
            f"blesses_hosp_{suffixe}": ("nb_blesses_hosp", "sum"),
        }
    )
    agregat[f"victimes_graves_{suffixe}"] = agregat[f"tues_{suffixe}"] + agregat[f"blesses_hosp_{suffixe}"]
    return agregat


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

    # 1. Agrégations mensuelles sur trois périmètres (voir PERIMETRES) :
    #    "80" = réseau concerné par le 80 km/h (RN + RD), "rd" = routes départementales
    #    seules (cœur de Q2), "temoin" = agglomération et autoroutes.
    panel = grille
    for suffixe, perimetre in [("80", "reseau_80"), ("rd", "rd"), ("temoin", "temoin")]:
        agregat = _agreger_par_mois(acc[masque_perimetre(acc, perimetre)], suffixe)
        panel = panel.merge(
            agregat, left_on=["code_dep", "date_mois"], right_on=["dep", "date_mois"], how="left"
        ).drop(columns="dep")

    cols_comptage = [
        f"{mesure}_{suffixe}"
        for suffixe in ("80", "rd", "temoin")
        for mesure in ("accidents", "accidents_mortels", "tues", "blesses_hosp", "victimes_graves")
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
    panel["taux_tues_rd"] = 100_000 * panel["tues_rd"] / panel["population"]

    return panel


# --- Chargement en cascade ---------------------------------------------------------------


def charger_ou_construire(reconstruire: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Renvoie ``(accidents, panel)`` en reconstruisant ce qui manque depuis les sources brutes.

    1. ``data/processed/accidents.parquet`` est relu s'il existe ; sinon les BAAC sont
       téléchargées (``collecte.telecharger_baac``) puis nettoyées (``clean_data.build_dataset``).
    2. ``data/processed/panel_dep.parquet`` est relu s'il existe et contient les colonnes
       attendues ; sinon il est reconstruit avec :func:`construire_panel`.

    Parameters
    ----------
    reconstruire : bool
        Ignore les fichiers existants et repart des données brutes.
    """
    chemin_accidents = DOSSIER_PROCESSED / "accidents.parquet"
    chemin_panel = DOSSIER_PROCESSED / "panel_dep.parquet"
    DOSSIER_PROCESSED.mkdir(parents=True, exist_ok=True)

    if chemin_accidents.exists() and not reconstruire:
        accidents = pd.read_parquet(chemin_accidents)
    else:
        from clean_data import build_dataset
        from collecte import telecharger_baac

        telecharger_baac()
        accidents = build_dataset()
        accidents.to_parquet(chemin_accidents, index=False)

    panel = None
    if chemin_panel.exists() and not reconstruire:
        panel = pd.read_parquet(chemin_panel)
        if "tues_rd" not in panel.columns:  # panel produit par une ancienne version du code
            panel = None
    if panel is None:
        panel = construire_panel(accidents)
        panel.to_parquet(chemin_panel, index=False)
    return accidents, panel


# --- Description de la base --------------------------------------------------------------


def tableau_controle_annuel(accidents: pd.DataFrame) -> pd.DataFrame:
    """Accidents, tués et contrôles de la règle du réseau concerné, par année (métropole).

    Returns
    -------
    pd.DataFrame
        Index ``annee`` ; colonnes ``accidents``, ``tues``, ``part_reseau_concerne``
        (part des accidents classés sur le réseau 80), ``part_reseau_inconnu`` (règle
        inapplicable faute d'information) et ``part_vma_80_90`` (parmi les accidents du
        réseau concerné dont la VMA est connue, part à 80 ou 90 km/h : contrôle de la règle,
        possible seulement depuis 2019).
    """
    acc = accidents[accidents["dep"].isin(DEPS_METRO)]
    concerne = masque_perimetre(acc, "reseau_80")
    vma_connue = concerne & acc["vma"].notna()
    controle_vma = acc["vma"].isin([80, 90]).astype(float).where(vma_connue)
    return pd.DataFrame(
        {
            "accidents": acc.groupby("annee").size(),
            "tues": acc.groupby("annee")["nb_tues"].sum(),
            "part_reseau_concerne": concerne.groupby(acc["annee"]).mean(),
            "part_reseau_inconnu": acc["reseau_80"].isna().groupby(acc["annee"]).mean(),
            "part_vma_80_90": controle_vma.groupby(acc["annee"]).mean(),
        }
    )


def valeurs_manquantes(accidents: pd.DataFrame, variables: list[str] | None = None) -> pd.DataFrame:
    """Part de valeurs manquantes (entre 0 et 1) par variable (lignes) et par année (colonnes)."""
    variables = variables or [
        "lum",
        "agg",
        "int",
        "atm",
        "col",
        "lat",
        "long",
        "catr",
        "circ",
        "nbv",
        "prof",
        "plan",
        "surf",
        "vma",
        "nb_tues",
    ]
    return accidents[variables].isna().groupby(accidents["annee"]).mean().T


def tues_mensuels_par_reseau(accidents: pd.DataFrame) -> pd.DataFrame:
    """Tués par mois sur le réseau concerné (colonne ``True``) et sur les autres réseaux (``False``).

    Les accidents dont le réseau est inconnu sont écartés. Entrée de ``graphiques.tracer_mensuel_reseau``.
    """
    acc = accidents[accidents["dep"].isin(DEPS_METRO) & accidents["reseau_80"].notna()]
    mois = acc["date"].dt.to_period("M").dt.to_timestamp().rename("date_mois")
    reseau = acc["reseau_80"].astype(bool).rename("reseau_80")
    return (
        acc.groupby([mois, reseau])["nb_tues"]
        .sum()
        .unstack("reseau_80", fill_value=0)
        .reindex(columns=[True, False])
    )



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