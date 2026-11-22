"""Fonctions de visualisation réutilisables par le rapport.

Palette : trois couleurs catégorielles validées pour le daltonisme (bleu, orange,
vert d'eau), toujours dans le même ordre et toujours associées au même groupe ;
une rampe bleue pour les intensités (cartes, heatmap) ; un couple bleu/rouge
autour d'un gris neutre pour les évolutions (baisse / hausse).
"""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.transforms import offset_copy

SURFACE = "#fcfcfb"
ENCRE = "#0b0b0b"
ENCRE_SECONDAIRE = "#52514e"
GRILLE = "#e4e3df"
NEUTRE = "#b5b4ae"

COULEURS_GROUPES = {"G80": "#2a78d6", "G90_partiel": "#eb6834", "G90_total": "#1baf7a"}
LIBELLES_GROUPES = {
    "G80": "Restés à 80 km/h",
    "G90_partiel": "Relevés à 90 km/h (partiel)",
    "G90_total": "Relevés à 90 km/h (total)",
}
COULEURS_SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]

RAMPE_BLEUE = LinearSegmentedColormap.from_list(
    "bleu", ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
)
DIVERGENTE = LinearSegmentedColormap.from_list(
    "baisse_hausse", ["#104281", "#3987e5", "#9ec5f4", "#f0efec", "#f2a3a2", "#e34948", "#a32a2a"]
)

DATE_80KMH = pd.Timestamp("2018-07-01")
DATE_LOM = pd.Timestamp("2020-01-01")


def appliquer_style() -> None:
    """Style commun : axes discrets, traits de 2 px, couleurs des séries dans l'ordre validé."""
    mpl.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "axes.edgecolor": NEUTRE,
            "axes.labelcolor": ENCRE_SECONDAIRE,
            "axes.titlecolor": ENCRE,
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": GRILLE,
            "grid.linewidth": 0.8,
            "xtick.color": ENCRE_SECONDAIRE,
            "ytick.color": ENCRE_SECONDAIRE,
            "text.color": ENCRE,
            "lines.linewidth": 2,
            "lines.markersize": 6,
            "legend.frameon": False,
            "axes.prop_cycle": mpl.cycler(color=COULEURS_SERIES),
            "figure.dpi": 110,
        }
    )


def _etiquettes_fin(ax, points: list[tuple]) -> None:
    """Étiquettes directes en bout de courbe, écartées verticalement pour ne pas se chevaucher.

    ``points`` : liste de ``(x, y, texte, couleur)``. À appeler une fois les limites de l'axe fixées.
    La pastille reste sur la vraie valeur ; seul le texte est décalé. Le texte est en encre,
    la couleur de la série n'est portée que par la pastille.
    """
    bas, haut = ax.get_ylim()
    ecart = (haut - bas) * 0.06
    decalage = offset_copy(ax.transData, fig=ax.figure, x=9, y=0, units="points")
    precedent = None
    for x, y, texte, couleur in sorted(points, key=lambda point: point[1]):
        y_texte = y if precedent is None else max(y, precedent + ecart)
        precedent = y_texte
        ax.plot([x], [y], "o", color=couleur, markersize=7, markeredgecolor=SURFACE, markeredgewidth=1.5)
        ax.text(x, y_texte, texte, transform=decalage, va="center", fontsize=9, color=ENCRE, clip_on=False)


def _legende_dessous(ax, ncol: int = 3) -> None:
    """Légende sous le graphique, pour ne jamais masquer de données."""
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=ncol)


def _repere_vertical(ax, x, texte: str) -> None:
    """Ligne verticale pointillée annotée en haut du graphique."""
    ax.axvline(x, color=ENCRE_SECONDAIRE, ls="--", lw=1)
    ax.annotate(
        texte,
        (x, 1),
        xycoords=("data", "axes fraction"),
        xytext=(4, -4),
        textcoords="offset points",
        va="top",
        fontsize=8.5,
        color=ENCRE_SECONDAIRE,
    )


