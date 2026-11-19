"""Statistiques descriptives sur le panel départemental mensuel.

Lit data/processed/panel_dep.parquet (produit par scripts/indicateurs.py) et calcule :

- l'évolution nationale des tués sur le réseau 80 et sur le réseau témoin ;
- les taux annuels pour 100 000 habitants par groupe (G80 / G90_partiel / G90_total) ;
- une comparaison avant / après relèvement, département par département, rapportée
  à l'évolution des départements restés à 80 km/h sur les mêmes mois.
"""

from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
CHEMIN_PANEL = RACINE / "data" / "processed" / "panel_dep.parquet"

GROUPES = ["G80", "G90_partiel", "G90_total"]
ANNEES_REFERENCE = [2015, 2016, 2017]  # trois années pleines avant le 80 km/h
DEBUT_80 = pd.Timestamp("2018-07-01")
FIN_PANEL = pd.Timestamp("2024-12-01")
# Mois de confinement strict, retirés des comparaisons avant / après
MOIS_CONFINEMENT = pd.to_datetime(["2020-03-01", "2020-04-01", "2020-05-01", "2020-11-01"])
COMPTAGES = ["accidents_80", "tues_80", "victimes_graves_80",
             "accidents_temoin", "tues_temoin", "victimes_graves_temoin"]


def charger_panel(chemin: Path = CHEMIN_PANEL) -> pd.DataFrame:
    """Charge le panel ; indique quels scripts lancer s'il n'existe pas encore."""
    if not Path(chemin).exists():
        raise FileNotFoundError(
            f"{chemin} introuvable : lancer scripts/clean_data.py puis scripts/indicateurs.py"
        )
    return pd.read_parquet(chemin)


def verifier_panel(panel: pd.DataFrame) -> pd.Series:
    """Contrôles de cohérence du panel (dimensions, doublons, valeurs manquantes)."""
    doublons = int(panel.duplicated(["code_dep", "date_mois"]).sum())
    if doublons:
        raise ValueError(f"{doublons} couples (département, mois) en double dans le panel")
    dep_annee = panel.drop_duplicates(["code_dep", "annee"])
    return pd.Series({
        "departements": panel["code_dep"].nunique(),
        "mois": panel["date_mois"].nunique(),
        "lignes": len(panel),
        "departements_sans_groupe": panel.loc[panel["groupe"].isna(), "code_dep"].nunique(),
        "dep_annees_sans_population": int(dep_annee["population"].isna().sum()),
        "dep_annees_sans_carburants": int(dep_annee["carburants_routiers_m3"].isna().sum()),
    })


def par_dep_annee(panel: pd.DataFrame) -> pd.DataFrame:
    """Agrège le panel mensuel au niveau département × année.

    Population et carburants sont annuels (répétés sur les 12 mois) : on garde
    la première valeur au lieu de les sommer.
    """
    return panel.groupby(["code_dep", "groupe", "annee"], as_index=False, dropna=False).agg(
        **{c: (c, "sum") for c in COMPTAGES},
        population=("population", "first"),
        carburants_routiers_m3=("carburants_routiers_m3", "first"),
    )


def bilan_national(panel: pd.DataFrame) -> pd.DataFrame:
    """Totaux annuels France métropolitaine et indices base 100 = moyenne 2015-2017.

    Les ventes de carburants servent d'indicateur indirect du trafic.
    """
    colonnes = COMPTAGES + ["carburants_routiers_m3"]
    annuel = par_dep_annee(panel).groupby("annee")[colonnes].sum(min_count=1)
    reference = annuel.loc[annuel.index.isin(ANNEES_REFERENCE)].mean()
    indices = (100 * annuel / reference).add_prefix("indice_")
    return annuel.join(indices)


def taux_par_groupe(panel: pd.DataFrame, variable: str = "tues_80") -> pd.DataFrame:
    """Taux annuel pour 100 000 habitants par groupe (total des victimes / total des habitants)."""
    dep_an = par_dep_annee(panel).dropna(subset=["population"])
    totaux = dep_an.groupby(["annee", "groupe"])[[variable, "population"]].sum()
    taux = 100_000 * totaux[variable] / totaux["population"]
    return taux.unstack("groupe").reindex(columns=GROUPES)


def ecart_au_groupe_80(taux: pd.DataFrame) -> pd.DataFrame:
    """Rapport du taux de chaque groupe à celui de G80, base 100 = moyenne 2015-2017.

    Une courbe qui monte après 2020 signifie que le groupe s'éloigne des
    départements restés à 80 km/h, dans le sens d'une hausse relative.
    """
    rapport = taux.div(taux["G80"], axis=0)
    reference = rapport.loc[rapport.index.isin(ANNEES_REFERENCE)].mean()
    return 100 * rapport / reference


