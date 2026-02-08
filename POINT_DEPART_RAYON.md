# Point de départ personnalisé et rayon de recherche

## 🎯 Objectif

Permettre à l'utilisateur de :
1. Spécifier une adresse de départ personnalisée pour commencer l'itinéraire
2. Filtrer les orthophonistes dans un rayon donné autour de cette adresse
3. Calculer le chemin optimal en partant de cette adresse

---

## 📍 Fonctionnalités

### 1️⃣ **Point de départ personnalisé**

L'utilisateur peut entrer une adresse de départ dans le champ "📍 Point de départ (optionnel)".

**Exemples d'adresses valides :**
- `15 Avenue des Champs-Élysées, Paris`
- `10 Rue de la Paix, 75002 Paris`
- `123 Boulevard Haussmann, Paris 8`

**Comportement :**
- Si l'adresse est vide → le TSP démarre automatiquement depuis le premier site optimal
- Si l'adresse est fournie → elle est géocodée puis utilisée comme point de départ obligatoire

### 2️⃣ **Rayon de recherche**

L'utilisateur peut sélectionner un rayon dans le menu déroulant "🌐 Rayon de recherche".

**Options disponibles :**
- Toute la zone sélectionnée (pas de filtre)
- Dans un rayon de 2 km
- Dans un rayon de 5 km
- Dans un rayon de 10 km
- Dans un rayon de 20 km
- Dans un rayon de 50 km

**Comportement :**
- Le filtre s'applique uniquement si un point de départ est fourni
- Seuls les sites situés à ≤ N km du point de départ sont inclus dans l'itinéraire
- La distance est calculée "à vol d'oiseau" (formule de Haversine)

---

## 🔧 Architecture technique

### Frontend (templates/index.html)

#### Champs HTML

```html
<!-- Point de départ -->
<div class="field">
    <label for="startAddress">📍 Point de départ (optionnel)</label>
    <input
        type="text"
        id="startAddress"
        placeholder="15 Avenue des Champs-Élysées, Paris..."
        autocomplete="off"
    >
</div>

<!-- Rayon de recherche -->
<div class="field">
    <label for="radiusSelect">🌐 Rayon de recherche</label>
    <select id="radiusSelect">
        <option value="">Toute la zone sélectionnée</option>
        <option value="2">Dans un rayon de 2 km</option>
        <option value="5">Dans un rayon de 5 km</option>
        <option value="10">Dans un rayon de 10 km</option>
        <option value="20">Dans un rayon de 20 km</option>
        <option value="50">Dans un rayon de 50 km</option>
    </select>
</div>
```

#### JavaScript : Géocodage du point de départ

```javascript
async function generateRoute() {
    const startAddressInput = document.getElementById('startAddress').value.trim();
    const radiusKm = document.getElementById('radiusSelect').value;

    let startPoint = null;

    // Géocoder le point de départ si fourni
    if (startAddressInput) {
        const geocodeResp = await fetch('/api/geocode', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ address: startAddressInput }),
        });

        const geocodeData = await geocodeResp.json();

        if (!geocodeResp.ok) {
            showToast('Impossible de géocoder l\'adresse de départ');
            return;
        }

        startPoint = {
            lat: geocodeData.latitude,
            lon: geocodeData.longitude,
            address: geocodeData.geocoded_label
        };
    }

    // Construire le body avec les paramètres
    const body = {
        city: selectedCity.name,
        dept: deptSelect.value,
        closed_loop: closedLoop,
        tsp_limit: tspLimit,
    };

    // Ajouter point de départ et rayon si définis
    if (startPoint) {
        body.start_lat = startPoint.lat;
        body.start_lon = startPoint.lon;
        body.start_address = startPoint.address;

        if (radiusKm) {
            body.radius_km = parseInt(radiusKm);
        }
    }

    // Appeler /api/generate
    const resp = await fetch('/api/generate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body),
    });
}
```

---

### Backend (app.py)

#### Endpoint : /api/geocode

Géocode une adresse fournie par l'utilisateur via l'API data.geopf.fr.

```python
@app.route("/api/geocode", methods=["POST"])
def api_geocode():
    """
    Géocode une adresse de départ fournie par l'utilisateur.
    Body JSON : {"address": "15 Avenue des Champs-Élysées, Paris"}
    """
    from pipeline.geocode import geocode_one

    body = request.get_json(force=True)
    address = (body.get("address") or "").strip()

    if not address:
        return jsonify({"error": "Adresse vide"}), 400

    # Extraire CP et ville si possible
    parts = address.split(",")
    postal_code = ""
    city = ""
    # ... (parsing logic)

    result = geocode_one(
        address_line=address,
        postal_code=postal_code,
        city=city,
        address_normalized=address
    )

    if not result["latitude"] or not result["longitude"]:
        return jsonify({"error": "Adresse introuvable"}), 404

    return jsonify({
        "geocoded_label": result["geocoded_label"],
        "latitude": result["latitude"],
        "longitude": result["longitude"],
        "score": result["score"],
    })
```

#### Fonction : haversine_distance()

Calcule la distance "à vol d'oiseau" entre deux coordonnées GPS.

```python
def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcule la distance en kilomètres entre deux points GPS (formule de Haversine).
    """
    R = 6371.0  # Rayon de la Terre en km

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c
```

#### Endpoint : /api/generate (modifié)

```python
@app.route("/api/generate", methods=["POST"])
def api_generate():
    body = request.get_json(force=True)

    # Nouveaux paramètres
    start_lat = body.get("start_lat")
    start_lon = body.get("start_lon")
    start_address = body.get("start_address", "")
    radius_km = body.get("radius_km")

    # ... (filtre ville + département)

    # ── Filtre par rayon autour du point de départ ──────────────────
    if start_lat is not None and start_lon is not None and radius_km is not None:
        df_routable["distance_from_start"] = df_routable.apply(
            lambda row: haversine_distance(
                start_lat, start_lon,
                row["latitude"], row["longitude"]
            ),
            axis=1
        )

        df_routable = df_routable[df_routable["distance_from_start"] <= radius_km]
        df_routable = df_routable.reset_index(drop=True)

    # ── Ajout du point de départ dans coords et df_routable ─────────
    coords = list(zip(df_routable["latitude"], df_routable["longitude"]))
    start_point_idx = None

    if start_lat is not None and start_lon is not None:
        # Vérifier si le point de départ est déjà un site existant
        is_existing = False
        for i, (lat, lon) in enumerate(coords):
            if abs(lat - start_lat) < 0.0001 and abs(lon - start_lon) < 0.0001:
                start_point_idx = i
                is_existing = True
                break

        if not is_existing:
            # Ajouter le point de départ au début
            coords.insert(0, (start_lat, start_lon))
            start_point_idx = 0

            # Créer une ligne fictive dans df_routable
            start_row = pd.DataFrame([{
                "site_id": "START_POINT",
                "geocoded_label": start_address or f"Point de départ ({start_lat:.4f}, {start_lon:.4f})",
                "latitude": start_lat,
                "longitude": start_lon,
                "nb_orthos": 0,
            }])
            df_routable = pd.concat([start_row, df_routable], ignore_index=True)

    # ── Calcul TSP avec start_index ─────────────────────────────────
    if start_point_idx is not None:
        route_order, total_duration = solve_tsp(
            matrix,
            open_path=open_path,
            time_limit=tsp_limit,
            start_index=start_point_idx
        )
    else:
        route_order, total_duration = solve_tsp(
            matrix,
            open_path=open_path,
            time_limit=tsp_limit
        )
```

---

### Pipeline (pipeline/routing.py)

#### Fonction : solve_tsp() (modifiée)

Ajout du paramètre `start_index` pour forcer le départ à un index spécifique.

```python
def solve_tsp(
    matrix: np.ndarray,
    open_path: bool = True,
    time_limit: int = 30,
    start_index: int | None = None,  # NOUVEAU
) -> tuple[list[int], float]:
    """
    Résout le TSP sur la matrice de durées.

    start_index : Force le départ à cet index (None = auto)
    """
    # ...

    if open_path:
        depot = n  # Dummy depot
    else:
        depot = start_index if start_index is not None else 0

    manager = pywrapcp.RoutingIndexManager(size, 1, depot)
    routing = pywrapcp.RoutingModel(manager)

    # ... (reste du code)
```

---

## 🎨 Affichage dans l'interface

### Point de départ sur la carte

