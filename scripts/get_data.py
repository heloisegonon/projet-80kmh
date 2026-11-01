"""
Téléchargement des données BAAC depuis data.gouv.fr.

Ce script récupérera les fichiers annuels :
- Caractéristiques
- Lieux
- Véhicules
- Usagers
"""

from pathlib import Path
import requests

# Adresse de l'API de data.gouv.fr
API_URL = (
    "https://www.data.gouv.fr/api/1/datasets/"
    "bases-de-donnees-annuelles-des-accidents-corporels-de-la-circulation-routiere-annees-de-2005-a-2025/"
)


def get_dataset_information():
    """Récupère les informations du jeu de données BAAC."""

    response = requests.get(API_URL, timeout=30)

    # Vérifie que la requête a fonctionné
    response.raise_for_status()

    # Transforme la réponse JSON en dictionnaire Python
    dataset = response.json()

    print("Jeu de données trouvé :", dataset["title"])
    print("Nombre de ressources :", len(dataset["resources"]))

    return dataset

def display_resources(dataset):
    """Affiche les informations principales des ressources BAAC."""

    for resource in dataset["resources"]:
        print(
            "Titre :", resource.get("title"),
            "| Format :", resource.get("format"),
            "| URL :", resource.get("url")
        )

def filter_baac_resources(dataset, years):
    """Sélectionne les quatre fichiers BAAC principaux par année."""

    categories = {
        "caracteristiques": "car",
        "lieux": "lieux",
        "vehicules": "vehicules",
        "usagers": "usagers"
    }

    selected_resources = {}

    for resource in dataset["resources"]:
        title = resource.get("title", "").lower()
        file_format = (resource.get("format") or "").lower()

        # On ne garde que les fichiers CSV
        if file_format != "csv":
            continue

        # On exclut les fichiers de véhicules immatriculés
        if "immatricul" in title:
            continue

        # On cherche l'année dans le titre
        for year in years:
            if str(year) not in title:
                continue

            # On identifie la catégorie du fichier
            for category, keyword in categories.items():
                if keyword in title:
                    selected_resources[(year, category)] = resource

    # Affichage et vérification
    for year in years:
        print(f"\n--- {year} ---")

        for category in categories:
            resource = selected_resources.get((year, category))

            if resource is None:
                print(f"MANQUANT : {category}")
            else:
                print(f"{category} : {resource['title']}")

    return selected_resources

def download_resources(resources):
    """Télécharge les fichiers BAAC sélectionnés dans data/raw/."""

    # Chemin vers le dossier data/raw/
    raw_data_dir = Path(__file__).resolve().parent.parent / "data" / "raw"

    # Crée le dossier s'il n'existe pas
    raw_data_dir.mkdir(parents=True, exist_ok=True)

    # Parcourt les 60 ressources sélectionnées
    for (year, category), resource in resources.items():

        # Construit le nom du fichier
        filename = f"{category}_{year}.csv"
        destination = raw_data_dir / filename

        # Évite de télécharger un fichier déjà présent
        if destination.exists():
            print(f"Déjà présent : {filename}")
            continue

        # Récupère l'adresse de téléchargement
        url = resource.get("url")

        if not url:
            print(f"URL manquante : {filename}")
            continue

        # Télécharge le fichier
        response = requests.get(url, timeout=120)
        response.raise_for_status()

        # Enregistre le fichier sur l'ordinateur
        destination.write_bytes(response.content)

        print(f"Téléchargé : {filename}")

if __name__ == "__main__":
    dataset = get_dataset_information()

    years = range(2010, 2025)

    selected_resources = filter_baac_resources(dataset, years)

    download_resources(selected_resources)