# Guide d'utilisation : Interface Web

## 🚀 Démarrage rapide

### 1. Lancer l'application

```bash
cd /Users/nathankrief/Desktop/get_ortho
venv/bin/python app.py
```

**Temps de démarrage :**
- Première fois (avec géocodage) : ~20-25 minutes
- Fois suivantes (cache existant) : ~2 secondes

```
============================================================
  PHASE 1 — Chargement du CSV
============================================================
  26867 lignes chargées

============================================================
  PHASE 2 — Normalisation des adresses
============================================================
  26851 adresses normalisées

============================================================
  PHASE 3 — Création table Sites
============================================================
  17823 sites uniques

============================================================
  PHASE 4 — Géocodage des sites (avec cache)
============================================================
  [17823/17823]  cache=17823  new=0  erreurs=0
  OK    (score >= 0.7): 15234  (85.5%)
  WARN  (0.5 – 0.7)  : 2089   (11.7%)
  FAILED (< 0.5)     : 500    (2.8%)

============================================================
  Données prêtes en 2.1s — 6060 villes disponibles
============================================================

  Serveur web : http://127.0.0.1:5000
  Ctrl+C pour arrêter
```

### 2. Ouvrir dans le navigateur

```
http://127.0.0.1:5000
```

---

## 📝 Tutoriel pas à pas

### Scénario 1 : Démarcher Paris 15e

#### Étape 1 : Rechercher la ville
```
1. Clique dans le champ "Ville"
2. Tape "pari"
3. Le dropdown affiche :
   ┌─────────────────────────────────────┐
   │ PARIS                               │
   │ 1288 orthophonistes · 728 sites     │
   ├─────────────────────────────────────┤
   │ PARIGNE                             │
   │ 3 orthophonistes · 2 sites          │
   └─────────────────────────────────────┘
4. Clique sur "PARIS" (ou appuie sur Enter)
```

#### Étape 2 : Sélectionner l'arrondissement
```
Le dropdown "Code postal / Arrondissement" se remplit automatiquement :
┌─────────────────┐
│ Toute la ville  │
│ 75001           │
│ 75002           │
│ ...             │
│ 75015  ← choisis celui-ci
│ ...             │
│ 75020           │
└─────────────────┘
```

#### Étape 3 : Configurer le TSP
```
TSP (sec) : [30]  ← durée du calcul (30s recommandé)
☐ Boucle fermée   ← coche si tu veux revenir au point de départ
```

#### Étape 4 : Générer l'itinéraire
```
Clique sur "Générer l'itinéraire"

Loading :
⭕ Calcul de la matrice de distances…
   (requêtes OSRM : ~2-3 minutes pour 162 sites)
```

#### Étape 5 : Résultat
```
┌─────────────────────────────────────────────────────┐
│ RÉSULTAT                                            │
├─────────────────────────────────────────────────────┤
│  162 sites    │  8.4h          │  3.1 min    │ 162  │
│  visités      │  durée totale  │  moy/seg    │ orthos│
└─────────────────────────────────────────────────────┘

ITINÉRAIRE
──────────────────────────────────────
① 15 Boulevard Victor                 Départ
  3 orthophonistes
                                      +2.5 min
② 185 Boulevard Raymond Losserand
  1 orthophoniste
                                      +1.8 min
③ 22 Rue de Vaugirard
  2 orthophonistes
...
```

**Carte interactive** :
- Polyline bleue = tracé routier
- Marqueurs numérotés = ordre de visite
- 🟢 Vert = départ
- 🔵 Bleu = intermédiaire
- 🔴 Rouge = arrivée

---

### Scénario 2 : Démarcher Marseille complète

```
1. Tape "mars" dans le champ ville
2. Sélectionne "MARSEILLE"
3. Laisse "Toute la ville"
4. TSP : 60s (beaucoup de sites)
5. Génère

Résultat :
- 536 sites visités
- 24.8h de trajet
- ~2.8 min par segment
```

---

### Scénario 3 : Test rapide sur petite ville

```
1. Tape "dijo" dans le champ ville
2. Sélectionne "DIJON"
3. Toute la ville (97 sites)
4. TSP : 10s (ville moyenne)
5. Génère en ~1 minute

Résultat :
- 97 sites visités
- 4.2h de trajet
```

---

## ⌨️ Raccourcis clavier

| Touche | Action |
|--------|--------|
| **↓** | Descendre dans le dropdown |
| **↑** | Remonter dans le dropdown |
| **Enter** | Sélectionner la ville surlignée |
| **Escape** | Fermer le dropdown |
| **Tab** | Passer au champ suivant |

---

## 🎨 Interface détaillée

### Header
```
╔════════════════════════════════════════════════════╗
║ Ortho Route Planner     6060 villes · 17823 sites ║
╚════════════════════════════════════════════════════╝
```

### Sidebar (gauche)
```
╔═══════════════════════════════════╗
║ FILTRE                            ║
╟───────────────────────────────────╢
║ Ville                             ║
║ [Rechercher une ville...]         ║
║                                   ║
║ Code postal / Arrondissement      ║
║ [Toute la ville ▼]                ║
║                                   ║
║ 728 sites — 1288 orthophonistes   ║
║                                   ║
║ TSP (sec)  │  ☐ Boucle fermée     ║
║ [30]       │                      ║
║                                   ║
║ [Générer l'itinéraire]            ║
╟───────────────────────────────────╢
║ RÉSULTAT                          ║
║ ┌────────┬────────┬────────┬─────┐║
║ │ 162    │ 8.4h   │ 3.1min │ 162 │║
║ │ sites  │ durée  │ moy    │ orthos│║
║ └────────┴────────┴────────┴─────┘║
╟───────────────────────────────────╢
║ ITINÉRAIRE                        ║
║ ① 15 Bd Victor           Départ   ║
║   3 orthos                        ║
║ ② 185 Bd Losserand       +2.5min  ║
║   1 ortho                         ║
║ ...                               ║
╚═══════════════════════════════════╝
```