# --- 7.1 Description de la base --------------------------------------------------


def tracer_description_annuelle(controle: pd.DataFrame):
    """Accidents, tués et part du réseau concerné par an (trois petits graphiques, une échelle chacun)."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    annees = controle.index
    mesures = [
        (controle["accidents"] / 1000, "Accidents corporels (milliers)", "Milliers d'accidents"),
        (controle["tues"], "Tués (à 30 jours)", "Tués"),
        (100 * controle["part_reseau_concerne"], "Part des accidents sur le réseau concerné", "%"),
    ]
    for ax, (valeurs, titre, ylabel) in zip(axes, mesures):
        if ylabel == "%":
            ax.plot(annees, valeurs, marker="o", color=COULEURS_SERIES[0])
            ax.set_ylim(0, max(30, valeurs.max() * 1.2))
        else:
            ax.bar(annees, valeurs, color=COULEURS_SERIES[0], edgecolor=SURFACE, linewidth=1.5, width=0.8)
        _repere_vertical(ax, 2018.5, "nouveau\nformat")
        ax.set(title=titre, ylabel=ylabel, xlabel="Année")
        ax.grid(axis="x", visible=False)
    fig.tight_layout()
    return fig


def heatmap_manquants(manquants: pd.DataFrame, ax=None):
    """Part de valeurs manquantes par variable (lignes) et par année (colonnes)."""
    ax = ax or plt.subplots(figsize=(13, 0.5 * len(manquants) + 1.5))[1]
    image = ax.imshow(manquants.values * 100, cmap=RAMPE_BLEUE, vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(manquants.shape[1]), manquants.columns)
    ax.set_yticks(range(manquants.shape[0]), manquants.index)
    ax.grid(False)
    for (i, j), valeur in np.ndenumerate(manquants.values * 100):
        if valeur >= 1:
            ax.text(
                j,
                i,
                f"{valeur:.0f}",
                ha="center",
                va="center",
                fontsize=8,
                color=SURFACE if valeur > 50 else ENCRE,
            )
    plt.colorbar(image, ax=ax, label="% de valeurs manquantes", shrink=0.8)
    ax.set_title("Valeurs manquantes par variable et par année (%)")
    return ax


# --- G1 à G5 ------------------------------------------------------------------------


def tracer_mensuel_reseau(mensuel: pd.DataFrame, ax=None, fenetre: int = 12):
    """G1 : tués par mois sur le réseau concerné et les autres réseaux (moyenne mobile).

    Parameters
    ----------
    mensuel : pd.DataFrame
        Index = mois, colonnes = ``True`` (réseau concerné) / ``False`` (autres réseaux).
    fenetre : int
        Largeur de la moyenne mobile en mois.
    """
    ax = ax or plt.subplots(figsize=(12, 5))[1]
    libelles = {True: "Réseau concerné par le 80 km/h", False: "Autres réseaux"}
    points = []
    for couleur, colonne in zip(COULEURS_SERIES, mensuel.columns):
        lisse = mensuel[colonne].rolling(fenetre, center=True).mean()
        ax.plot(mensuel.index, mensuel[colonne], color=couleur, alpha=0.25, lw=1)
        ax.plot(mensuel.index, lisse, color=couleur, label=f"{libelles.get(colonne, colonne)}")
        dernier = lisse.last_valid_index()
        points.append((dernier, lisse[dernier], libelles.get(colonne, colonne), couleur))
    _repere_vertical(ax, DATE_80KMH, "80 km/h\n(1/7/2018)")
    _repere_vertical(ax, DATE_LOM, "LOM, Covid\n(2020)")
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.set_xlim(right=mensuel.index.max() + pd.DateOffset(months=3))
    ax.set(
        title=f"G1. Tués par mois selon le réseau (trait fin : brut ; trait épais : moyenne mobile {fenetre} mois)",
        xlabel="Mois",
        ylabel="Tués par mois",
    )
    _etiquettes_fin(ax, points)
    _legende_dessous(ax, ncol=2)
    return ax


def carte_groupes(contours, groupes: pd.DataFrame, ax=None):
    """G2 : carte des départements métropolitains selon leur groupe."""
    carte = contours.merge(groupes, on="code_dep", how="inner")
    ax = ax or plt.subplots(figsize=(8, 8))[1]
    for groupe, couleur in COULEURS_GROUPES.items():
        sous = carte[carte["groupe"] == groupe]
        if not sous.empty:
            sous.plot(ax=ax, color=couleur, edgecolor=SURFACE, linewidth=0.6)
    effectifs = groupes["groupe"].value_counts()
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in COULEURS_GROUPES.values()]
    libelles = [f"{LIBELLES_GROUPES[g]} : {effectifs.get(g, 0)}" for g in COULEURS_GROUPES]
    ax.legend(handles, libelles, loc="lower left")
    ax.set_axis_off()
    ax.set_title("Vitesse sur le réseau départemental au 31/12/2024")
    return ax


def tracer_calendrier(groupes: pd.DataFrame, ax=None):
    """G3 : date du premier relèvement de chaque département relevé."""
    releves = groupes.dropna(subset=["date_releve"]).sort_values("date_releve")
    ax = ax or plt.subplots(figsize=(8, 10))[1]
    for groupe, couleur in COULEURS_GROUPES.items():
        sous = releves[releves["groupe"] == groupe]
        if sous.empty:
            continue
        ax.scatter(
            sous["date_releve"],
            sous["nom_dep"],
            color=couleur,
            s=40,
            edgecolor=SURFACE,
            linewidth=1,
            label=LIBELLES_GROUPES[groupe],
            zorder=3,
        )
    ax.set(title="Date du premier relèvement à 90 km/h", xlabel="Date", ylabel="")
    ax.tick_params(axis="y", labelsize=7)
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right")
    return ax


def tracer_series_groupes_ic(serie: pd.DataFrame, titre: str, ylabel: str, ax=None):
    """G4 : indice par groupe (base 100) avec intervalle de Poisson à 95 % en bande.

    ``serie`` est la sortie de :func:`src.indicateurs.serie_groupes_ic`.
    """
    ax = ax or plt.subplots(figsize=(11, 5.5))[1]
    points = []
    for groupe, couleur in COULEURS_GROUPES.items():
        sous = serie[serie["groupe"] == groupe].sort_values("periode")
        if sous.empty:
            continue
        ax.fill_between(sous["periode"], sous["ic_bas"], sous["ic_haut"], color=couleur, alpha=0.12, lw=0)
        ax.plot(sous["periode"], sous["indice"], marker="o", color=couleur, label=LIBELLES_GROUPES[groupe])
        dernier = sous.iloc[-1]
        points.append((dernier["periode"], dernier["indice"], LIBELLES_GROUPES[groupe], couleur))
    ax.axhline(100, color=ENCRE_SECONDAIRE, lw=0.8)
    ax.axvspan(2019.5, 2020.5, color=GRILLE, alpha=0.6, lw=0)
    ax.annotate(
        "2020 : Covid,\npremiers relèvements",
        (2020, 0.02),
        xycoords=("data", "axes fraction"),
        ha="center",
        fontsize=8.5,
        color=ENCRE_SECONDAIRE,
    )
    _repere_vertical(ax, 2018.5, "80 km/h")
    ax.set_xlim(right=serie["periode"].max() + 0.4)
    ax.set(title=titre, xlabel="Année", ylabel=ylabel)
    _etiquettes_fin(ax, points)
    _legende_dessous(ax)
    return ax


def tracer_series_groupes(serie: pd.DataFrame, titre: str, ylabel: str, ax=None):
    """Courbes par groupe (index = période, colonnes = groupes), base 100, étiquettes directes."""
    ax = ax or plt.subplots(figsize=(10, 5))[1]
    points = []
    for groupe in serie.columns:
        couleur = COULEURS_GROUPES.get(groupe)
        ax.plot(
            serie.index, serie[groupe], marker="o", color=couleur, label=LIBELLES_GROUPES.get(groupe, groupe)
        )
        points.append(
            (serie.index[-1], serie[groupe].iloc[-1], LIBELLES_GROUPES.get(groupe, groupe), couleur)
        )
    ax.axhline(100, color=ENCRE_SECONDAIRE, lw=0.8)
    ax.axvspan(2019.5, 2020.5, color=GRILLE, alpha=0.6, lw=0)
    ax.set_xlim(right=serie.index.max() + 0.4)
    ax.set(title=titre, xlabel="Année", ylabel=ylabel)
    _etiquettes_fin(ax, points)
    _legende_dessous(ax)
    return ax


def tracer_evenement(evenement: pd.DataFrame, ax=None):
    """G5 : indice moyen par département selon l'année relative au relèvement, par groupe."""
    ax = ax or plt.subplots(figsize=(11, 5))[1]
    points = []
    for groupe, couleur in COULEURS_GROUPES.items():
        sous = evenement[evenement["groupe"] == groupe].sort_values("annee_relative")
        if sous.empty:
            continue
        ax.fill_between(
            sous["annee_relative"], sous["ic_bas"], sous["ic_haut"], color=couleur, alpha=0.12, lw=0
        )
        ax.plot(
            sous["annee_relative"], sous["indice"], marker="o", color=couleur, label=LIBELLES_GROUPES[groupe]
        )
        fin = sous.iloc[-1]
        points.append((fin["annee_relative"], fin["indice"], LIBELLES_GROUPES[groupe], couleur))
    ax.axhline(100, color=ENCRE_SECONDAIRE, lw=0.8)
    _repere_vertical(ax, -0.5, "relèvement")
    ax.set_xlim(right=evenement["annee_relative"].max() + 0.4)
    ax.set_xticks(sorted(evenement["annee_relative"].unique()))
    ax.set(
        title="G5. Tués par département relevé, selon le nombre d'années depuis le relèvement",
        xlabel="Années depuis le relèvement (0 = année du relèvement)",
        ylabel="Indice (moyenne des années −3 à −1 = 100)",
    )
    _etiquettes_fin(ax, points)
    _legende_dessous(ax, ncol=2)
    return ax


