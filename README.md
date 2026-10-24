# ortho-route-planner

Extraction, nettoyage, geocodage et optimisation de tournees pour les orthophonistes du RPPS (Repertoire Partage des Professionnels de Sante).

## Structure du projet

```
ortho-route-planner/
├── scraping/                         # 1. Extraction des donnees depuis l'API eSante
│   ├── main.py                       #    Pipeline complet : extraction brute + enrichissement
│   ├── check_api.py                  #    Test de connectivite API
│   ├── extract_contact_columns.py    #    Export CSV simplifie (colonnes contacts)
│   ├── env_utils.py                  #    Chargement du fichier .env
│   └── code_profession.json          #    Codes professions disponibles
│
├── pipeline/                         # 2. Nettoyage, geocodage et routing
│   ├── __init__.py
│   ├── config.py                     #    Chemins, constantes, abbreviations
│   ├── load.py                       #    Phase 1 : chargement CSV + validation
│   ├── clean.py                      #    Phase 2 : normalisation adresses FR
│   ├── sites.py                      #    Phase 3 : table sites dedoublonnee
│   ├── geocode.py                    #    Phase 4 : geocodage API data.geopf.fr
│   ├── mapping.py                    #    Phase 5+8 : cartes Folium
│   ├── routing.py                    #    Phase 6+7 : matrice OSRM + TSP OR-Tools
│   └── db.py                         #    Suivi des visites (MongoDB Atlas)
│
├── app.py                            # 3. Interface web Flask
├── templates/index.html              #    Page de l'interface web
├── run_pipeline.py                   # Point d'entree du pipeline (phases 1-8)
│
├── data/
│   ├── raw/                          #    Exports bruts API (non versionnes)
│   ├── enriched/                     #    Exports enrichis (seul contacts_orthophonistes_basic.csv est versionne)
│   └── exports/                      #    Exports manuels (xlsx, csv)
│
├── output/                           # Fichiers generes par le pipeline
│   ├── cache/geocode_cache.json      #    Cache geocodage (evite les re-requetes)
│   ├── sites_clean.csv               #    Sites uniques normalises
│   ├── orthos_with_site_id.csv       #    Orthos + site_id
│   ├── sites_geocoded.csv            #    Sites + lat/lon/score
│   ├── route_solution_sites.csv      #    Itineraire optimal (ordre + durees)
│   ├── map_sites.html                #    Carte des sites
│   └── map_route.html                #    Carte de l'itineraire
│
├── requirements.txt                  # Dependances Python (versions figees)
├── render.yaml                       # Configuration du deploiement Render
├── .env                              # Cles et secrets (non versionne, a creer)
├── .env.example                      # Modele de .env
├── .gitignore
├── venv/                             # Environnement virtuel Python (non versionne, a creer)
└── README.md
```

## Installation

### Prerequis

