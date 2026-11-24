# 80 km/h, retour aux 90 km/h et radars : quel effet sur la mortalité routière ?

Projet *Python pour la data science*, ENSAE 2e année (2026-2027), cours de Lino Galiana.

> **État : brouillon.** La collecte, le nettoyage, le panel départemental et la structure du rapport sont en place ; l'analyse et la rédaction sont en cours. Le cadrage complet est dans [`docs/plan_projet.md`](docs/plan_projet.md).

## Problématique

Le 1er juillet 2018, la vitesse maximale est passée de 90 à 80 km/h sur les routes bidirectionnelles hors agglomération. Depuis la loi d'orientation des mobilités (décembre 2019), les départements peuvent revenir aux 90 km/h : 50 l'avaient fait fin 2024, à des dates et sur des linéaires très différents. Nous exploitons cette expérience naturelle pour mesurer l'effet de la vitesse autorisée sur la mortalité routière.

## Données

| Source | Accès | Usage |
|---|---|---|
| Accidents corporels BAAC 2010-2024 (ONISR) | API data.gouv.fr | Tués, accidents, réseau, collisions |
| Départements revenus aux 90 km/h | **Table construite** : [`data/departements_90.csv`](data/departements_90.csv), méthode dans [`docs/collecte_departements.md`](docs/collecte_departements.md) | Groupes `G80`, `G90_partiel`, `G90_total` |
| Population au 1er janvier par département (INSEE) | API Melodi | Taux par habitant |
| Ventes de carburants routiers par département (SDES) | API DiDo | Indicateur indirect du trafic |
| Contours des départements (IGN) | `cartiflette` | Cartes |
| Radars fixes (ministère de l'Intérieur) | API data.gouv.fr | Radars actifs par département et par mois |

Seule la table des relèvements est versionnée, avec la liste de secours des URL des fichiers BAAC ([`data/sources_baac.csv`](data/sources_baac.csv)). Tout le reste est téléchargé par le code.

## Reproduire les résultats

```bash
git clone https://github.com/heloisegonon/projet-80kmh.git
cd projet-80kmh
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Puis ouvrir `main.ipynb` et lancer « Exécuter tout » : au premier lancement, le notebook télécharge les données, les nettoie et construit le panel, puis relit les fichiers de `data/processed/` aux lancements suivants.

Chaque étape peut aussi se lancer séparément, depuis la racine du projet :

```bash
python scripts/collecte.py        # télécharge les fichiers BAAC dans data/raw/baac/
python scripts/clean_data.py      # nettoie et fusionne les 4 tables : data/processed/accidents.parquet
python scripts/indicateurs.py     # construit le panel : data/processed/panel_dep.parquet
python scripts/data_analysis.py   # statistiques descriptives sur le panel
```

**Erreur de connexion (`ConnectionError`, `Connection refused`).** Les requêtes sont relancées automatiquement 5 fois. Si l'API de data.gouv.fr reste injoignable, le code utilise la liste versionnée des URL des fichiers ([`data/sources_baac.csv`](data/sources_baac.csv)), hébergés sur `static.data.gouv.fr`. Les données de contexte (population, carburants, radars, contours) sont recopiées dans `data/processed/contexte/` après chaque téléchargement réussi, et relues avec un avertissement si la source en ligne ne répond plus. Si l'erreur persiste, c'est le réseau de la machine qui bloque l'accès. Pour vérifier :

```bash
# doit afficher 200 ; « 000 » signifie que la connexion est refusée ou bloquée
curl -s -o /dev/null -w "%{http_code}\n" "$(sed -n 2p data/sources_baac.csv | cut -d, -f3)"
# un réseau d'école ou d'entreprise impose souvent un proxy (variables HTTPS_PROXY)
env | grep -i proxy
```

## Organisation

```
├── data/
│   ├── departements_90.csv     # table des relèvements, construite et sourcée
│   └── sources_baac.csv        # URL des fichiers BAAC (liste de secours)
├── docs/
│   ├── plan_projet.md          # cadrage du projet
│   └── collecte_departements.md
├── scripts/
│   ├── collecte.py             # API data.gouv, INSEE, SDES, cartiflette, S3
│   ├── clean_data.py           # nettoyage et fusion des BAAC 2010-2024
│   ├── indicateurs.py          # groupes G80 / G90, panel département × mois, étude d'événement, différence de différences
│   ├── data_analysis.py        # statistiques descriptives, avant / après relèvement
│   └── graphiques.py           # palette et fonctions de visualisation du rapport
├── main.ipynb                  # le rapport
└── pyproject.toml
```

## Conventions

- Branche par fonctionnalité, fusion dans `main` par pull request relue.
- Formatage : `ruff format scripts/`.
