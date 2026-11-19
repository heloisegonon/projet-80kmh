"""Graphiques du rapport, construits à partir des tableaux de scripts/data_analysis.py.

Chaque fonction renvoie la figure matplotlib (affichée dans le notebook, ou
enregistrée avec ``fig.savefig``).
"""

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch

COULEURS = {"G80": "#4C72B0", "G90_partiel": "#DD8452", "G90_total": "#C44E52"}
LIBELLES = {"G80": "Restés à 80 km/h", "G90_partiel": "Retour partiel à 90 km/h",
            "G90_total": "Retour (quasi) total à 90 km/h"}


def _reperes(ax: plt.Axes) -> None:
    """Marque la réforme (1er juillet 2018) et l'année 2020 (confinements) sur un axe annuel."""
    ax.axvline(2018, color="grey", ls="--", lw=1)
    ax.annotate("80 km/h\n(1er juillet 2018)", (2018, 1), xycoords=("data", "axes fraction"),
                xytext=(4, -4), textcoords="offset points", va="top", fontsize=8, color="grey")
    ax.axvspan(2019.5, 2020.5, color="grey", alpha=0.12, lw=0)
    ax.set_xticks(range(2010, 2025, 2))
    ax.spines[["top", "right"]].set_visible(False)


def fig_bilan_national(bilan: pd.DataFrame) -> plt.Figure:
    """Indices (base 100 = 2015-2017) des tués sur le réseau 80, le réseau témoin et du trafic."""
    fig, ax = plt.subplots(figsize=(9, 4.5))
    series = {"indice_tues_80": ("Tués, réseau 80 (RN/RD bidirectionnelles hors agglo.)", "#C44E52"),
              "indice_tues_temoin": ("Tués, réseau témoin (agglo. et autoroutes)", "#4C72B0"),
              "indice_carburants_routiers_m3": ("Ventes de carburants routiers (trafic)", "#8C8C8C")}
    for colonne, (libelle, couleur) in series.items():
        ax.plot(bilan.index, bilan[colonne], marker="o", ms=3, label=libelle, color=couleur)
    ax.axhline(100, color="black", lw=0.6)
    _reperes(ax)
    ax.set(xlabel="Année", ylabel="Indice (base 100 = moyenne 2015-2017)",
           title="France métropolitaine : tués selon le réseau et trafic")
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    return fig


def fig_par_groupe(tableau: pd.DataFrame, ylabel: str, titre: str) -> plt.Figure:
    """Une courbe par groupe (sortie de ``taux_par_groupe`` ou de ``ecart_au_groupe_80``)."""
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for groupe in tableau.columns:
        ax.plot(tableau.index, tableau[groupe], marker="o", ms=3,
                color=COULEURS[groupe], label=LIBELLES[groupe])
    _reperes(ax)
    ax.set(xlabel="Année", ylabel=ylabel, title=titre)
    ax.legend(frameon=False, fontsize=8)
    return fig


def fig_avant_apres(tableau: pd.DataFrame,
                    titre: str = "Tués sur le réseau 80 : avant / après le retour à 90 km/h") -> plt.Figure:
    """Écart d'évolution (en points) entre chaque département relevé et les G80, mêmes mois."""
    tableau = tableau.dropna(subset=["ecart_pts"]).sort_values("ecart_pts")
    fig, ax = plt.subplots(figsize=(7, 0.22 * len(tableau) + 1.5))
    ax.barh(tableau["nom_dep"], tableau["ecart_pts"], color=tableau["groupe"].map(COULEURS))
    ax.axvline(0, color="black", lw=0.8)
    ax.legend(handles=[Patch(color=COULEURS[g], label=LIBELLES[g]) for g in ["G90_partiel", "G90_total"]],
              frameon=False, fontsize=8, loc="lower right")
    ax.set(xlabel="Évolution du département − évolution des G80 (points de %)",
           title=titre)
    ax.tick_params(axis="y", labelsize=7)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig