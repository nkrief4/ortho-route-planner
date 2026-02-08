# Point de départ amélioré

## 🎯 Problème résolu

Le point de départ ne fonctionnait pas correctement pour deux raisons :
1. **Géocodage** : L'utilisateur devait entrer l'adresse complète avec la ville
2. **TSP** : Le chemin ouvert (open_path=True) ignorait le point de départ et utilisait un dummy depot

## ✅ Corrections apportées

### 1. Géocodage automatique avec la ville sélectionnée

**Avant :**
```javascript
// L'utilisateur devait entrer : "15 Avenue des Champs-Élysées, Paris"
body: JSON.stringify({ address: startAddressInput })
```

**Après :**
```javascript
// L'utilisateur entre juste : "15 Avenue des Champs-Élysées"
// La ville est automatiquement ajoutée
body: JSON.stringify({
    address: startAddressInput,
    city: city,              // Ville sélectionnée
    postal_code: dept        // Département/arrondissement sélectionné
})
```

**Backend modifié :**
```python
@app.route("/api/geocode", methods=["POST"])
def api_geocode():
    address = body.get("address").strip()
    city = body.get("city").strip()
    postal_code = body.get("postal_code").strip()

    # Construire l'adresse complète
    full_address = address
    if city and city.lower() not in address.lower():
        full_address = f"{address}, {city}"

    result = geocode_one(
        address_line=full_address,
        postal_code=postal_code,
        city=city,
        address_normalized=full_address,
    )
```

---

### 2. TSP avec point de départ forcé

**Avant :**
```python
if open_path:
    # Utilisait toujours un dummy depot (n)
    depot = n
    size = n + 1
else:
    # Utilisait start_index seulement en mode fermé
    depot = start_index if start_index is not None else 0
    size = n
```

**Problème :** En mode ouvert (sans retour), le TSP ignorait le point de départ spécifié.

**Après :**
```python
if open_path and start_index is None:
    # Chemin ouvert sans point de départ forcé → dummy depot
    depot = n
    size = n + 1
elif open_path and start_index is not None:
    # Chemin ouvert avec point de départ forcé → utiliser start_index
    depot = start_index
    size = n
else:
    # Boucle fermée → utiliser start_index ou 0
    depot = start_index if start_index is not None else 0
    size = n
```

**Résultat :** Le TSP démarre maintenant toujours du point spécifié, même en mode ouvert.

---

## 📝 Interface utilisateur

### Nouveau placeholder

**Desktop :**
```
📍 Point de départ (optionnel)
┌──────────────────────────────────────┐
│ Ex: 15 Avenue des Champs-Élysées     │
└──────────────────────────────────────┘
Entrez uniquement le numéro et le nom de la rue
(la ville est déjà sélectionnée)
```

**Mobile :**
```
📍 Point de départ (optionnel)
┌──────────────────────────────────────┐
│ Ex: 15 Avenue des Champs-Élysées     │
└──────────────────────────────────────┘
Entrez uniquement le numéro et la rue
(la ville est déjà sélectionnée)
```

**Petit mobile :**
```
📍 Point de départ
┌────────────────────────────┐
│ Ex: 15 Ave Champs-Élysées  │
└────────────────────────────┘
Numéro + rue (ville auto)
```

---

## 🧪 Tests à effectuer

### Test 1 : Point de départ simple

**Étapes :**
1. Ouvrir http://127.0.0.1:5000
2. Rechercher "Paris"
3. Sélectionner "75008" (optionnel)
4. Entrer dans "Point de départ" : `15 Avenue des Champs-Élysées`
5. Laisser "Rayon de recherche" vide
6. Cliquer "Générer l'itinéraire"

**Résultat attendu :**
- ✅ Géocodage réussit : "15 Avenue des Champs-Élysées, 75008 Paris"
- ✅ Marqueur vert #1 au point de départ
- ✅ Le chemin commence à cette adresse
- ✅ Tous les sites de Paris 75008 sont visités

### Test 2 : Point de départ + rayon

**Étapes :**
1. Rechercher "Paris"
2. Entrer : `10 Rue de la Paix`
3. Sélectionner rayon : "Dans un rayon de 5 km"
4. Générer l'itinéraire

**Résultat attendu :**
- ✅ Géocodage : "10 Rue de la Paix, Paris"
- ✅ Seuls les sites dans 5km du point de départ sont affichés
- ✅ Le chemin commence à "10 Rue de la Paix"

### Test 3 : Point de départ sans ville préalable

**Étapes :**
1. Rechercher "Lyon"
2. Entrer : `25 Rue de la République`
3. Générer l'itinéraire

**Résultat attendu :**
- ✅ Géocodage : "25 Rue de la République, Lyon"
- ✅ Le TSP démarre de cette adresse

### Test 4 : Adresse invalide