Le point de départ est marqué avec :
- **Numéro** : ① (premier marqueur)
- **Couleur** : Vert (#27ae60)
- **Popup** :
  ```
  #1 – 15 Avenue des Champs-Élysées, 75008 Paris

  0 orthophoniste(s)
  ```
- **Tooltip** : `#1`

### Sites visités

Les sites suivants sont numérotés ②, ③, ④, etc., avec :
- **Couleur** : Bleu (#2980b9) pour les intermédiaires
- **Couleur** : Rouge (#c0392b) pour le dernier arrêt
- **Popup** : Adresse + noms des orthophonistes + contacts
- **Tooltip** : Noms des 3 premiers orthophonistes

---

## 📊 Cas d'usage

### Cas 1 : Visite autour de mon cabinet

**Contexte** : Je suis orthophoniste à Paris 8 et je veux visiter tous les confrères dans un rayon de 5 km.

**Actions** :
1. Rechercher "Paris" dans l'autocomplete
2. Entrer mon adresse : `10 Rue de la Boétie, 75008 Paris`
3. Sélectionner "Dans un rayon de 5 km"
4. Cliquer sur "Générer l'itinéraire"

**Résultat** :
- L'itinéraire commence à mon adresse
- Seuls les cabinets dans un rayon de 5 km sont visités
- Le chemin optimal est calculé pour minimiser le temps de trajet

### Cas 2 : Tournée depuis une gare

**Contexte** : J'arrive en train à Gare de Lyon et je veux visiter les orthophonistes de Paris 12.

**Actions** :
1. Rechercher "Paris" → Sélectionner "75012"
2. Entrer "Gare de Lyon, Paris" comme point de départ
3. Sélectionner "Dans un rayon de 10 km"
4. Générer l'itinéraire

**Résultat** :
- L'itinéraire commence à la gare
- Les orthophonistes de Paris 12 dans un rayon de 10 km sont visités
- Je peux voir le temps de trajet total et moyen

### Cas 3 : Toute une ville sans point de départ

**Contexte** : Je veux juste calculer l'itinéraire optimal pour visiter tous les orthophonistes de Marseille.

**Actions** :
1. Rechercher "Marseille"
2. Laisser "Point de départ" vide
3. Laisser "Rayon de recherche" sur "Toute la zone sélectionnée"
4. Générer l'itinéraire

**Résultat** :
- L'itinéraire commence au site optimal (calculé par OR-Tools)
- Tous les orthophonistes de Marseille sont visités
- Pas de filtre par rayon

---

## 🧪 Tests

### Test 1 : Point de départ valide

```bash
curl -X POST http://127.0.0.1:5000/api/geocode \
  -H "Content-Type: application/json" \
  -d '{"address": "15 Avenue des Champs-Élysées, Paris"}'
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

### Test 2 : Point de départ + rayon 5km

```bash
curl -X POST http://127.0.0.1:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "city": "Paris",
    "dept": "75008",
    "start_lat": 48.8698,
    "start_lon": 2.3078,
    "start_address": "15 Avenue des Champs-Élysées, 75008 Paris",
    "radius_km": 5,
    "closed_loop": false,
    "tsp_limit": 30
  }'
```

**Console (logs attendus) :**
```
[filtre] Rayon 5km autour de (48.8698, 2.3078)
[filtre] 38 sites dans le rayon
[route] Point de départ ajouté : 15 Avenue des Champs-Élysées, 75008 Paris
[route] Calcul matrice OSRM pour 39 points…
[route] Résolution TSP (limit=30s, open=True)…
```

### Test 3 : Adresse invalide

```bash
curl -X POST http://127.0.0.1:5000/api/geocode \
  -H "Content-Type: application/json" \
  -d '{"address": "xyzabc123"}'
```

**Réponse attendue :**
```json
{
  "error": "Adresse introuvable"
}
```

---

## 🎁 Améliorations futures

### 1. Isochrones

Afficher visuellement la zone de rayon autour du point de départ.

```python
folium.Circle(
    location=[start_lat, start_lon],
    radius=radius_km * 1000,  # mètres
    color='blue',
    fill=True,
    fillOpacity=0.2
).add_to(m)
```

### 2. Multi-départ

Permettre plusieurs points de départ pour diviser le territoire en zones.

### 3. Heure de départ

Prendre en compte le trafic en temps réel (OSRM supporte les profils temporels).

### 4. Export GPX

Exporter l'itinéraire au format GPX pour l'utiliser dans Waze/Google Maps.

---

## ✅ Résumé

Cette fonctionnalité permet de :
- ✅ Spécifier une adresse de départ personnalisée
- ✅ Filtrer les orthophonistes par rayon autour de cette adresse
- ✅ Calculer l'itinéraire optimal en partant de ce point
- ✅ Visualiser le point de départ sur la carte (marqueur vert)
- ✅ Gérer automatiquement les cas où l'adresse est déjà un cabinet d'ortho

**Bénéfices** :
- Gain de temps : démarrer depuis un lieu précis (domicile, gare, hôtel)
- Pertinence : se concentrer sur une zone géographique limitée
- Flexibilité : adapter l'itinéraire selon les contraintes de mobilité
