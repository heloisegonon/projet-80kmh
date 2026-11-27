# 80 km/h, retour aux 90 km/h : quel effet sur la mortalité routière ?

Projet *Python pour la data science*, ENSAE 2e année (2026-2027), cours de Lino Galiana.

> **Rapport en ligne : [heloisegonon.github.io/projet-80kmh](https://heloisegonon.github.io/projet-80kmh/)** — le notebook mis en page avec Quarto, avec tous les graphiques et tableaux.
>
> **État : version finale.** Le rapport complet est dans [`main.ipynb`](main.ipynb) ; le cadrage initial du projet est dans [`docs/plan_projet.md`](docs/plan_projet.md).

## Problématique

Le 1er juillet 2018, la vitesse maximale est passée de 90 à 80 km/h sur les routes bidirectionnelles hors agglomération. Depuis la loi d'orientation des mobilités (décembre 2019), les départements peuvent revenir aux 90 km/h : 50 l'avaient fait fin 2024, à des dates et sur des linéaires très différents. Nous exploitons cette expérience naturelle pour mesurer l'effet de la vitesse autorisée sur la mortalité routière.

## Résultats principaux

- **Données validées.** De 2017 à 2024, nos tués en métropole sont identiques, année par année, aux chiffres publiés par l'ONISR. Ce contrôle a permis de corriger une erreur de codage des départements dans le fichier de 2019.
- **H1, le passage à 80 km/h (2018) : effet plausible mais modeste.** En 2019, à trafic constant, les tués baissent de 9 % sur le réseau concerné par rapport à 2015-2017, soit 2 à 4 points de plus que sur les autres réseaux. Cet écart est du même ordre qu'un biais de codage des BAAC en 2019, et bien plus faible que l'effet estimé par le Cerema (−12 %).
- **H2, le retour aux 90 km/h : pas démontré.** Sur les mêmes mois, les départements relevés font un peu moins bien que ceux restés à 80 km/h (+14 points en différence de différences, intervalle approché de 4 à 24). Le résultat dépend des dates de relèvement : en les avançant de six mois, l'écart tombe à +2 points.
- **H3, l'intensité du relèvement : compatible, non démontrée.** Les 8 départements relevés en totalité s'écartent nettement de ceux restés à 80 km/h (+48 points), dans toutes nos approches. Mais ils sont presque tous de montagne, ne comptent qu'une centaine de tués, et leurs routes non relevées se dégradent encore plus (+57 %) : l'écart vient probablement en partie, voire en totalité, de facteurs locaux.
- **H4, le mécanisme par les chocs frontaux et les sorties de route : non confirmée.** Les collisions frontales baissent autant ou davantage dans les départements relevés que dans ceux restés à 80 km/h. Seule la hausse des sorties de route dans les départements à relèvement partiel (+19 %, contre +2 %) va dans le sens de cette hypothèse.
- **Radars fixes (Q3, piste exploratoire) : non concluant.** Autour des 924 radars mis en service en 2020-2022, les accidents baissent de 3 % en deux ans, contre une hausse d'environ 1 % attendue d'après la tendance nationale. Mais l'écart médian par radar est nul et la régression vers la moyenne domine : cette piste n'a pas été retenue dans le rapport.

En résumé, le retour aux 90 km/h coïncide avec une évolution moins favorable de la mortalité là où il a été le plus large, mais nos données ne permettent pas de l'attribuer au relèvement plutôt qu'aux spécificités des départements concernés.

## Données

| Source | Accès | Usage |
|---|---|---|
| Accidents corporels BAAC 2010-2024 (ONISR) | API data.gouv.fr | Tués, accidents, réseau, collisions |
| Départements revenus aux 90 km/h | **Table construite** : [`data/departements_90.csv`](data/departements_90.csv), méthode dans [`docs/collecte_departements.md`](docs/collecte_departements.md) | Groupes `G80`, `G90_partiel`, `G90_total` |
| Population au 1er janvier par département (INSEE) | API Melodi | Taux par habitant |
| Ventes de carburants routiers par département (SDES) | API DiDo | Indicateur indirect du trafic |
| Contours des départements (IGN) | `cartiflette` | Cartes |
| Radars fixes (ministère de l'Intérieur) | API data.gouv.fr | Question Q3, explorée mais non retenue |

Seule la table des relèvements est versionnée, avec la liste de secours des URL des fichiers BAAC ([`data/sources_baac.csv`](data/sources_baac.csv)). Tout le reste est téléchargé par le code.

## Reproduire les résultats

### Première fois

1. **Vérifier la version de Python** : `python3 --version` doit afficher 3.11 ou plus. Python n'est pas installé par le projet. Sur Mac, le `python3` fourni par Apple est parfois en version 3.9, avec laquelle le code ne fonctionne pas : installer une version récente, par exemple avec `brew install python@3.12`, puis utiliser `python3.12` à la place de `python3`.

2. **Récupérer le projet, créer l'environnement virtuel et installer les bibliothèques** :

   ```bash
   git clone https://github.com/heloisegonon/projet-80kmh.git
   cd projet-80kmh
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

   `pip` télécharge toutes les bibliothèques de `requirements.txt` (pandas, geopandas, Jupyter…) et leurs dépendances dans le dossier `.venv`, sans toucher au reste de la machine. Une connexion internet est nécessaire.

3. **Exécuter le notebook** : ouvrir `main.ipynb` **avec le noyau de l'environnement `.venv`** et lancer « Exécuter tout ». Dans VS Code, choisir `.venv` en haut à droite du notebook ; dans Jupyter, lancer `.venv/bin/jupyter lab`. Si un autre Jupyter est déjà installé sur la machine, il peut exécuter le notebook hors de l'environnement du projet et échouer sur `Missing optional dependency 'pyarrow'`. Pour tout exécuter sans ouvrir le notebook (le résultat est écrit dans `main_execute.ipynb`) :

   ```bash
   .venv/bin/jupyter nbconvert --to notebook --execute main.ipynb --output main_execute.ipynb --ExecutePreprocessor.timeout=3600
   ```

Le notebook enchaîne seul toutes les étapes : il télécharge les données, nettoie les BAAC, construit le panel, puis produit l'analyse et les graphiques. **Il n'y a aucun script à lancer à la main.**

**Durée.** Au premier lancement, le téléchargement (environ 330 Mo de fichiers BAAC), le nettoyage et la construction du panel prennent environ **4 minutes** (3 min 40 s mesurées sur un MacBook Air, avec l'installation des dépendances en 30 secondes en plus).

### Lancements suivants

Il suffit de revenir dans le dossier du projet et de réactiver l'environnement, sans rien réinstaller :

```bash
cd projet-80kmh
source .venv/bin/activate
```

puis de relancer le notebook (étape 3). Il relit les fichiers déjà construits dans `data/processed/` et ne retélécharge rien.

### Lancer une étape seule (facultatif)

Pour exécuter ou déboguer une étape isolément, les scripts se lancent depuis la racine du projet, **avec l'environnement `.venv` activé**, dans cet ordre (chacun utilise le fichier produit par le précédent) :

| Commande | Rôle |
|---|---|
| `python scripts/collecte.py` | télécharge les fichiers BAAC dans `data/raw/baac/` |
| `python scripts/clean_data.py` | nettoie et fusionne les 4 tables : `data/processed/accidents.parquet` |
| `python scripts/indicateurs.py` | construit le panel : `data/processed/panel_dep.parquet` |
| `python scripts/data_analysis.py` | statistiques descriptives sur le panel |

### En cas de problème

**Erreur de connexion (`ConnectionError`, `Connection refused`).** Les requêtes sont relancées automatiquement 5 fois. Si l'API de data.gouv.fr reste injoignable, le code utilise la liste versionnée des URL des fichiers ([`data/sources_baac.csv`](data/sources_baac.csv)), hébergés sur `static.data.gouv.fr`. Les données de contexte (population, carburants, radars, contours) sont recopiées dans `data/processed/contexte/` après chaque téléchargement réussi, et relues avec un avertissement `UserWarning` si la source en ligne ne répond plus. Si l'erreur persiste, c'est le réseau de la machine qui bloque l'accès. Pour le vérifier, la commande suivante doit afficher `200` (`000` signifie que la connexion est refusée ou bloquée) :

```bash
curl -s -o /dev/null -w "%{http_code}\n" "$(sed -n 2p data/sources_baac.csv | cut -d, -f3)"
```

Sur un réseau d'école ou d'entreprise, un proxy est souvent nécessaire : `env | grep -i proxy` affiche celui qui est configuré.

## Organisation

```
├── data/
│   ├── departements_90.csv     # table des relèvements, construite et sourcée
│   └── sources_baac.csv        # URL des fichiers BAAC (liste de secours)
├── docs/
│   ├── plan_projet.md          # cadrage du projet
│   └── collecte_departements.md
├── scripts/
│   ├── collecte.py             # API data.gouv, INSEE, SDES, cartiflette
│   ├── clean_data.py           # nettoyage et fusion des BAAC 2010-2024
│   ├── indicateurs.py          # groupes G80 / G90, panel département × mois, étude d'événement, différence de différences
│   ├── data_analysis.py        # statistiques descriptives, avant / après relèvement
│   └── graphiques.py           # palette et fonctions de visualisation du rapport
├── main.ipynb                  # le rapport
└── requirements.txt            # dépendances
```

## Conventions

- Branche par fonctionnalité, fusion dans `main` par pull request relue.
- Formatage : `ruff format scripts/`.


## Usage de l'intelligence artificielle

Le cours autorise les assistants de code, à condition que le travail reste le nôtre. Nous avons utilisé un assistant d'IA à plusieurs étapes du projet :

- **Recherche** : identifier les sources utiles (évaluations du Cerema et de l'ONISR, données publiques) et vérifier certains faits sur le contexte de la réforme.
- **Code** : propositions pour certaines fonctions (par exemple les statistiques descriptives et la comparaison avant / après relèvement de `scripts/data_analysis.py`), que nous avons relues, testées sur nos données et adaptées, ainsi qu'une aide au débogage et à l'utilisation de `git`.
- **Interprétation** : aide à la rédaction des commentaires de résultats, pour n'oublier aucun élément important des graphiques et des tableaux.
- **Vérification**, surtout : contrôle de nos interprétations, en confrontant chaque chiffre cité aux sorties du notebook et chaque conclusion aux résultats des autres sections, pour nous assurer qu'elles étaient justes et cohérentes entre elles.

Ces vérifications nous ont permis de corriger plusieurs erreurs, dont une venant d'une proposition de l'IA : le réseau témoin de `avant_apres_releve` était mal défini pour les routes départementales (corrigé dans la pull request n° 9). Nous ne nous sommes pas reposés sur l'IA pour valider nos données : nos comptages de tués sont d'abord contrôlés contre les chiffres officiels de l'ONISR (section 2.3 du notebook).