# --- G6 : évolution par catégorie (H4) ---------------------------------------------------


def tracer_evolution_categories(tableau: pd.DataFrame, categorie: str, libelles: dict, titre: str, ax=None):
    """G6 : évolution des tués (après / avant, en %) par catégorie et par groupe, en barres groupées.

    ``tableau`` est la sortie de :func:`src.indicateurs.evolution_par_categorie`.
    Chaque catégorie affiche le nombre de tués par an avant, pour situer son poids.
    """
    categories = [c for c in libelles if c in set(tableau[categorie])]
    groupes = [g for g in COULEURS_GROUPES if g in set(tableau["groupe"])]
    ax = ax or plt.subplots(figsize=(11, 1.2 * len(categories) + 1.5))[1]
    hauteur = 0.8 / len(groupes)
    poids = tableau.groupby(categorie)["tues_par_an_avant"].sum()
    for k, groupe in enumerate(groupes):
        sous = tableau[tableau["groupe"] == groupe].set_index(categorie).reindex(categories)
        positions = np.arange(len(categories)) + (k - (len(groupes) - 1) / 2) * hauteur
        ax.barh(
            positions,
            sous["evolution_%"],
            height=hauteur,
            color=COULEURS_GROUPES[groupe],
            edgecolor=SURFACE,
            linewidth=1.5,
            label=LIBELLES_GROUPES[groupe],
        )
        for y, valeur in zip(positions, sous["evolution_%"]):
            if pd.notna(valeur):
                ax.annotate(
                    f"{valeur:+.0f} %",
                    (valeur, y),
                    xytext=(4 if valeur >= 0 else -4, 0),
                    textcoords="offset points",
                    ha="left" if valeur >= 0 else "right",
                    va="center",
                    fontsize=8,
                    color=ENCRE_SECONDAIRE,
                )
    ax.set_yticks(
        range(len(categories)), [f"{libelles[c]}\n({poids[c]:.0f} tués/an avant)" for c in categories]
    )
    ax.invert_yaxis()
    ax.axvline(0, color=ENCRE, lw=0.8)
    ax.grid(axis="y", visible=False)
    limite = np.nanmax(np.abs(tableau["evolution_%"].replace([np.inf, -np.inf], np.nan))) * 1.25
    ax.set_xlim(-limite, limite)
    ax.set(title=titre, xlabel="Évolution des tués par an, 2021-2024 par rapport à 2015-2019 (%)")
    _legende_dessous(ax)
    return ax


