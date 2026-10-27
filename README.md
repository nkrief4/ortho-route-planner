# ortho-route-planner

Extraction, nettoyage, geocodage et optimisation de tournees pour les orthophonistes du RPPS (Repertoire Partage des Professionnels de Sante).

## Structure du projet

```
ortho-route-planner/
├── scraping/                         # 1. Extraction des donnees Annuaire Sante (ANS)
│   ├── import_open_data.py           #    Mise a jour depuis l'open data data.gouv.fr (recommande)
│   ├── main.py                       #    Extraction via l'API FHIR (cle ESANTE_API_KEY)
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
| `ESANTE_API_KEY` | `scraping/main.py` (extraction via l'API FHIR) | Non : `scraping/import_open_data.py` n'en a pas besoin |
| `MONGODB_URI` | `app.py` (suivi des sites visites) | Non : sans elle, l'interface fonctionne mais le marquage « visite » renvoie une erreur |
| `CARTO_API_KEY` | `pipeline/mapping.py` (fond de carte clair CARTO) | Non : sans elle, la carte utilise les tuiles OpenStreetMap |

#### Obtenir une cle CARTO (gratuite)

Depuis 2026, les tuiles CARTO (« CartoDB positron ») affichent « API KEY REQUIRED »
sans cle. Pour retrouver ce fond de carte :

1. Aller sur <https://carto.com/basemaps/apikey>, saisir son e-mail et cliquer sur le
   lien de connexion recu (pas de mot de passe).
2. Creer une cle dans le tableau de bord. Offre gratuite : 1 million de tuiles par
   mois en usage commercial, 5 millions en usage non commercial.
3. Restreindre la cle aux domaines du site (ex: `localhost`, `*.onrender.com`) : elle
   est visible dans le code de la page.
4. L'ajouter dans `.env` (`CARTO_API_KEY=...`) et dans les variables d'environnement
   du service Render.

Les donnees necessaires a l'interface web (`data/enriched/contacts_orthophonistes_basic.csv`
et `output/cache/geocode_cache.json`) sont deja dans le depot : pas besoin de lancer
le scraping pour travailler en local.

## 1. Extraction des donnees (scraping/)

Les orthophonistes (code profession 91) viennent de l'**Annuaire Sante** de l'Agence du
Numerique en Sante (ANS), alimente par le RPPS. Deux sources sont possibles.

### Mettre a jour la base (recommande : open data, sans cle)

L'ANS publie deux extractions sur data.gouv.fr, mises a jour regulierement :

- [Annuaire Sante - Extractions des donnees en libre acces (Format Zip)](https://www.data.gouv.fr/datasets/annuaire-sante-extractions-des-donnees-en-libre-acces-des-professionnels-intervenant-dans-le-systeme-de-sante-rpps-format-zip) :
  professionnels, lieux d'exercice, telephone et email du cabinet (~230 Mo).
- [Annuaire Sante - Extraction des BAL MSSante (Format Zip)](https://www.data.gouv.fr/datasets/annuaire-sante-extraction-des-bal-mssante-format-zip) :
  adresses de messagerie securisee MSSante (~22 Mo), rattachees par numero RPPS.

```bash
# Telecharge les dernieres extractions (dans data/raw/) et regenere
# data/enriched/contacts_orthophonistes_basic.csv
venv/bin/python scraping/import_open_data.py

