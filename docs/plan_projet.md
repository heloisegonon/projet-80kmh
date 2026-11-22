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