# --- G7 : cartes avant / après ------------------------------------------------------------


def cartes_avant_apres(contours, taux: pd.DataFrame, limite_evolution: float = 60):
    """G7 : taux de tués par million d'habitants avant, après (même échelle), et évolution."""
    carte = contours.merge(taux, on="code_dep", how="inner")
    fig, axes = plt.subplots(1, 3, figsize=(17, 6.5))
    vmax = np.nanpercentile(carte[["taux_avant", "taux_apres"]].to_numpy(dtype=float), 98)
    for ax, colonne, titre in (
        (axes[0], "taux_avant", "Avant : 2015-2019"),
        (axes[1], "taux_apres", "Après : 2021-2024"),
    ):
        carte.plot(
            column=colonne, ax=ax, cmap=RAMPE_BLEUE, vmin=0, vmax=vmax, edgecolor=SURFACE, linewidth=0.4
        )
        ax.set_title(titre)
        ax.set_axis_off()
    echelle = mpl.cm.ScalarMappable(cmap=RAMPE_BLEUE, norm=mpl.colors.Normalize(0, vmax))
    fig.colorbar(
        echelle,
        ax=axes[:2],
        orientation="horizontal",
        shrink=0.5,
        pad=0.02,
        label="Tués par million d'habitants et par an (RD hors agglomération)",
    )

    norme = TwoSlopeNorm(vmin=-limite_evolution, vcenter=0, vmax=limite_evolution)
    carte.assign(evol=carte["evolution_%"].astype(float).clip(-limite_evolution, limite_evolution)).plot(
        column="evol",
        ax=axes[2],
        cmap=DIVERGENTE,
        norm=norme,
        edgecolor=SURFACE,
        linewidth=0.4,
        missing_kwds={"color": GRILLE},
    )
    axes[2].set_title("Évolution (%)")
    axes[2].set_axis_off()
    fig.colorbar(
        mpl.cm.ScalarMappable(cmap=DIVERGENTE, norm=norme),
        ax=axes[2],
        orientation="horizontal",
        shrink=0.8,
        pad=0.02,
        label=f"Évolution du taux (%), bornée à ±{limite_evolution:.0f}",
    )
    fig.suptitle(
        "G7. Mortalité sur les routes départementales hors agglomération, par département",
        x=0.02,
        ha="left",
        fontweight="bold",
    )
    return fig