def _somme_entre(serie: pd.Series, debut: pd.Timestamp, fin: pd.Timestamp) -> float:
    """Somme d'une série indexée par mois sur [debut, fin[."""
    return serie[(serie.index >= debut) & (serie.index < fin)].sum()


def avant_apres_releve(panel: pd.DataFrame, fenetre: int = 24,
                       variable: str = "tues_80") -> pd.DataFrame:
    """Compare, pour chaque département relevé, les victimes avant et après le relèvement.

    Fenêtres symétriques de ``h`` mois : [relèvement - h, relèvement[ et
    [relèvement, relèvement + h[. ``h`` vaut au plus ``fenetre``, est arrondi à un
    multiple de 12 (même saisonnalité des deux côtés) et est réduit pour que la
    fenêtre « avant » commence après le 1er juillet 2018 et que la fenêtre
    « après » s'arrête fin 2024. Le mois du relèvement compte dans « après ».
    Les mêmes mois sont sommés pour l'ensemble des départements G80 (témoins).
    """
    panel = panel[~panel["date_mois"].isin(MOIS_CONFINEMENT)]
    temoin_g80 = panel[panel["groupe"] == "G80"].groupby("date_mois")[variable].sum()
    reseau_temoin = variable.replace("_80", "_temoin")

    lignes = []
    traites = panel[panel["date_releve_eff"].notna()]
    for (code, nom, groupe, date), dep in traites.groupby(
        ["code_dep", "nom_dep", "groupe", "date_releve_eff"]
    ):
        debut = date.to_period("M").to_timestamp()
        mois_avant = (debut.year - DEBUT_80.year) * 12 + debut.month - DEBUT_80.month
        mois_apres = (FIN_PANEL.year - debut.year) * 12 + FIN_PANEL.month - debut.month + 1
        h = 12 * (min(fenetre, mois_avant, mois_apres) // 12)
        if h == 0:
            continue
        bornes_avant = (debut - pd.DateOffset(months=h), debut)
        bornes_apres = (debut, debut + pd.DateOffset(months=h))
        serie = dep.set_index("date_mois")
        lignes.append({
            "code_dep": code, "nom_dep": nom, "groupe": groupe,
            "date_releve": date, "horizon_mois": h,
            "avant": _somme_entre(serie[variable], *bornes_avant),
            "apres": _somme_entre(serie[variable], *bornes_apres),
            "g80_avant": _somme_entre(temoin_g80, *bornes_avant),
            "g80_apres": _somme_entre(temoin_g80, *bornes_apres),
            "temoin_avant": _somme_entre(serie[reseau_temoin], *bornes_avant),
            "temoin_apres": _somme_entre(serie[reseau_temoin], *bornes_apres),
        })

    tableau = pd.DataFrame(lignes)
    return _ajouter_evolutions(tableau).sort_values("ecart_pts").reset_index(drop=True)


def _ajouter_evolutions(tableau: pd.DataFrame) -> pd.DataFrame:
    """Évolutions en % et écart (en points) entre le département et les G80.

    Une évolution n'est pas calculable (NaN) si aucune victime n'est observée avant.
    """
    tableau = tableau.copy()
    for prefixe, colonne in [("", "evol_dep_pct"), ("g80_", "evol_g80_pct"),
                             ("temoin_", "evol_reseau_temoin_pct")]:
        avant = tableau[f"{prefixe}avant"].where(tableau[f"{prefixe}avant"] > 0)
        tableau[colonne] = 100 * (tableau[f"{prefixe}apres"] / avant - 1)
    tableau["ecart_pts"] = tableau["evol_dep_pct"] - tableau["evol_g80_pct"]
    return tableau


def synthese_avant_apres(tableau: pd.DataFrame) -> pd.DataFrame:
    """Regroupe le tableau avant / après par groupe (sommes des victimes, puis évolutions)."""
    sommes = tableau.groupby("groupe")[
        ["avant", "apres", "g80_avant", "g80_apres", "temoin_avant", "temoin_apres"]
    ].sum()
    synthese = _ajouter_evolutions(sommes)
    synthese.insert(0, "nb_departements", tableau.groupby("groupe").size())
    return synthese.round(1)


if __name__ == "__main__":
    panel = charger_panel()
    print(verifier_panel(panel), "\n")
    print(bilan_national(panel)[["tues_80", "tues_temoin", "indice_tues_80",
                                 "indice_tues_temoin", "indice_carburants_routiers_m3"]].round(1), "\n")
    print(ecart_au_groupe_80(taux_par_groupe(panel)).round(1), "\n")
    print(synthese_avant_apres(avant_apres_releve(panel)))