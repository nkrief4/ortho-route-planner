# 🔍 Debug Point de Départ - Comment ça fonctionne ?

## 📊 Flux complet du système

### Étape 1 : L'utilisateur entre une adresse

**Interface :**
```
┌────────────────────────────────────┐
│ Ville : Paris ✓                    │
│ Arrondissement : 75008             │
│                                    │
│ 📍 Point de départ (optionnel)     │
│ ┌──────────────────────────────┐   │
│ │ 15 Avenue des Champs-Élysées │   │
│ └──────────────────────────────┘   │
│                                    │
│ [Générer l'itinéraire]             │
└────────────────────────────────────┘
```

**Que se passe-t-il ?**
1. L'utilisateur sélectionne d'abord une ville : `Paris`
2. Optionnellement un département : `75008`
3. Entre une adresse : `15 Avenue des Champs-Élysées`
4. Clique sur "Générer l'itinéraire"

---

### Étape 2 : JavaScript récupère les données

**Code dans `templates/index.html` (ligne ~1061) :**
```javascript
async function generateRoute() {
    // Vérifier qu'une ville est sélectionnée
    if (!selectedCity) {
        showToast('Veuillez sélectionner une ville');
        return;
    }

    const city = selectedCity.name;           // "Paris"
    const dept = deptSelect.value;            // "75008" ou ""
    const startAddressInput = document.getElementById('startAddress').value.trim();
    // startAddressInput = "15 Avenue des Champs-Élysées"
}
```

---

### Étape 3 : Géocodage de l'adresse de départ

**Code JavaScript (ligne ~1086) :**
```javascript
if (startAddressInput) {
    loadingText.textContent = 'Géocodage du point de départ...';

    // Appel à l'API de géocodage avec la ville
    const geocodeResp = await fetch('/api/geocode', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            address: startAddressInput,    // "15 Avenue des Champs-Élysées"
            city: city,                    // "Paris"
            postal_code: dept              // "75008"
        }),
    });

    const geocodeData = await geocodeResp.json();
}
```

**Backend `/api/geocode` dans `app.py` (ligne ~177) :**
```python
@app.route("/api/geocode", methods=["POST"])
def api_geocode():
    body = request.get_json(force=True)
    address = body.get("address").strip()      # "15 Avenue des Champs-Élysées"
    city = body.get("city").strip()            # "Paris"
    postal_code = body.get("postal_code").strip()  # "75008"

    # Construire l'adresse complète
    full_address = f"{address}, {city}"
    # full_address = "15 Avenue des Champs-Élysées, Paris"

    # Appeler l'API de géocodage française
    result = geocode_one(
        address_line=full_address,
        postal_code=postal_code,
        city=city,
        address_normalized=full_address,
    )

    # Retourner les coordonnées GPS
    return jsonify({
        "geocoded_label": result["geocoded_label"],  # "15 Av. des Champs-Élysées, 75008 Paris"
        "latitude": result["latitude"],              # 48.8698
        "longitude": result["longitude"],            # 2.3078
        "score": result["score"],                    # 0.95 (confiance)
    })
```

**API utilisée :** `data.geopf.fr` (API de géocodage du gouvernement français)

---

### Étape 4 : Stockage du point de départ

**JavaScript (ligne ~1105) :**
```javascript
if (!geocodeResp.ok) {
    showToast('Impossible de géocoder l\'adresse de départ');
    return;
}

// Stocker le point de départ
startPoint = {
    lat: geocodeData.latitude,      // 48.8698
    lon: geocodeData.longitude,     // 2.3078
    address: geocodeData.geocoded_label  // "15 Av. des Champs-Élysées, 75008 Paris"
};

loadingText.textContent = `Départ: ${startPoint.address}`;
```

---

### Étape 5 : Génération de l'itinéraire

**JavaScript envoie à `/api/generate` (ligne ~1123) :**
```javascript
const body = {
    city: city,                  // "Paris"
    dept: dept,                  // "75008"
    closed_loop: closedLoop,     // false (chemin ouvert)
    tsp_limit: tspLimit,         // 30 secondes
};

// Ajouter le point de départ si défini
if (startPoint) {
    body.start_lat = startPoint.lat;        // 48.8698
    body.start_lon = startPoint.lon;        // 2.3078
    body.start_address = startPoint.address; // "15 Av. des Champs-Élysées..."
}

const resp = await fetch('/api/generate', {
    method: 'POST',
    body: JSON.stringify(body),
});
```

---

### Étape 6 : Backend filtre les sites

**Backend `app.py` (ligne ~278) :**
```python
# Filtrer les sites de la ville/département
df_routable = df_sites[
    (df_sites["city"] == city) &
    (dept == "" or df_sites["dept"].isin([dept])) &
    df_sites["latitude"].notna() &
    df_sites["longitude"].notna()
]

# Extraire les coordonnées GPS de tous les sites
coords = list(zip(df_routable["latitude"], df_routable["longitude"]))
# coords = [(48.87, 2.31), (48.88, 2.32), (48.86, 2.30), ...]
```