# --- Robustesse et radars -------------------------------------------------------------------


def tracer_robustesse(robustesse: pd.DataFrame, ax=None):
    """Effet estimé (points de %) dans chaque configuration : une ligne par configuration."""
    configurations = robustesse.index.get_level_values(0).unique()
    ax = ax or plt.subplots(figsize=(10, 0.7 * len(configurations) + 1.5))[1]
    styles = {
        "total": (COULEURS_GROUPES["G90_total"], "o"),
        "total + partiel": (COULEURS_GROUPES["G90_partiel"], "s"),
    }
    for etiquette, (couleur, marqueur) in styles.items():
        valeurs = robustesse.xs(etiquette, level=1)["effet_points_%"].reindex(configurations)
        ax.scatter(
            valeurs,
            range(len(configurations)),
            color=couleur,
            marker=marqueur,
            s=70,
            edgecolor=SURFACE,
            linewidth=1.5,
            zorder=3,
            label=f"Groupe traité : {etiquette}",
        )
        for y, v in enumerate(valeurs):
            ax.annotate(
                f"{v:+.1f}",
                (v, y),
                xytext=(0, 9),
                textcoords="offset points",
                ha="center",
                fontsize=8,
                color=ENCRE_SECONDAIRE,
            )
    ax.axvline(0, color=ENCRE, lw=0.8)
    ax.set_yticks(range(len(configurations)), configurations)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.set(
        title="Robustesse. Effet estimé du relèvement selon la configuration (différence de différences)",
        xlabel="Écart d'évolution des tués avec les départements restés à 80 km/h (points de %)",
    )
    ax.margins(x=0.08, y=0.15)
    _legende_dessous(ax, ncol=2)
    return ax