# Puis lancer l'app une fois en local : au demarrage, les adresses absentes du cache
# sont geocodees (~45 min pour 4 000 nouvelles adresses) et ajoutees au cache
venv/bin/python app.py --port 5001
```

Versionner ensuite `data/enriched/contacts_orthophonistes_basic.csv` et
`output/cache/geocode_cache.json` : sur Render, toutes les adresses sont alors deja dans
le cache et le demarrage reste rapide.

Le script reconstruit les adresses au meme format que l'API FHIR, ce qui permet de
reutiliser le cache de geocodage existant.

### Liens utiles (Annuaire Sante / API FHIR)

- Guide d'implementation FHIR de l'Annuaire Sante : <https://interop.esante.gouv.fr/ig/fhir/annuaire/>
- Documentation de l'API FHIR : <https://ansforge.github.io/annuaire-sante-fhir-documentation/>
- Etat des services eSante (pannes, maintenances) : <https://status.esante.gouv.fr/>
- Code source du serveur FHIR : <https://github.com/ansforge/annuaire-sante-fhir-serveur>
- Signaler un probleme ou poser une question : <https://github.com/ansforge/annuaire-sante-fhir-documentation/issues>

### Extraction via l'API FHIR (cle ESANTE_API_KEY)

Alternative plus lente a l'open data. Les donnees viennent de deux requetes :

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

Puis geocoder les nouvelles adresses et versionner les deux fichiers, comme apres une
mise a jour open data (voir plus haut). Sans le cache a jour, le site en ligne
geocoderait les nouvelles adresses a chaque demarrage.

Autres options de `scraping/main.py` :

```bash
# Mode interactif (affiche les codes, demande la saisie)
venv/bin/python scraping/main.py

# Enrichissement seul (si le brut existe deja)
venv/bin/python scraping/main.py --code 91 --resume --enrich-only
```

#### Exporter un CSV simplifie

```bash
venv/bin/python scraping/extract_contact_columns.py
```

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

> `--skip-geocode` démarre avec le cache seul, sans aucune requête de géocodage :
> utile juste après une mise à jour des données, pour tester sans attendre. Les
> adresses absentes du cache (statut PENDING) n'apparaissent alors pas sur la carte.

> **macOS :** le port 5000 est occupé par le récepteur AirPlay (erreur
> « Address already in use » ou page 403). Lancez avec `--port 5001`, ou désactivez
> « Récepteur AirPlay » dans Réglages Système > Général > AirDrop et Handoff.

### Fonctionnalités

- **Recherche autocomplete** : tape quelques lettres pour filtrer parmi les ~6 300 communes
  (nom officiel INSEE : « BOURG-EN-BRESSE » et « BOURG EN BRESSE » ne font qu'une)
- **Navigation clavier** : ↑↓ pour naviguer, Enter pour sélectionner
- **Filtre par arrondissement** : pour Paris, Lyon, Marseille, etc. Le code postal retenu
  est celui de la position geocodee : un cabinet en CEDEX (75651) apparait dans son
  arrondissement (75013)
- **Génération d'itinéraire en temps réel** : calcul TSP + carte interactive. Le temps de
  calcul est automatique (1 s jusqu'a 30 sites, 5 s jusqu'a 200, 10 s au-dela) ; les
  temps de trajet deja obtenus sont gardes en memoire, donc regenerer la meme zone
  (autre depart, sites visites retires...) est quasi immediat
- **Statistiques détaillées** : durée totale, moyenne par segment, nombre de sites
- **Liste ordonnée** : ordre de visite optimal avec durées. Les cabinets localises
  seulement a peu pres (statut WARNING : rue voisine ou centre de la commune) sont
  marques « ≈ approximatif » et affichent leur adresse officielle
- **Annuaire** : recherche, filtres (ville, code postal, avec telephone, avec email) et
  bouton « Exporter (Excel) » qui telecharge toute la liste filtree (onglet « Filtres »
  rappelant les criteres). Un nom de ville complet ne garde que cette ville
  (« Lyon » exclut Lyons-la-Foret)

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
| 4 | Geocodage (cache, fallback, retry ; filtre commune INSEE, controle de la commune) | data.geopf.fr |
| 5 | Carte des sites (couleur par score) | Folium |
| 6 | Matrice NxN durees routieres (1 requete jusqu'a 100 sites, blocs au-dela, cache) | OSRM Table API |
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
| `--tsp-limit` | Temps max du solveur TSP en secondes (defaut: auto, 1 a 10 s) |
| `--input` | Chemin CSV source (defaut: data/enriched/) |
| `--output` | Dossier de sortie (defaut: output/) |