- **Python 3.11 ou plus recent** (`pandas==3.0.0` ne s'installe pas en dessous).
  Verifier avec `python3 --version`. Le Python fourni par macOS (3.9) ne convient pas :
  installer une version recente via [python.org](https://www.python.org/downloads/)
  ou `brew install python@3.12`.
- git

### Etapes (macOS / Linux)

```bash
# Recuperer le projet
git clone https://github.com/nkrief4/ortho-route-planner.git
cd ortho-route-planner

# Creer l'environnement virtuel
python3 -m venv venv

# Installer toutes les dependances (Flask, pandas, OR-Tools, pymongo...)
venv/bin/pip install -r requirements.txt

# Creer le fichier de configuration
cp .env.example .env
```

### Etapes (Windows, PowerShell)

```powershell
git clone https://github.com/nkrief4/ortho-route-planner.git
cd ortho-route-planner
py -3.12 -m venv venv          # ou toute autre version >= 3.11
venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

Sous Windows, remplacer `venv/bin/python` par `venv\Scripts\python` dans toutes
les commandes de ce README.

### Configurer `.env`

| Variable | Utilisee par | Obligatoire ? |
|----------|--------------|---------------|
| `ESANTE_API_KEY` | `scraping/` (extraction RPPS) | Seulement pour relancer l'extraction |
| `MONGODB_URI` | `app.py` (suivi des sites visites) | Non : sans elle, l'interface fonctionne mais le marquage « visite » renvoie une erreur |

Les donnees necessaires a l'interface web (`data/enriched/contacts_orthophonistes_basic.csv`
et `output/cache/geocode_cache.json`) sont deja dans le depot : pas besoin de lancer
le scraping pour travailler en local.

## 1. Extraction des donnees (scraping/)

### Tester la connexion API

```bash
venv/bin/python scraping/check_api.py
```

### Extraire les orthophonistes

```bash
# Mode interactif (affiche les codes, demande la saisie)
venv/bin/python scraping/main.py

# Code specifique (91 = orthophonistes)
venv/bin/python scraping/main.py --code 91 --resume

# Enrichissement seul (si le brut existe deja)
venv/bin/python scraping/main.py --code 91 --resume --enrich-only
```

### Exporter un CSV simplifie

```bash
venv/bin/python scraping/extract_contact_columns.py
```

### Mettre a jour toutes les donnees

Les donnees viennent de l'API Annuaire Sante de l'ANS (FHIR) :

1. `Practitioner?qualification-code=91` : la liste des orthophonistes (nom, RPPS, MSSante).
2. Pour chacun, `PractitionerRole?practitioner=<id>&active=true&_include=PractitionerRole:organization` :
   ses lieux d'exercice actifs et la fiche du cabinet (adresse, telephone, email).
   Le telephone et l'email sont donc ceux du cabinet, pas de la personne.

**A lancer depuis un ordinateur personnel** : l'API refuse les adresses IP des serveurs
cloud (« Your IP ... is not allowed to reach this resource »). Compter 1h30 a 3h.

```bash
venv/bin/python scraping/check_api.py                             # verifie la cle ESANTE_API_KEY
caffeinate -i venv/bin/python scraping/main.py --code 91 --resume  # macOS : empeche la veille
                                                                  # relancer la meme commande reprend la ou elle s'est arretee
cp data/enriched/contacts_orthophoniste_91.csv data/enriched/contacts_orthophonistes_basic.csv
```

Puis geocoder les nouvelles adresses en lancant `venv/bin/python app.py` une fois
(le cache `output/cache/geocode_cache.json` est complete), et versionner les deux
fichiers (`contacts_orthophonistes_basic.csv` et `geocode_cache.json`). Sans le cache
a jour, le site en ligne geocoderait les nouvelles adresses a chaque demarrage.

## 2. Interface Web (app.py)

### Lancer l'interface

```bash
venv/bin/python app.py

# Port custom
venv/bin/python app.py --port 5001
```

Le démarrage prend quelques secondes : toutes les adresses sont déjà dans
`output/cache/geocode_cache.json`, donc aucune requête de géocodage n'est faite.
Seules les adresses absentes du cache sont envoyées à l'API.

> L'option `--skip-geocode` est inutile : elle n'a actuellement aucun effet, et le
> cache rend déjà le démarrage rapide.

> **macOS :** le port 5000 est occupé par le récepteur AirPlay (erreur
> « Address already in use » ou page 403). Lancez avec `--port 5001`, ou désactivez
> « Récepteur AirPlay » dans Réglages Système > Général > AirDrop et Handoff.

### Fonctionnalités

- **Recherche autocomplete** : tape quelques lettres pour filtrer parmi 6060 villes
- **Navigation clavier** : ↑↓ pour naviguer, Enter pour sélectionner
- **Filtre par arrondissement** : pour Paris, Lyon, Marseille, etc.
- **Génération d'itinéraire en temps réel** : calcul TSP + carte interactive
- **Statistiques détaillées** : durée totale, moyenne par segment, nombre de sites
- **Liste ordonnée** : ordre de visite optimal avec durées

### Interface

```
http://127.0.0.1:5000

┌─────────────────────────────────────────┐
│ Sidebar                │ Carte           │
│ • Recherche ville      │ [Map Folium]    │
│ • Filtre CP/Arrondt    │                 │
│ • Paramètres TSP       │ + route tracée  │
│ • Stats résultat       │ + marqueurs     │
│ • Liste arrêts         │                 │
└─────────────────────────────────────────┘
```

## 3. Pipeline adresses (run_pipeline.py)

### Phases disponibles

| Phase | Description | Technologie |
|-------|-------------|-------------|
| 1 | Chargement CSV + validation | pandas |
| 2 | Normalisation adresses FR | regex, unicodedata |
| 3 | Table sites dedoublonnee + mapping ortho-site | MD5, groupby |
| 4 | Geocodage (cache, fallback, retry) | data.geopf.fr |
| 5 | Carte des sites (couleur par score) | Folium |
| 6 | Matrice NxN durees routieres (batching) | OSRM Table API |
| 7 | TSP - itineraire optimal | OR-Tools |
| 8 | Carte de l'itineraire (trace routier) | OSRM Route + Folium |

### Commandes

```bash
# Nettoyage seul (phases 1-3)
venv/bin/python run_pipeline.py

# Pipeline complet sur un arrondissement
venv/bin/python run_pipeline.py --phases all --dept 75005

# Pipeline complet sur Paris
venv/bin/python run_pipeline.py --phases all --city PARIS

# Pipeline complet sur un departement
venv/bin/python run_pipeline.py --phases all --dept 92

# Jusqu'a la carte (sans routing)
venv/bin/python run_pipeline.py --phases 1,2,3,4,5 --city PARIS

# TSP en boucle fermee avec plus de temps
venv/bin/python run_pipeline.py --phases all --dept 75005 --closed-loop --tsp-limit 60
```

### Options CLI

| Option | Description |
|--------|-------------|
| `--phases` | Phases a executer : `1,2,3` ou `all` |
| `--city` | Filtrer sur une ville (ex: `PARIS`) |
| `--dept` | Filtrer sur un code postal (ex: `75`, `75005`, `92`) |
| `--closed-loop` | TSP en boucle fermee (retour au depart) |
| `--tsp-limit` | Temps max du solveur TSP en secondes (defaut: 30) |
| `--input` | Chemin CSV source (defaut: data/enriched/) |
| `--output` | Dossier de sortie (defaut: output/) |
