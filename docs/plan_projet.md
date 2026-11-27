# 80 km/h, retour aux 90 km/h et radars : quel effet sur la mortalité routière ?

**Projet Python pour la data science — ENSAE, 2e année (2026-2027)**
Cours de Lino Galiana — [pythonds.linogaliana.fr](https://pythonds.linogaliana.fr/content/annexes/evaluation.html)

> Document de cadrage du projet : problématique, données, méthode, organisation du dépôt, répartition du travail, calendrier et préparation de la soutenance. À lire par les trois membres du groupe avant de commencer, et à faire valider par le chargé de TD.

---

## Sommaire

1. [Résumé du projet](#1-résumé-du-projet)
2. [Contexte](#2-contexte)
3. [Problématique et hypothèses](#3-problématique-et-hypothèses)
4. [Les données](#4-les-données)
5. [Nettoyage et harmonisation](#5-nettoyage-et-harmonisation)
6. [Construction des indicateurs](#6-construction-des-indicateurs)
7. [Analyse descriptive](#7-analyse-descriptive)
8. [Démarche scientifique](#8-démarche-scientifique)
9. [Reproductibilité](#9-reproductibilité)
10. [Organisation du code et du dépôt](#10-organisation-du-code-et-du-dépôt)
11. [Répartition du travail et usage de Git](#11-répartition-du-travail-et-usage-de-git)
12. [Calendrier](#12-calendrier)
13. [Soutenance](#13-soutenance)
14. [Risques et plans de secours](#14-risques-et-plans-de-secours)
15. [Checklist au regard du barème](#15-checklist-au-regard-du-barème)
16. [Références](#16-références)

---

## 1. Résumé du projet

Le 1er juillet 2018, la vitesse maximale autorisée est passée de 90 à 80 km/h sur les routes bidirectionnelles sans séparateur central, hors agglomération. Depuis la loi d'orientation des mobilités (LOM) de décembre 2019, les départements peuvent revenir aux 90 km/h sur tout ou partie de leur réseau. Environ la moitié d'entre eux l'ont fait, à des dates et avec une ampleur très différentes.

Cette situation crée une **expérience naturelle** : à partir de 2020, des départements comparables vivent sous deux régimes de vitesse différents. Le projet exploite cette variation pour mesurer, de façon descriptive mais rigoureuse, l'effet de la vitesse autorisée sur la mortalité routière.

Le projet croise trois familles de données :

- les **accidents corporels** de 2010 à 2024 (fichiers BAAC de l'ONISR, open data) ;
- une **table construite par nos soins** des départements revenus aux 90 km/h, avec dates et ampleur du relèvement (collecte manuelle et documentée à partir de sources publiques) ;
- des **données de contexte** : radars fixes, population, contours géographiques, trafic.

**Livrable :** un dépôt GitHub public contenant un notebook `rapport.ipynb` qui tourne de bout en bout sans erreur, des modules Python dans `src/`, et un `README.md` expliquant comment reproduire les résultats.

---

## 2. Contexte

### 2.1 Chronologie

| Date | Événement |
|---|---|
| Janvier 2018 | Annonce de la mesure par le gouvernement (Comité interministériel de la sécurité routière) |
| 1er juillet 2018 | Passage à 80 km/h sur le réseau bidirectionnel sans séparateur central, hors agglomération |
| 26 décembre 2019 | Promulgation de la LOM : les départements peuvent relever la vitesse à 90 km/h sur leurs routes, après étude d'accidentalité et avis de la commission départementale de sécurité routière |
| 2020 | Premiers relèvements (Corrèze et Cantal au 1er février 2020, puis d'autres départements au fil de l'année) — et confinements liés au Covid |
| 2020-2025 | Relèvements progressifs, partiels ou totaux, dans environ 40 à 50 départements selon les décomptes |

### 2.2 Pourquoi ce sujet est intéressant

- **Une question de politique publique réelle et débattue.** La mesure a été très contestée et le retour aux 90 km/h est une décision politique locale.
- **Une variation exploitable.** Le relèvement n'a pas eu lieu partout en même temps ni de la même façon, ce qui permet de comparer des groupes.
- **Un résultat de référence pour se situer.** L'ONISR a publié une évaluation du relèvement sur 2019-2022. Nous pourrons comparer nos résultats aux siens et expliquer les éventuels écarts.
- **Un vrai travail de données.** Les bases BAAC changent de format en 2019, et il n'existe aucun fichier officiel recensant proprement les relèvements : il faut le construire.

### 2.3 Mécanisme attendu

La littérature en sécurité routière (notamment le « modèle de puissance » de Nilsson, repris par l'ONISR et le Cerema) établit que le nombre de tués varie bien plus que proportionnellement avec la vitesse moyenne pratiquée. Une baisse de quelques km/h de la vitesse moyenne peut donc produire une baisse sensible de la mortalité, surtout pour les chocs frontaux et les sorties de route, qui sont les accidents typiques du réseau secondaire. C'est ce mécanisme que nous cherchons à retrouver dans les données.

> ⚠️ Nous ne disposons pas des vitesses réellement pratiquées. Nous mesurons l'effet d'un **changement de règle**, pas d'un changement de vitesse observé. C'est une limite à mentionner dans le rapport.

---

## 3. Problématique et hypothèses

### 3.1 Question centrale

> **La baisse de la vitesse autorisée à 80 km/h a-t-elle réduit la mortalité routière, et le retour aux 90 km/h l'a-t-il fait remonter ?**

### 3.2 Sous-questions

**Q1 — L'effet de 2018 (contexte).**
La mortalité a-t-elle baissé plus vite après juillet 2018 sur le réseau concerné (routes bidirectionnelles hors agglomération) que sur le réseau non concerné (autoroutes, routes à chaussées séparées, routes en agglomération) ?

**Q2 — L'effet du retour aux 90 km/h (cœur du projet).**
À partir de 2020, la mortalité sur le réseau secondaire a-t-elle évolué différemment dans les départements relevés à 90 km/h et dans ceux restés à 80 km/h ? L'effet est-il plus marqué là où le relèvement est total plutôt que partiel ?

**Q3 — Les radars (optionnel, si le temps le permet).**
Le nombre d'accidents diminue-t-il à proximité d'un radar fixe après sa mise en service ?

### 3.3 Hypothèses à tester

| Hypothèse | Ce qu'on devrait observer si elle est vraie |
|---|---|
| H1 : le 80 km/h a réduit la mortalité | Rupture à la baisse en 2018-2019 sur le réseau concerné, absente ou plus faible sur le réseau non concerné |
| H2 : le retour aux 90 km/h a augmenté la mortalité | Après relèvement, évolution moins favorable dans les départements relevés que dans les départements restés à 80 |
| H3 : l'effet dépend de l'intensité | Écart plus grand pour les départements relevés en totalité que pour ceux relevés partiellement |
| H4 : l'effet passe par certains types d'accidents | Variation concentrée sur les chocs frontaux et les sorties de route, plus faible sur les autres collisions |

Le rapport doit conclure sur chaque hypothèse, y compris quand les données ne permettent pas de trancher.

---

## 4. Les données

### 4.1 Vue d'ensemble

| Source | Producteur | Accès | Contenu utile | Rôle |
|---|---|---|---|---|
| BAAC 2010-2024 | ONISR via data.gouv.fr | API data.gouv + CSV | Tous les accidents corporels, lieux, véhicules, usagers | Variable d'intérêt (tués, accidents) |
| Départements relevés à 90 km/h | **Construit par nous** | Collecte manuelle documentée | Département, date, ampleur du relèvement, source | Définition des groupes |
| Radars fixes | Ministère de l'Intérieur via data.gouv.fr | CSV | Identifiant, coordonnées GPS, date de mise en service, type, VMA | Q3 |
| Population par département | INSEE | `pynsee` ou CSV des populations légales | Population annuelle | Taux par habitant |
| Contours des départements | IGN / INSEE | `cartiflette` | Géométries | Cartes |
| Trafic | SDES / ONISR | CSV | Ventes de carburant par département ou indice national de circulation | Correction du Covid |
| Évaluation ONISR du relèvement 2019-2022 | ONISR | PDF | Résultats de référence | Comparaison |

### 4.2 BAAC — accidents corporels

**Lien :** [data.gouv.fr — Bases de données annuelles des accidents corporels de la circulation routière, 2005 à 2024](https://www.data.gouv.fr/datasets/53698f4ca3a729239d2036df/)

Chaque année comprend **4 fichiers CSV** reliés par l'identifiant d'accident `Num_Acc` :

| Fichier | Une ligne = | Variables utiles (à vérifier dans le guide de codification) |
|---|---|---|
| `caracteristiques` | un accident | `Num_Acc`, `jour`, `mois`, `an`, `hrmn`, `lum`, `dep`, `com`, `agg` (en/hors agglomération), `atm` (météo), `col` (type de collision), `lat`, `long` |
| `lieux` | un accident | `catr` (catégorie de route), `circ` (régime de circulation), `nbv` (nombre de voies), `lartpc` (terre-plein central), `vma` (vitesse max., **seulement depuis 2019**), `surf`, `infra`, `situ` |
| `vehicules` | un véhicule | `catv` (catégorie de véhicule), `obs`, `obsm`, `choc`, `manv` |
| `usagers` | un usager | `grav` (gravité), `catu`, `sexe`, `an_nais`, `trajet` |

**Codes à connaître (format 2019 et suivants, à vérifier pour les années antérieures) :**

- `grav` : 1 = indemne, 2 = tué, 3 = blessé hospitalisé, 4 = blessé léger
- `agg` : 1 = hors agglomération, 2 = en agglomération
- `catr` : 1 = autoroute, 2 = route nationale, 3 = route départementale, 4 = voie communale, …
- `circ` : 1 = sens unique, 2 = bidirectionnelle, 3 = chaussées séparées, 4 = voies d'affectation variable

**Définition d'un tué :** personne décédée sur le coup ou dans les 30 jours suivant l'accident.

Les deux documents à lire en priorité, joints au jeu de données :

- la **description des bases de données annuelles** (évolutions de format, avertissements) ;
- le **guide d'utilisation de la codification** du bulletin d'analyse des accidents corporels.

### 4.3 Table des départements revenus aux 90 km/h — notre apport principal

C'est la partie qui valorise le plus la collecte, car **cette table n'existe pas sous forme propre**. Nous la construisons et la versionnons dans `data/departements_90.csv`.

**Schéma de la table :**

| Colonne | Type | Description | Exemple |
|---|---|---|---|
| `code_dep` | str | Code département (2 ou 3 caractères) | `19` |
| `nom_dep` | str | Nom du département | `Corrèze` |
| `releve` | bool | Le département a-t-il relevé au moins une route ? | `True` |
| `date_releve` | date | Date d'entrée en vigueur du premier relèvement | `2020-02-01` |
| `etendue` | str | `total`, `partiel` ou `aucun` | `total` |
| `km_releves` | float | Kilomètres relevés, si l'information existe | `4000` |
| `km_reseau` | float | Longueur du réseau départemental, si disponible | `4700` |
| `source_1` | str | URL de la première source | `https://...` |
| `source_2` | str | URL d'une source de confirmation | `https://...` |
| `commentaire` | str | Précisions, incertitudes | `relèvement en deux étapes` |

**Méthode de collecte :**

1. Partir d'une liste agrégée (par exemple celle de la Ligue de défense des conducteurs, reprise par la presse, et celle diffusée par Roole Data en 2025).
2. Pour chaque département de la liste, chercher **la délibération ou le communiqué du conseil départemental** et un article de presse locale donnant la date d'entrée en vigueur et le linéaire concerné.
3. Exiger **deux sources concordantes** pour chaque date. En cas de désaccord, retenir la source officielle et noter le désaccord dans `commentaire`.
4. Les départements absents des listes sont codés `aucun`, après vérification rapide.
5. Comparer, à la fin, notre classement à celui de l'étude ONISR, qui a défini ses propres groupes.

**Pourquoi l'étendue compte :** certains départements ont relevé presque tout leur réseau (Corrèze, Cantal, Creuse, Allier…), d'autres seulement quelques tronçons (la Dordogne a annoncé 287 km sur environ 4 900 km, l'Indre environ 220 km). Les traiter de la même façon diluerait l'effet. Il faut donc au minimum distinguer `total` et `partiel`, et si possible calculer une **part du réseau relevée**.

> 💡 Si le temps le permet, le scraping de quelques pages de communiqués départementaux peut automatiser une partie de la collecte. Mais la table finale doit être versionnée dans le dépôt pour ne pas dépendre de sites qui peuvent changer.

### 4.4 Radars fixes

**Lien :** [data.gouv.fr — Liste des radars fixes en France](https://www.data.gouv.fr/datasets/liste-des-radars-fixes-en-france/)

Environ 3 400 radars, avec identifiant, coordonnées GPS, date de mise en service, type (ETF, ETD, ETVM, ETU…) et vitesse maximale autorisée. Mis à jour annuellement (dernière mise à jour fin 2025).

> ⚠️ Le fichier liste les radars **actuellement en service**. Les radars démontés ou vandalisés n'y figurent pas, ce qui introduit un biais de survie à discuter.

### 4.5 Données de contexte

- **Population :** populations légales annuelles par département (INSEE), via `pynsee` ou le fichier CSV publié par l'INSEE.
- **Contours :** `cartiflette`, la bibliothèque utilisée dans le cours, pour récupérer les géométries des départements.
- **Trafic :** c'est indispensable pour 2020. Deux options, par ordre de préférence :
  1. ventes de carburant routier par département (SDES), qui servent d'indicateur indirect du trafic local ;
  2. à défaut, l'indice national de circulation publié dans les bilans annuels de l'ONISR et du SDES.

### 4.6 Ce que nous n'utiliserons pas

- Pas de données Kaggle (interdit par le cours).
- Pas de base de données de vitesses pratiquées : elle n'est pas disponible en open data à la bonne échelle.
- Les départements et collectivités d'outre-mer sont exclus : réseaux et règles différents, et couverture incomplète dans l'open data avant 2019.

---

## 5. Nettoyage et harmonisation

C'est l'étape la plus délicate techniquement. Elle doit être **entièrement codée** (aucune modification à la main des fichiers bruts) et **documentée** dans le rapport.

### 5.1 Les ruptures connues des BAAC

| Problème | Années | Traitement |
|---|---|---|
| Changement de format en 2019 (variables ajoutées ou renommées, séparateur, encodage) | avant/après 2019 | Une fonction de lecture par format, puis renommage vers un **schéma commun** |
| Encodage des anciens fichiers (souvent `latin-1`) | avant 2019 | Paramètre `encoding` dans `pd.read_csv`, testé sur chaque année |
| Séparateur différent selon les années (`,` ou `;`, voire tabulation pour certains fichiers) | variable | Détection automatique ou dictionnaire `{année: séparateur}` |
| Année sur 2 chiffres, heure au format entier (`1530`) | avant 2019 | Conversion vers une vraie date-heure |
| Code département avec un zéro final (`590` pour le Nord) dans les anciens fichiers | avant 2019 | Fonction de normalisation vers le code officiel (`59`, `2A`, `2B`…) |
| Coordonnées dans un format entier et souvent manquantes | avant 2019 | Conversion et contrôle de cohérence (point bien dans le département déclaré) |
| Variable `vma` (vitesse maximale autorisée) absente | avant 2019 | Voir 5.2 |
| Ajout des usagers en fuite | depuis 2021 | Exclure ou isoler ces usagers pour garder une série comparable |
| Fiabilité des blessés hospitalisés | depuis 2018 | Indicateur principal = **tués** ; blessés en analyse secondaire seulement |

### 5.2 Identifier le réseau concerné par la mesure

La mesure de 2018 concerne les routes **hors agglomération**, **bidirectionnelles**, **sans séparateur central**. Nous définissons donc :

```
reseau_concerne = (agg == hors agglomération)
                  & (circ == bidirectionnelle)
                  & (catr in {route nationale, route départementale, voie communale})
```

- Depuis 2019, on peut **vérifier** cette règle avec la variable `vma` (part des accidents du réseau concerné avec `vma` égale à 80 ou 90).
- Avant 2019, on applique la même règle sans pouvoir la vérifier. Il faut le dire dans le rapport.
- Pour Q2, on se restreint aux **routes départementales** (`catr == 3`), puisque ce sont les départements qui décident du relèvement.

> 📝 Documenter dans le rapport : la règle exacte, la part des accidents classés « concernés » chaque année, et un tableau de contrôle par année pour montrer l'absence de saut artificiel en 2019.

### 5.3 Schéma de sortie

Toutes les années sont empilées dans **deux tables Parquet** :

- `accidents.parquet` : une ligne par accident (caractéristiques + lieux) avec `annee`, `mois`, `date`, `code_dep`, `reseau_concerne`, `catr`, `type_collision`, `nb_tues`, `nb_blesses`, `lat`, `lon` ;
- `usagers.parquet` : une ligne par usager, pour les analyses par âge ou type d'usager.

### 5.4 Exemple de squelette de code

```python
# src/collecte.py
import requests

DATASET_BAAC = "53698f4ca3a729239d2036df"

def lister_ressources_baac() -> list[dict]:
    """Interroge l'API data.gouv.fr et renvoie les fichiers du jeu BAAC."""
    url = f"https://www.data.gouv.fr/api/1/datasets/{DATASET_BAAC}/"
    reponse = requests.get(url, timeout=30)
    reponse.raise_for_status()
    return [
        {"titre": r["title"], "url": r["url"], "format": r["format"]}
        for r in reponse.json()["resources"]
    ]
```

```python
# src/nettoyage.py
import pandas as pd

def normaliser_departement(code: str) -> str:
    """Convertit les anciens codes BAAC (ex. '590') en codes officiels ('59')."""
    ...

def lire_caracteristiques(url: str, annee: int) -> pd.DataFrame:
    """Lit un fichier 'caracteristiques' quelle que soit l'année
    et renvoie un DataFrame au schéma commun."""
    sep = ";" if annee >= 2019 else ","
    encodage = "utf-8" if annee >= 2019 else "latin-1"
    df = pd.read_csv(url, sep=sep, encoding=encodage, dtype=str)
    ...
    return df
```

Chaque fonction a une docstring, prend des paramètres explicites et ne dépend d'aucun chemin local en dur.

---

## 6. Construction des indicateurs

### 6.1 Indicateur principal

**Nombre de tués sur le réseau concerné**, par département et par année (ou par semestre), rapporté :

- à la **population** (tués par million d'habitants), pour comparer des départements de tailles différentes ;
- au **trafic** quand l'indicateur est disponible, pour neutraliser 2020.

### 6.2 Indicateurs secondaires

- Nombre d'**accidents mortels** (plus stable que le nombre de tués, car un accident peut faire plusieurs victimes).
- Tués par **type de collision** : frontale, sortie de route sans tiers, autres.
- Tués par **type d'usager** : automobilistes, deux-roues motorisés, piétons, cyclistes.
- **Gravité moyenne** : part des tués parmi les victimes (avec la réserve sur les blessés hospitalisés).

### 6.3 Les groupes

| Groupe | Définition | Utilisé pour |
|---|---|---|
| Réseau concerné / non concerné | Règle de la section 5.2 | Q1 |
| `G80` | Départements restés à 80 km/h | Q2 (groupe témoin) |
| `G90_partiel` | Départements ayant relevé une partie du réseau | Q2 |
| `G90_total` | Départements ayant relevé la quasi-totalité du réseau | Q2 |
| `G80_rural` | Départements restés à 80 km/h, hors départements très urbains | Q2 (robustesse) |

**Définition de « très urbain » :** à fixer à partir de la densité de population ou de la part de population en agglomération (INSEE). Le seuil est choisi **avant** de regarder les résultats et justifié dans le rapport.

### 6.4 Gérer les petits nombres

Dans un petit département, le nombre de tués annuel peut être de quelques dizaines : une variation de quelques décès fait bouger fortement le taux. Pour éviter de surinterpréter le bruit :

- on agrège **par groupe** plutôt que de commenter des départements isolés ;
- on lisse sur **plusieurs années** (moyenne mobile ou comparaison de périodes) ;
- on indique, quand c'est utile, un **intervalle de confiance** sur les comptages (approximation de Poisson : un compte `N` a un écart-type d'environ `√N`).

---

## 7. Analyse descriptive

Chaque graphique doit avoir un titre explicite, des axes nommés avec leurs unités, une légende lisible, et **un paragraphe de commentaire** qui relie le résultat à une hypothèse.

### 7.1 Description de la base

- Nombre d'accidents, de tués, d'usagers par année, avant et après harmonisation.
- Part des accidents sur le réseau concerné, par année (contrôle de la règle de la section 5.2).
- Valeurs manquantes par variable et par année, sous forme de tableau ou de heatmap.

### 7.2 Graphiques prévus

| # | Graphique | Type | Question |
|---|---|---|---|
| G1 | Tués par mois, 2010-2024, réseau concerné vs non concerné, lignes verticales en juillet 2018 et en 2020 | Séries temporelles | Q1 |
| G2 | Carte des départements selon leur groupe (`G80`, `G90_partiel`, `G90_total`) | Carte choroplèthe | Q2 |
| G3 | Calendrier des relèvements : date de relèvement par département | Frise ou graphique en points | Q2 |
| G4 | **Tués en base 100 (2017 ou 2019) par groupe, 2015-2024** | Séries temporelles | Q2 — graphique central |
| G5 | Évolution en fonction du nombre d'années avant/après le relèvement de chaque département | « Étude d'événement » descriptive | Q2 |
| G6 | Répartition des tués par type de collision, avant/après, par groupe | Barres groupées | H4 |
| G7 | Carte des taux de tués par million d'habitants, avant et après | Deux cartes côte à côte | Q2 |
| G8 | Accidents dans un rayon de 1 km autour des radars, avant/après mise en service | Barres ou boîtes à moustaches | Q3 |

Bibliothèques : `matplotlib` / `seaborn` ou `plotnine` pour les graphiques statiques, `geopandas` + `cartiflette` pour les cartes, éventuellement `plotly` ou `folium` pour une carte interactive des accidents.

### 7.3 Pistes d'interprétation à préparer

- Si la baisse de 2018-2019 est visible **aussi** sur le réseau non concerné, une partie de l'effet relève d'une tendance générale (amélioration du parc automobile, autres mesures).
- Si `G90_total` diverge de `G80` alors que `G90_partiel` ne diverge pas, cela soutient H3.
- Si les écarts apparaissent **avant** le relèvement, les groupes n'étaient pas comparables : il faut le dire et relativiser les conclusions (voir section 8).

---

## 8. Démarche scientifique

### 8.1 La méthode centrale : avant/après avec groupe témoin

Pour Q2, nous comparons **l'évolution** de la mortalité dans les départements relevés à celle des départements restés à 80 km/h :

```
effet estimé = (évolution dans G90) − (évolution dans G80)
             = (Y_G90, après − Y_G90, avant) − (Y_G80, après − Y_G80, avant)
```

C'est le principe de la **différence de différences**, appliqué ici de manière descriptive avec des moyennes de groupes, sans avoir besoin d'un modèle économétrique.

**Périodes :**

- *avant* : de juillet 2018 à fin 2019, quand tous les départements sont à 80 km/h. On peut l'élargir à 2015-2019 pour vérifier les tendances ;
- *après* : de la date de relèvement de chaque département jusqu'à 2024 ;
- **2020 est traitée à part** à cause du Covid : on présente les résultats avec et sans cette année.

**Condition de validité :** les deux groupes doivent avoir des **tendances parallèles avant le relèvement**. On le vérifie visuellement avec le graphique G4 sur 2015-2019. Si les courbes divergent déjà avant 2020, la comparaison est fragile.

**Dates de relèvement échelonnées :** comme les départements n'ont pas relevé au même moment, le graphique G5 aligne chaque département sur **sa propre date** de relèvement (année −3, −2, −1, 0, +1, +2…). C'est plus juste qu'une date unique pour tout le monde.

### 8.2 Les biais à discuter explicitement

| Biais | Pourquoi il existe | Comment on le traite |
|---|---|---|
| **Sélection** | Les départements ont choisi de relever ou non ; les départements très urbains sont tous restés à 80 | Comparaison restreinte aux départements ruraux (`G80_rural`) ; comparaison des profils des groupes avant 2020 |
| **Covid** | Le trafic s'effondre en 2020, l'année des premiers relèvements | Taux rapportés au trafic quand c'est possible ; résultats avec et sans 2020 |
| **Petits nombres** | Peu de tués par département et par an | Agrégation par groupe, périodes pluriannuelles, ordres de grandeur de l'incertitude |
| **Mesures concomitantes** | Certains relèvements s'accompagnent de nouvelles zones à 70 km/h, de radars, d'aménagements | À mentionner ; on ne peut pas tout isoler |
| **Mesure imparfaite du traitement** | Relèvements partiels, dates parfois imprécises | Distinction `total` / `partiel` ; analyse de sensibilité en décalant les dates de quelques mois |
| **Rupture des données en 2019** | Changement de format BAAC l'année même de la LOM | Contrôle de la stabilité des séries autour de 2019 (section 5.2) |
| **Régression vers la moyenne** (Q3) | Les radars sont installés là où il y a eu beaucoup d'accidents, qui auraient de toute façon baissé ensuite | Comparer avec des points accidentogènes sans radar ; prudence dans les conclusions |
| **Biais de survie** (Q3) | Seuls les radars encore en service figurent dans le fichier | À mentionner |

### 8.3 Tests de robustesse

1. Résultats **avec et sans 2020**.
2. Résultats en **tués** puis en **accidents mortels**.
3. Résultats sur **tous les départements** puis sur les **départements ruraux** uniquement.
4. Résultats avec **`G90_total` seul**, puis avec `G90_total` + `G90_partiel`.
5. Décaler les **dates de relèvement** de ±6 mois pour voir si la conclusion tient.

Un tableau récapitulatif dans le rapport présente l'effet estimé dans chaque configuration. Une conclusion qui tient dans toutes les configurations est solide ; une conclusion qui ne tient que dans une seule doit être présentée avec prudence.

### 8.4 Confrontation avec l'évaluation officielle

L'ONISR a publié une étude sur l'impact du relèvement à 90 km/h entre 2019 et 2022, qui conclut à une surmortalité dans les départements relevés. Dans le rapport :

- résumer sa méthode (groupes, période, indicateur) ;
- comparer nos groupes aux siens ;
- comparer nos ordres de grandeur aux siens ;
- expliquer les écarts éventuels (définition des groupes, période, traitement de 2020).

Retrouver un résultat officiel avec ses propres données, ou expliquer de manière convaincante pourquoi on s'en écarte, est un très bon argument de démarche scientifique.

### 8.5 Ce que nous ne pourrons pas conclure

À écrire noir sur blanc dans la conclusion :

- nous mesurons l'effet d'une règle, pas de la vitesse réelle ;
- une comparaison de groupes non tirés au hasard ne prouve pas la causalité, elle la rend plus ou moins plausible ;
- les résultats valent pour le réseau secondaire français entre 2015 et 2024, pas au-delà.

---

## 9. Reproductibilité

**Condition non négociable :** le notebook final doit s'exécuter de la première à la dernière cellule sans erreur. Sinon, la moyenne est impossible.

### 9.1 Principes

- **Aucune donnée téléchargée à la main.** Tout passe par du code qui part des URL publiques (API data.gouv.fr pour les BAAC et les radars, `pynsee` et `cartiflette` pour l'INSEE et les contours).
- **Exception documentée :** la table `data/departements_90.csv` est construite par nous et versionnée dans le dépôt. Elle est petite (une centaine de lignes), donc sa place dans Git est justifiée.
- **Les gros fichiers ne vont pas dans Git.** Les BAAC harmonisés en Parquet sont stockés sur l'espace S3 du SSP Cloud (MinIO), comme expliqué dans le cours.
- **Fonctionnement en cascade :** le notebook lit d'abord la version Parquet sur S3 ; si elle n'est pas accessible, il retélécharge et reconstruit les données depuis les sources brutes. Les deux chemins doivent fonctionner.
- **Pas de secret dans le code.** Si un identifiant est nécessaire (S3), il passe par des variables d'environnement (`.env` non versionné, `python-dotenv`).

### 9.2 Dépendances

Un fichier `pyproject.toml` (ou `requirements.txt`) avec les versions minimales :

```
pandas
pyarrow
duckdb
requests
geopandas
cartiflette
pynsee
matplotlib
seaborn
plotnine
python-dotenv
s3fs
nb-clean
```

### 9.3 Test final

Une semaine avant le rendu, **un membre du groupe qui n'a pas écrit le code** clone le dépôt dans un service SSP Cloud vierge, installe les dépendances en suivant le `README.md`, et lance « Exécuter tout ». Tout problème rencontré est corrigé et le `README.md` mis à jour.

---

## 10. Organisation du code et du dépôt

### 10.1 Arborescence

```
projet-80kmh/
├── README.md                 # problématique, résultats clés, instructions de reproduction
├── pyproject.toml            # dépendances
├── .gitignore                # données brutes, .env, caches
├── data/
│   └── departements_90.csv   # table construite à la main, sourcée
├── src/
│   ├── __init__.py
│   ├── collecte.py           # API data.gouv, téléchargements, lecture/écriture S3
│   ├── nettoyage.py          # harmonisation des années, normalisation des codes
│   ├── indicateurs.py        # agrégations, taux, groupes, différence de différences
│   └── graphiques.py         # fonctions de visualisation réutilisables
├── rapport.ipynb             # le rapport : importe src/, contient l'analyse commentée
└── docs/
    └── collecte_departements.md  # journal de la collecte de la table des relèvements
```

### 10.2 Règles de qualité du code

- **Pas de copier-coller de cellules** : dès qu'une opération est répétée (par exemple pour chaque année), elle devient une fonction dans `src/`.
- **Docstrings** pour toutes les fonctions : ce qu'elle fait, ses paramètres, ce qu'elle renvoie.
- **Noms explicites** en français ou en anglais, mais de façon cohérente.
- **Formatage automatique** avec `ruff format` ou `black`.
- **Sorties du notebook nettoyées** avant chaque commit (`nb-clean`), pour limiter les conflits Git.
- Le notebook ne contient que de **l'orchestration et du commentaire** : chargement, appels de fonctions, graphiques, interprétation.

---

## 11. Répartition du travail et usage de Git

### 11.1 Rôles

| Membre | Responsabilité principale | Fichiers |
|---|---|---|
| **A — Accidents** | Collecte et harmonisation des BAAC 2010-2024, règle du réseau concerné, tables Parquet | `collecte.py`, `nettoyage.py` |
| **B — Traitement et contexte** | Construction de la table des départements relevés, radars, population, trafic, contours | `data/departements_90.csv`, `docs/collecte_departements.md`, partie de `collecte.py` |
| **C — Analyse et rapport** | Indicateurs, graphiques, cartes, différence de différences, robustesse, comparaison ONISR, rédaction | `indicateurs.py`, `graphiques.py`, `rapport.ipynb` |

Les rôles ne sont pas étanches : chacun relit le travail des autres et tout le monde doit pouvoir expliquer l'ensemble du projet à l'oral.

### 11.2 Pratiques Git attendues

- Une **branche par fonctionnalité** (`collecte-baac`, `table-releves`, `graphique-g4`…).
- Des **commits fréquents** avec des messages explicites (« Harmonise le code département des BAAC avant 2019 » plutôt que « update »).
- Fusion dans `main` uniquement par **pull request relue par un autre membre**.
- **Jamais deux personnes sur le même notebook en même temps sur la même branche.**
- Utilisation des **issues GitHub** pour suivre les tâches et les problèmes rencontrés.

Le cours pénalise les dépôts où le projet a simplement été déposé en une fois, et valorise les dépôts où l'historique montre un vrai travail collaboratif.

---

## 12. Calendrier

À adapter selon la date exacte de rendu (décembre 2026) et de soutenance (janvier 2027).

| Semaine | Dates indicatives | Étape | Livrable |
|---|---|---|---|
| 1 | mi-octobre | Validation du sujet par le chargé de TD, création du dépôt, lecture du guide BAAC et de l'étude ONISR | Dépôt créé, `README.md` initial |
| 2-3 | fin octobre | Collecte des BAAC via l'API ; début de la table des relèvements | Script de téléchargement fonctionnel |
| 4-5 | début novembre | Harmonisation des années, règle du réseau concerné, contrôles ; table des relèvements terminée | `accidents.parquet`, `departements_90.csv` |
| 6-7 | mi-novembre | Description de la base, graphiques G1 à G4, cartes | Première version du rapport |
| 8-9 | fin novembre | Différence de différences, étude d'événement, robustesse, Q3 si le temps le permet | Tableau de robustesse |
| 10 | début décembre | Comparaison ONISR, rédaction de l'introduction et de la conclusion, relecture croisée | Rapport complet |
| 11 | une semaine avant le rendu | Test de reproductibilité sur environnement vierge, nettoyage du code, finalisation du `README.md` | Version finale |
| — | janvier | Préparation et répétitions de la soutenance | Support de présentation |

**Point d'étape :** prévoir une courte réunion chaque semaine pour faire le point, et une « version présentable » du rapport fin novembre pour pouvoir la montrer au chargé de TD si besoin.

---

## 13. Soutenance

### 13.1 Fil narratif proposé

1. **L'accroche (1 min).** Une mesure parmi les plus contestées de la décennie, puis un retour en arrière décidé département par département. Cela crée une occasion rare de mesurer l'effet de la vitesse.
2. **La question (1 min).** Le 80 km/h a-t-il sauvé des vies, et le retour aux 90 en a-t-il coûté ?
3. **Les données (2-3 min).** Quinze ans d'accidents, une rupture de format à gérer, et surtout une table des relèvements qui n'existait pas et que nous avons construite. Montrer la carte G2.
4. **Les résultats (4-5 min).** Le graphique G4 d'abord, commenté lentement. Puis G5 et le tableau de robustesse.
5. **Les limites (2 min).** Sélection des départements, Covid, petits nombres. Ce que l'on peut conclure et ce que l'on ne peut pas.
6. **La comparaison avec l'ONISR et la conclusion (1-2 min).**

### 13.2 Conseils

- **Peu de graphiques, bien expliqués :** quatre ou cinq au maximum.
- Le graphique G4 doit être **compréhensible en dix secondes** : deux ou trois courbes, couleurs contrastées, annotations directement sur le graphique.
- Chaque membre présente une partie, mais **chacun doit pouvoir répondre** sur l'ensemble.
- Préparer les réponses aux questions probables :
  - « Pourquoi ne pas simplement comparer avant et après 2018 ? »
  - « Comment avez-vous traité 2020 ? »
  - « Les départements relevés ne sont-ils pas différents dès le départ ? »
  - « Pourquoi vos résultats diffèrent-ils (ou non) de ceux de l'ONISR ? »
  - « Comment avez-vous construit la table des relèvements, et quelle confiance lui accorder ? »

---

## 14. Risques et plans de secours

| Risque | Probabilité | Plan de secours |
|---|---|---|
| Harmonisation des BAAC plus longue que prévu | Moyenne | Se limiter à 2015-2024 au lieu de 2010-2024 |
| Dates de relèvement introuvables pour certains départements | Élevée | Les coder à l'année plutôt qu'au mois, ou les exclure avec justification |
| Pas d'indicateur de trafic par département | Moyenne | Utiliser l'indice national et présenter les résultats sans 2020 |
| Résultats non significatifs ou contradictoires | Moyenne | Ce n'est pas un échec : expliquer pourquoi les données ne permettent pas de trancher, c'est un résultat |
| Panne d'une source en ligne au moment de la correction | Faible | Cache Parquet sur S3 + table des relèvements dans le dépôt |
| Q3 (radars) trop longue | Élevée | La traiter en annexe ou la supprimer : elle est optionnelle |

---

## 15. Checklist au regard du barème

### Données — collecte et nettoyage (4 points)

- [ ] Plusieurs sources croisées (BAAC, table des relèvements, radars, INSEE, trafic)
- [ ] Utilisation d'une API (data.gouv.fr) et de bibliothèques d'accès aux données (`pynsee`, `cartiflette`)
- [ ] Construction d'une table originale, sourcée et documentée
- [ ] Harmonisation codée des 15 années de BAAC, ruptures documentées
- [ ] Choix de nettoyage expliqués dans le rapport

### Analyse descriptive (4 points)

- [ ] Description de la base et des valeurs manquantes
- [ ] Graphiques adaptés, avec titres, axes, unités et légendes
- [ ] Au moins deux cartes
- [ ] Chaque tableau et graphique commenté et relié à une hypothèse

### Démarche scientifique et reproductibilité (5 points)

- [ ] Problématique et hypothèses posées dès l'introduction
- [ ] Méthode avant/après avec groupe témoin, tendances parallèles vérifiées
- [ ] Biais discutés explicitement, tests de robustesse
- [ ] Comparaison avec l'étude ONISR
- [ ] Limites clairement énoncées dans la conclusion
- [ ] Notebook exécutable de bout en bout sans erreur
- [ ] Données récupérées par le code depuis des sources publiques, cache sur S3
- [ ] Dépendances listées, `README.md` suffisant pour reproduire
- [ ] Test sur environnement vierge effectué

### Format du code (2 points)

- [ ] Code organisé en modules dans `src/`
- [ ] Fonctions documentées, pas de copier-coller
- [ ] Code formaté, sorties de notebook nettoyées
- [ ] Historique Git riche : branches, commits réguliers, pull requests relues

### Soutenance (5 points)

- [ ] Fil narratif clair et minuté
- [ ] Quatre ou cinq visuels maximum, lisibles
- [ ] Répartition de la parole entre les trois membres
- [ ] Réponses préparées aux questions probables
- [ ] Au moins deux répétitions chronométrées

---

## 16. Références

**Données**

- ONISR, *Bases de données annuelles des accidents corporels de la circulation routière, années 2005 à 2024*, data.gouv.fr — <https://www.data.gouv.fr/datasets/53698f4ca3a729239d2036df/>
- ONISR, *Description des bases de données annuelles des accidents corporels* (PDF joint au jeu de données)
- Ministère de l'Intérieur, *Liste des radars fixes en France*, data.gouv.fr — <https://www.data.gouv.fr/datasets/liste-des-radars-fixes-en-france/>
- INSEE, populations légales et données départementales (via `pynsee`)
- `cartiflette` — <https://github.com/inseefrlab/cartiflette>

**Études et contexte**

- ONISR, *Relèvement de la vitesse maximale autorisée à 90 km/h sur certaines routes départementales, impact 2019-2022* — <https://www.onisr.securite-routiere.gouv.fr/sites/default/files/2026-05/2024-02_23_Impact%20relevement_90_2019-2022-v5.pdf>
- ONISR, liste des indicateurs labellisés — <https://www.onisr.securite-routiere.gouv.fr/outils-statistiques/indicateurs-labellises>
- Loi n° 2019-1428 du 26 décembre 2019 d'orientation des mobilités (LOM)
- Presse-citron, liste des départements revenus aux 90 km/h selon la Ligue de défense des conducteurs — <https://www.presse-citron.net/voici-la-liste-officielle-des-46-departements-dont-la-limite-est-repassee-a-90-km-h/>
- Roole, point sur les départements revenus aux 90 km/h au 1er juillet 2025 — <https://media.roole.fr/quotidien/reglementation/ces-departements-ou-la-vitesse-est-repassee-a-90-km-h-sur-les-routes-secondaires>
- Weka, retour aux 90 km/h en Corrèze et dans le Cantal (février 2020) — <https://www.weka.fr/actualite/urbanisme/article/routes-correze-et-cantal-repassent-a-90-km-h-95116/>
- Caradisiac, retour partiel aux 90 km/h en Dordogne — <https://www.caradisiac.com/la-dordogne-annonce-le-retour-des-90-km-h-187327.htm>

**Cours**

- Lino Galiana, *Python pour la data science*, page d'évaluation — <https://pythonds.linogaliana.fr/content/annexes/evaluation.html>
- Chapitres du cours utiles : jointures Pandas, Geopandas, cartographie, API, Parquet et S3, Git.

---

*Les codes de variables BAAC indiqués dans ce document sont donnés à titre indicatif : ils doivent être vérifiés dans le guide de codification officiel, en particulier pour les années antérieures à 2019.*