---

### Étape 7 : Ajout du point de départ

**Backend `app.py` (ligne ~349) :**
```python
start_point_idx = None

if start_lat is not None and start_lon is not None:
    # Vérifier si le point de départ existe déjà dans les sites
    is_existing = False
    for i, (lat, lon) in enumerate(coords):
        if abs(lat - start_lat) < 0.0001 and abs(lon - start_lon) < 0.0001:
            start_point_idx = i
            is_existing = True
            print(f"  [route] Point de départ = site existant (index {i})")
            break

    if not is_existing:
        # Ajouter le point de départ au début
        coords.insert(0, (start_lat, start_lon))
        start_point_idx = 0

        # Créer une ligne fictive dans df_routable
        start_row = pd.DataFrame([{
            "site_id": "START_POINT",
            "geocoded_label": start_address,
            "latitude": start_lat,
            "longitude": start_lon,
            "nb_orthos": 0,
        }])
        df_routable = pd.concat([start_row, df_routable], ignore_index=True)

        print(f"  [route] Point de départ ajouté : {start_address}")
```

**Résultat :**
- Si l'adresse correspond déjà à un cabinet → utiliser ce cabinet
- Sinon → ajouter un point fictif en position 0

---

### Étape 8 : Calcul de la matrice OSRM

**Backend `app.py` (ligne ~352) :**
```python
print(f"  [route] Calcul matrice OSRM pour {len(coords)} points…")
matrix = compute_duration_matrix(coords)
# matrix[i][j] = durée en secondes du site i au site j
# matrix[0][1] = 120 secondes (2 minutes)
```

**API utilisée :** OSRM (`router.project-osrm.org`)

---

### Étape 9 : Résolution du TSP

**Backend `app.py` (ligne ~360) :**
```python
if start_point_idx is not None:
    # Forcer le départ à start_point_idx
    route_order, total_duration = solve_tsp(
        matrix,
        open_path=True,      # Pas de retour au point de départ
        time_limit=30,
        start_index=start_point_idx  # Forcer départ à l'index 0
    )
else:
    # Laisser OR-Tools choisir le meilleur point de départ
    route_order, total_duration = solve_tsp(
        matrix,
        open_path=True,
        time_limit=30
    )
```

**OR-Tools dans `pipeline/routing.py` (ligne ~160) :**
```python
def solve_tsp(matrix, open_path=True, start_index=None):
    if open_path and start_index is not None:
        # Chemin ouvert avec point de départ forcé
        depot = start_index  # depot = 0
        size = n

    manager = pywrapcp.RoutingIndexManager(size, 1, depot)
    routing = pywrapcp.RoutingModel(manager)

    # Résolution TSP...
    solution = routing.SolveWithParameters(params)

    # Extraction de la route
    route = []
    idx = routing.Start(0)
    while not routing.IsEnd(idx):
        node = manager.IndexToNode(idx)
        if node != depot:
            route.append(node)
        idx = solution.Value(routing.NextVar(idx))

    return route, total_duration
```

**Résultat :**
```python
route_order = [0, 5, 12, 3, 8, 1, 9, ...]
# 0 = point de départ
# 5, 12, 3... = indices des sites dans l'ordre optimal
```

---

### Étape 10 : Affichage de la carte

**Backend `app.py` (ligne ~408) :**
```python
# Créer la carte avec l'itinéraire
m = create_route_map(df_routable_enriched, route_order, route_geom)
map_html = m._repr_html_()
```

**Carte Folium :**
- Marqueur vert #1 au point de départ
- Marqueurs bleus #2, #3, #4... pour les sites suivants
- Marqueur rouge au dernier arrêt
- Ligne bleue pour le tracé routier

---

## 🐛 Points de débogage

### 1. Vérifier que le géocodage fonctionne

**Test manuel :**
```bash
curl -X POST http://127.0.0.1:5000/api/geocode \
  -H "Content-Type: application/json" \
  -d '{
    "address": "15 Avenue des Champs-Élysées",
    "city": "Paris",
    "postal_code": "75008"
  }'
```

**Réponse attendue :**
```json
{
  "geocoded_label": "15 Avenue des Champs-Élysées, 75008 Paris",
  "latitude": 48.8698,
  "longitude": 2.3078,
  "score": 0.95
}
```

**Si erreur :**
```json
{
  "error": "Adresse introuvable"
}
```

---

### 2. Vérifier les logs backend

**Logs attendus dans la console :**
```
Géocodage : "15 Avenue des Champs-Élysées, Paris" → 48.8698, 2.3078
[filtre] Ville: Paris, Département: 75008
[route] Point de départ ajouté : 15 Avenue des Champs-Élysées, 75008 Paris
[route] Calcul matrice OSRM pour 24 points…
    OSRM [1/1] batches
[route] Résolution TSP (limit=30s, open=True)…
```

