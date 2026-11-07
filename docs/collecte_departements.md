# Journal de collecte : départements revenus aux 90 km/h

Ce document décrit la construction de `data/departements_90.csv`. Aucune table officielle propre ne recense les relèvements : nous l'avons construite à partir de sources publiques, en octobre 2026.

## Sources

| Rôle | Source | Contenu utilisé |
|---|---|---|
| **Base officielle** | ONISR, *Relèvement de la VMA à 90 km/h sur certaines RD, bilan de l'année 2022*, février 2024, [tableau 8 (annexe 2)](https://www.onisr.securite-routiere.gouv.fr/sites/default/files/2026-05/2024-02_23_Impact%20relevement_90_2019-2022-v5.pdf) | Pour les 95 départements hors Paris : typologie Cerema, linéaire total de RD, date(s) de relèvement, km relevés à fin 2022, tués hors agglomération hors autoroute en 2019 et 2022 |
| Linéaire récent | L'Argus, [*Retour aux 90 km/h : quels sont les 52 départements concernés ?*](https://www.largus.fr/actualite-automobile/la-carte-de-france-des-departements-qui-repassent-a-90-kmh-10488403.html), mis à jour le 17/07/2026 | km relevés et part du réseau pour les 52 départements |
| Liste de contrôle | Ligue de défense des conducteurs, via [Presse-citron](https://www.presse-citron.net/voici-la-liste-officielle-des-46-departements-dont-la-limite-est-repassee-a-90-km-h/) (mai 2023) | 47 départements, étendue totale ou partielle |
| Contentieux | Cabinet Landot, [point jurisprudentiel au 21 mai 2026](https://blog.landot-avocats.net/2026/05/21/retour-aux-90-km-h-un-point-jurisprudentiel-au-21-mai-2026/) | Annulations d'arrêtés (Hérault, Hautes-Alpes, Orne, Corrèze, Sarthe…) |
| Relèvements après 2022 | Presse locale et nationale (lien dans `source_1` de chaque ligne) | Alpes-de-Haute-Provence, Doubs, Nièvre, Tarn-et-Garonne, Var (2023), Morbihan (2025), Eure (2026) |

## Méthode

1. **Point de départ : le tableau 8 de l'ONISR.** Les départements qui y figurent sur deux lignes (relèvement en 2022) sont fusionnés : la date retenue est celle du premier relèvement, les tués sont additionnés. Les relèvements en plusieurs étapes sont conservés dans la colonne `etapes` (`date:km cumulés`).
2. **Relèvements postérieurs à 2022.** La liste L'Argus 2026 (52 départements) contient 7 départements absents du groupe 90 de l'ONISR. Pour chacun, une date a été cherchée dans la presse ou les documents officiels ; la précision est indiquée dans `precision_date` (`jour`, `mois`, `approximative`).
3. **Linéaire relevé.** `km_releves_2022` reprend l'ONISR ; `km_releves` reprend le chiffre le plus récent (L'Argus 2026). `part_releve = km_releves / km_reseau` (plafonnée à 1).
4. **Étendue.** `total` si `part_releve ≥ 0,8`, `partiel` sinon, `aucun` si aucun relèvement. Ce seuil retrouve les 7 départements « quasi totaux » de l'ONISR (Allier, Aveyron, Cantal, Corrèze, Creuse, Lozère, Puy-de-Dôme), plus l'Ardèche (totale selon L'Argus et la LDC) et l'Eure (2026).
5. **Paris** est ajouté (absent du tableau ONISR) avec `etendue = aucun` : il n'a aucune route éligible.

## Points à vérifier (avant le rendu)

Le plan demande **deux sources concordantes pour chaque date**. À ce stade :

- les dates des 45 départements de l'ONISR ne reposent que sur l'ONISR (source officielle), sauf Corrèze et Cantal (confirmées par Weka) : **trouver une seconde source** (délibération ou presse locale) au moins pour les départements `total` ;
- **Tarn-et-Garonne** : date approximative (février 2023, d'après un article du 06/02/2023) ;
- **écarts de linéaire** ONISR 2022 / L'Argus 2026 : Haute-Loire (270 / 110 km), Vienne (429 / 200 km), Sarthe (930 / 610 km), Indre (400 / 219 km). Retours partiels à 80 km/h, ou erreurs de recensement ?
- **extensions sans date** : Yonne (450 → 1 511 km), Gers (350 → 570 km) ;
- **annulations en justice** : Corrèze (TA Limoges, 04/07/2023, effet au 01/01/2024), Orne (TA Caen, 25/11/2022), Hautes-Alpes (TA Marseille, 08/11/2022), Hérault (TA Montpellier 2022 et CAA Toulouse 2026), Sarthe (TA Nantes, 13/12/2023). Ces départements figurent toujours comme relevés en 2026 : vérifier si de nouveaux arrêtés ont été pris et s'il y a eu une période de retour à 80 km/h ;
- **Isère** : passage de tout le réseau annoncé au 01/01/2027 (hors période d'étude).

## Choix pour l'analyse

La période BAAC s'arrête fin 2024. Les départements relevés après le 31/12/2024 (Morbihan, Eure) sont comptés dans le groupe `G80` (voir `src/indicateurs.affecter_groupes`).

## Dictionnaire des colonnes

| Colonne | Description |
|---|---|
| `code_dep`, `nom_dep` | Code et nom officiels du département |
| `typologie_cerema` | z1 montagneux, z2 rural peu dense, z3 méditerranéen, z4 monopolarisé, z5 multipolarisé, z6 forte densité, z7 Paris et petite couronne |
| `releve` | Au moins une route relevée à 90 km/h (à la date de la collecte) |
| `date_releve`, `precision_date` | Date du premier relèvement et sa précision |
| `etendue` | `total`, `partiel` ou `aucun` |
| `km_releves_2022` | km relevés au 31/12/2022 (ONISR) |
| `km_releves` | km relevés, chiffre le plus récent (L'Argus 2026) |
| `km_reseau` | Linéaire total de RD (ONISR) |
| `part_releve` | `km_releves / km_reseau` |
| `etapes` | Étapes successives `date:km` (ONISR) |
| `tues_ha_2019_onisr`, `tues_ha_2022_onisr` | Tués hors agglomération hors autoroute selon l'ONISR (contrôle de nos calculs) |
| `source_1`, `source_2`, `commentaire` | Sources et remarques |
