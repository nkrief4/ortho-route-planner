# get_ortho

Extraction, nettoyage, geocodage et optimisation de tournees pour les orthophonistes du RPPS (Repertoire Partage des Professionnels de Sante).

## Structure du projet

```
get_ortho/
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
│   └── routing.py                    #    Phase 6+7 : matrice OSRM + TSP OR-Tools
│
├── run_pipeline.py                   # Point d'entree du pipeline (phases 1-8)
│
├── data/
│   ├── raw/                          #    Exports bruts API (non versionnes)
│   ├── enriched/                     #    Exports enrichis (non versionnes)
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
├── .env                              # Cle API (non versionne)
├── .env.example                      # Modele de .env
├── .gitignore
├── venv/                             # Environnement virtuel Python
└── README.md
```

## Installation

```bash
# Creer l'environnement virtuel
python3 -m venv venv

# Installer les dependances
venv/bin/pip install pandas folium numpy ortools

# Configurer la cle API eSante
cp .env.example .env
# Editer .env et remplacer PUT_YOUR_API_KEY_HERE par votre cle
```

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

## 2. Interface Web (app.py)

### Lancer l'interface

```bash
# Première fois (avec géocodage complet)
venv/bin/python app.py

# Avec cache de géocodage existant (démarrage rapide)
venv/bin/python app.py --skip-geocode

# Port custom
venv/bin/python app.py --port 5001
```

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
# ortho-route-planner