**Si erreur :**
```
[error] Géocodage échoué : score trop faible (0.12)
[error] NameError: name 'pd' is not defined
[error] KeyError: 'latitude'
```

---

### 3. Vérifier que le TSP démarre du bon point

**Ajouter un print dans `pipeline/routing.py` (ligne ~195) :**
```python
print(f"  [TSP] depot={depot}, start_index={start_index}, open_path={open_path}")
```

**Log attendu :**
```
[TSP] depot=0, start_index=0, open_path=True
```

---

### 4. Vérifier que le point de départ est dans df_routable

**Ajouter un print dans `app.py` (ligne ~360) :**
```python
print(f"  [debug] df_routable.head(3):")
print(df_routable.head(3)[["site_id", "geocoded_label", "latitude", "longitude"]])
```

**Résultat attendu :**
```
  [debug] df_routable.head(3):
      site_id                         geocoded_label  latitude  longitude
0  START_POINT  15 Av. Champs-Élysées, 75008 Paris   48.8698    2.3078
1  site_12345   10 Rue de la Paix, 75002 Paris       48.8687    2.3315
2  site_67890   5 Boulevard Haussmann, 75009 Paris   48.8742    2.3268
```

---

## 🚨 Problèmes fréquents

### Problème 1 : "Adresse introuvable"

**Cause :** L'API de géocodage ne trouve pas l'adresse

**Solutions :**
- Vérifier l'orthographe de l'adresse
- Essayer une adresse plus simple : `10 Rue de la Paix`
- Vérifier que la ville est bien sélectionnée
- Tester avec une adresse connue : `1 Avenue des Champs-Élysées`

### Problème 2 : Le TSP ne démarre pas du point de départ

**Cause :** `start_index` n'est pas passé correctement

**Vérification :**
```python
# Dans app.py ligne ~360
print(f"  [debug] start_point_idx = {start_point_idx}")

# Dans routing.py ligne ~195
print(f"  [debug] depot = {depot}")
```

**Si depot != 0**, vérifier la logique dans `routing.py` ligne ~183-198

### Problème 3 : NameError: name 'pd' is not defined

**Cause :** pandas n'est pas importé

**Solution :** Vérifier que `app.py` ligne 11 contient :
```python
import pandas as pd
```

### Problème 4 : Le marqueur vert n'apparaît pas

**Cause :** Le point de départ n'est pas dans `df_routable_enriched`

**Vérification :** Regarder les logs pour voir si :
```
[route] Point de départ ajouté : ...
```

---

## 🧪 Test complet pas à pas

### 1. Démarrer le serveur avec logs
```bash
venv/bin/python app.py
```

### 2. Ouvrir la console navigateur
- Chrome : F12 → Console
- Regarder les requêtes réseau (Network)

### 3. Tester le flux
1. Rechercher "Paris"
2. Entrer "15 Avenue des Champs-Élysées"
3. Cliquer "Générer l'itinéraire"

### 4. Observer les logs backend
```
Géocodage : "15 Avenue des Champs-Élysées, Paris"
[route] Point de départ ajouté : 15 Avenue des Champs-Élysées, 75008 Paris
[route] Calcul matrice OSRM pour 24 points…
[TSP] depot=0, start_index=0, open_path=True
```

### 5. Observer la console navigateur
```javascript
Départ: 15 Avenue des Champs-Élysées, 75008 Paris
Calcul de la matrice de distances…
```

### 6. Vérifier la carte
- ✅ Marqueur vert #1 au point de départ
- ✅ Ligne bleue commence au marqueur #1
- ✅ Liste des arrêts commence par le point de départ

---

## ✅ Quand ça fonctionne correctement

**Interface :**
```
#1 🟢 15 Avenue des Champs-Élysées, 75008 Paris
   👤 Point de départ                        +0 min

#2 🔵 10 Rue de la Paix, 75002 Paris
   👥 Marie DUPONT, Jean MARTIN               +2.5 min

#3 🔵 5 Boulevard Haussmann, 75009 Paris
   👤 Sophie BERNARD                          +3.1 min

...

#15 🔴 20 Rue du Faubourg Saint-Honoré
   👥 Pierre DURAND, Claire LEROY             +1.8 min
```

**Stats :**
```
Sites visités : 15
Durée totale  : 45 min (0.75 h)
Durée moy/seg : 3.2 min
```

---

## 📞 Si ça ne marche toujours pas

**Envoyer ces informations :**
1. Logs de la console backend
2. Message d'erreur dans le navigateur (console F12)
3. Ville et adresse testées
4. Screenshot de l'interface

**Commande pour obtenir les logs :**
```bash
venv/bin/python app.py 2>&1 | tee debug.log
```