def tracer_radars(radars_proches: pd.DataFrame, effectif_min: int = 20):
    """G8 : accidents à moins de 1 km des radars avant / après mise en service, par type de radar."""
    donnees = radars_proches.copy()
    effectifs = donnees["type_radar"].value_counts()
    donnees["type"] = donnees["type_radar"].where(
        donnees["type_radar"].map(effectifs) >= effectif_min, "Autres"
    )
    donnees = donnees[donnees["type"] != "Autres"]
    totaux = donnees.groupby("type")[["avant", "apres", "attendu_apres"]].sum()
    totaux.loc["Ensemble"] = totaux.sum()
    evolution = pd.DataFrame(
        {
            "Observée": 100 * (totaux["apres"] / totaux["avant"] - 1),
            "Attendue (tendance nationale)": 100 * (totaux["attendu_apres"] / totaux["avant"] - 1),
        }
    )
    n = donnees["type"].value_counts()
    n["Ensemble"] = len(donnees)

    fig, axes = plt.subplots(1, 2, figsize=(15, 5), gridspec_kw={"width_ratios": [1.1, 1]})
    positions = np.arange(len(evolution))
    for k, (serie, couleur, hachure) in enumerate(
        (("Observée", COULEURS_SERIES[0], None), ("Attendue (tendance nationale)", SURFACE, "///"))
    ):
        barres = axes[0].bar(
            positions + (k - 0.5) * 0.38,
            evolution[serie],
            width=0.38,
            color=couleur,
            hatch=hachure,
            edgecolor=COULEURS_SERIES[0] if hachure else SURFACE,
            linewidth=1.5,
            label=serie,
        )
        axes[0].bar_label(barres, fmt="%+.1f %%", fontsize=8, color=ENCRE_SECONDAIRE, padding=2)
    axes[0].set_xticks(positions, [f"{t}\n({n[t]} radars)" for t in evolution.index])
    axes[0].axhline(0, color=ENCRE, lw=0.8)
    axes[0].grid(axis="x", visible=False)
    axes[0].set(title="Accidents dans un rayon de 1 km : évolution sur 2 ans", ylabel="Évolution (%)")
    axes[0].legend(loc="best")

    ecart = (donnees["apres"] - donnees["attendu_apres"]).groupby(donnees["type"])
    types = list(ecart.groups)
    axes[1].boxplot(
        [ecart.get_group(t) for t in types],
        tick_labels=types,
        vert=False,
        widths=0.5,
        showfliers=False,
        medianprops={"color": COULEURS_SERIES[0], "linewidth": 2},
        boxprops={"color": ENCRE_SECONDAIRE},
        whiskerprops={"color": ENCRE_SECONDAIRE},
        capprops={"color": ENCRE_SECONDAIRE},
    )
    axes[1].axvline(0, color=ENCRE, lw=0.8)
    axes[1].grid(axis="y", visible=False)
    axes[1].set(
        title="Écart par radar : observé − attendu après mise en service",
        xlabel="Accidents (2 ans après) en plus (+) ou en moins (−) que la tendance nationale",
    )
    fig.suptitle(
        "G8. Accidents autour des radars fixes mis en service en 2020-2022",
        x=0.02,
        ha="left",
        fontweight="bold",
    )
    fig.tight_layout()
    return fig