### Zone carte (droite)
```
╔═══════════════════════════════════════════╗
║                                           ║
║         [Carte Folium interactive]        ║
║                                           ║
║  🟢 ─────→ 🔵 ─────→ 🔵 ─────→ 🔴        ║
║                                           ║
║  Zoom : +/-                               ║
║  Déplacer : cliquer-glisser               ║
║  Info : cliquer sur un marqueur           ║
║                                           ║
╚═══════════════════════════════════════════╝
```

---

## 🐛 Résolution de problèmes

### Problème : "Aucune ville trouvée"
```
Cause : Faute de frappe ou ville trop petite
Solution : Vérifie l'orthographe ou tape moins de lettres
Exemple : "pris" → rien, "par" → PARIS
```

### Problème : "Trop de sites (500+) pour le calcul en temps réel"
```
Cause : Ville entière trop grande (ex: PARIS complète = 728 sites)
Solution : Filtre par arrondissement
Exemple : Sélectionne "75015" au lieu de "Toute la ville"
```

### Problème : Le calcul de la matrice est long
```
Normal pour > 100 sites :
- 50 sites : ~30 secondes
- 100 sites : ~1 minute
- 200 sites : ~3 minutes
- 300 sites : ~5 minutes

Cause : Requêtes OSRM avec throttle (1s entre chaque)
Solution : Patience ☕ ou filtre davantage
```

### Problème : Le serveur ne démarre pas
```
Erreur : "Fichier enrichi introuvable"
Solution : Lance d'abord l'extraction
  venv/bin/python scraping/main.py --code 91 --resume
```

### Problème : Géocodage bloqué à [X/17823]
```
Cause : Première fois, géocodage en cours
Temps : ~20-25 minutes (0.08s par site)
Solution : Laisse tourner, ne sera fait qu'une fois
Prochaine fois : utilise --skip-geocode
```

---

## 💡 Astuces

### Astuce 1 : Recherche partielle
```
Au lieu de taper le nom complet, tape 2-3 lettres :
- "tou" → TOULOUSE
- "bor" → BORDEAUX
- "nan" → NANTES
```

### Astuce 2 : TSP adaptatif
```
Ajuste le temps TSP selon le nombre de sites :
- < 50 sites : 10s suffit
- 50-100 sites : 30s recommandé
- 100-200 sites : 60s
- > 200 sites : 120s
```

### Astuce 3 : Export CSV
```
Après génération, le CSV de la route est dans :
output/route_solution_sites.csv

Colonnes :
- visit_order : ordre de visite
- geocoded_label : adresse
- nb_orthos : nombre d'orthos
- segment_min : durée depuis arrêt précédent
- cumul_h : cumul en heures
```

### Astuce 4 : Boucle fermée
```
Coche "Boucle fermée" si :
- Tu veux revenir au point de départ
- Tu as un véhicule de location à rendre
- Tu pars de chez toi

Laisse décochée si :
- Tu fais un aller simple
- Tu termines ta tournée ailleurs
```

---

## 📊 Performances attendues

### Temps de génération selon nombre de sites

| Sites | Matrice OSRM | TSP 30s | Total |
|-------|--------------|---------|-------|
| 10 | 2s | 0.1s | ~2s |
| 50 | 30s | 2s | ~32s |
| 100 | 2min | 5s | ~2min 5s |
| 200 | 5min | 15s | ~5min 15s |
| 300 | 8min | 30s | ~8min 30s |

### Qualité de l'itinéraire selon temps TSP

| Temps TSP | Qualité | Recommandation |
|-----------|---------|----------------|
| 5s | ~95% optimal | Rapide, acceptable |
| 30s | ~98% optimal | **Défaut recommandé** |
| 60s | ~99% optimal | Bonne qualité |
| 120s | ~99.5% optimal | Excellent |

---

## 🎯 Workflow complet recommandé

### 1. Préparation (une fois)
```bash
# Extraction des données
venv/bin/python scraping/main.py --code 91 --resume

# Premier lancement (géocodage)
venv/bin/python app.py
# Attendre ~25 minutes
```

### 2. Usage quotidien
```bash
# Lancement rapide
venv/bin/python app.py --skip-geocode
# Prêt en 2 secondes
```

### 3. Génération d'itinéraire
```
1. Recherche ville (2-3 lettres)
2. Sélectionne arrondissement si grande ville
3. Génère
4. Exporte CSV si besoin
5. Suis l'itinéraire sur le terrain
```

### 4. Mise à jour des données (mensuelle)
```bash
# Re-télécharge les orthos
venv/bin/python scraping/main.py --code 91 --resume

# Efface le cache de géocodage
rm output/cache/geocode_cache.json

# Re-lance avec géocodage complet
venv/bin/python app.py
```

---

## 🎁 Bonus : Export pour Google Maps

Le CSV `output/route_solution_sites.csv` peut être importé dans Google Maps :

```
1. Ouvre Google My Maps
2. Importe le CSV
3. Colonnes :
   - latitude → Latitude
   - longitude → Longitude
   - geocoded_label → Nom
4. Trace l'itinéraire manuellement en suivant l'ordre visit_order
```