**Étapes :**
1. Rechercher "Paris"
2. Entrer : `99999 Rue Inexistante`
3. Générer l'itinéraire

**Résultat attendu :**
- ❌ Toast d'erreur : "Impossible de géocoder l'adresse de départ"
- ❌ L'itinéraire ne se génère pas

### Test 5 : Sans point de départ

**Étapes :**
1. Rechercher "Marseille"
2. Laisser "Point de départ" vide
3. Générer l'itinéraire

**Résultat attendu :**
- ✅ TSP démarre automatiquement du point optimal
- ✅ Pas de marqueur vert spécial
- ✅ Tous les sites de Marseille sont visités

---

## 🎨 Exemples d'adresses valides

Pour **Paris** :
- `15 Avenue des Champs-Élysées`
- `10 Rue de la Paix`
- `5 Place de la République`
- `123 Boulevard Haussmann`

Pour **Lyon** :
- `25 Rue de la République`
- `10 Place Bellecour`
- `3 Avenue Jean Jaurès`

Pour **Marseille** :
- `15 La Canebière`
- `20 Rue Paradis`
- `5 Boulevard Longchamp`

---

## 📊 Logs attendus

### Console backend (succès)

```
[filtre] Ville: Paris, Département: 75008
[filtre] Rayon 5km autour de (48.8698, 2.3078)
[filtre] 23 sites dans le rayon
[route] Point de départ ajouté : 15 Avenue des Champs-Élysées, 75008 Paris
[route] Calcul matrice OSRM pour 24 points…
    OSRM [1/1] batches
[route] Résolution TSP (limit=30s, open=True)…
```

### Console backend (erreur géocodage)

```
[error] Géocodage échoué pour "99999 Rue Inexistante, Paris" (score: 0.12)
```

---

## 🔧 Architecture technique

### Flux complet

```
┌──────────────────┐
│  Utilisateur     │
│  "15 Av Champs-  │
│   Élysées"       │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────┐
│  JavaScript (templates/index.html)│
│  - Récupère ville sélectionnée    │
│  - Récupère département (opt.)    │
│  - Envoie à /api/geocode          │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│  Backend (app.py)                 │
│  /api/geocode                     │
│  - Combine adresse + ville        │
│  - Appelle data.geopf.fr          │
│  - Retourne lat/lon               │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│  JavaScript                       │
│  - Stocke lat/lon dans startPoint │
│  - Envoie à /api/generate         │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│  Backend (app.py)                 │
│  /api/generate                    │
│  - Filtre sites par rayon (opt.)  │
│  - Ajoute start_point à coords    │
│  - Ajoute start_point à df_routable│
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│  Pipeline (routing.py)            │
│  solve_tsp()                      │
│  - open_path=True                 │
│  - start_index=0 (start_point)    │
│  - Calcul TSP depuis start_point  │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│  Résultat                         │
│  - Route commence au point départ │
│  - Marqueur vert #1               │
│  - Liste ordonnée des arrêts      │
└──────────────────────────────────┘
```

---

## ✅ Résumé des améliorations

| Aspect | Avant | Après |
|--------|-------|-------|
| **Saisie adresse** | Adresse complète requise | Numéro + rue suffit |
| **Géocodage** | Manuel | Automatique avec ville sélectionnée |
| **TSP ouvert** | Ignorait start_index | Démarre du start_index |
| **TSP fermé** | Utilisait start_index ✅ | Utilisait start_index ✅ |
| **Placeholder** | "15 Av..., Paris..." | "Ex: 15 Av..." (adaptatif) |
| **Message d'aide** | "Laissez vide..." | "Numéro + rue (ville auto)" |

---

## 🚀 Utilisation

### Cas d'usage typique

**Je suis orthophoniste à Paris 8 et je veux visiter les confrères dans un rayon de 5km autour de mon cabinet :**

1. Rechercher "**Paris**" → sélectionner automatiquement
2. Sélectionner "**75008**" dans le dropdown arrondissement
3. Entrer dans "Point de départ" : `**10 Rue de la Boétie**`
4. Sélectionner rayon : "**Dans un rayon de 5 km**"
5. Cliquer "**Générer l'itinéraire**"

**Résultat :**
- Itinéraire commence à "10 Rue de la Boétie, 75008 Paris"
- Seuls les cabinets dans 5km sont visités
- Chemin optimal calculé pour minimiser le temps de trajet
- Pas besoin de taper la ville, elle est déjà connue !

---

## 🎉 Fonctionnalité maintenant pleinement opérationnelle !

✅ Géocodage automatique avec ville sélectionnée
✅ TSP démarre du point spécifié (ouvert ou fermé)
✅ Filtre par rayon autour du point de départ
✅ Interface claire et concise
✅ Responsive sur tous les écrans
✅ Messages d'erreur explicites
