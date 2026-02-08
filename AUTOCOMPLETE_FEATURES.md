# Fonctionnalités de l'autocomplete

## ✨ Ce qui a été ajouté

Le sélecteur de ville fixe a été remplacé par un **champ de recherche avec autocomplete** qui filtre dynamiquement les 6060 villes.

---

## 🎮 Utilisation

### 1️⃣ **Recherche par texte**
```
Tape "par" → affiche PARIS, PARON, PARIGNE, etc.
Tape "mars" → affiche MARSEILLE, MARSAC, MARSAT, etc.
```

### 2️⃣ **Navigation au clavier**
- **↓** (flèche bas) : descendre dans la liste
- **↑** (flèche haut) : remonter dans la liste
- **Enter** : sélectionner la ville surlignée
- **Escape** : fermer le dropdown

### 3️⃣ **Sélection à la souris**
- Clique sur une ville dans le dropdown pour la sélectionner

### 4️⃣ **Focus automatique**
- Clique dans le champ → le dropdown s'affiche avec les résultats filtrés

### 5️⃣ **Fermeture automatique**
- Clique en dehors du champ → le dropdown se ferme

---

## 🎨 Design

### Couleurs selon l'état :
- **Item normal** : fond gris foncé (`var(--surface-2)`)
- **Item au survol** : fond gris moyen (`var(--surface)`)
- **Item sélectionné (clavier)** : fond accent violet (`var(--accent)`)

### Affichage des résultats :
```
PARIS
455 orthophonistes · 728 sites

MARSEILLE
536 orthophonistes · 455 sites
```

### Limite :
- Maximum **50 résultats** affichés à la fois (performance)
- Si aucun résultat : "Aucune ville trouvée"

---

## 🔧 Implémentation technique

### HTML
```html
<div class="autocomplete">
    <input type="text" id="cityInput" class="autocomplete-input"
           placeholder="Rechercher une ville..." autocomplete="off">
    <div id="cityDropdown" class="autocomplete-dropdown"></div>
</div>
```

### JavaScript
```javascript
// Filtrage
function filterCities(query) {
    return citiesData.filter(c =>
        c.name.toUpperCase().includes(query.toUpperCase())
    ).slice(0, 50);
}

// Rendu dynamique du dropdown
function renderDropdown(filtered) {
    cityDropdown.innerHTML = filtered.map((c, i) => `
        <div class="autocomplete-item">
            <div class="city-name">${c.name}</div>
            <div class="city-stats">${c.orthos} orthos · ${c.sites} sites</div>
        </div>
    `).join('');
}

// Événements
cityInput.addEventListener('input', (e) => {
    const filtered = filterCities(e.target.value);
    renderDropdown(filtered);
});
```

### CSS
```css
.autocomplete-dropdown {
    position: absolute;
    max-height: 300px;
    overflow-y: auto;
    z-index: 100;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.autocomplete-item:hover {
    background: var(--surface);
}

.autocomplete-item.selected {
    background: var(--accent);
}
```

---

## 📊 Avantages vs select classique

| Critère | `<select>` ancien | Autocomplete nouveau |
|---------|-------------------|---------------------|
| **Recherche** | ❌ Pas de recherche | ✅ Recherche instantanée |
| **Performance** | ⚠️ Lag avec 6060 items | ✅ Fluide (50 max affichés) |
| **UX** | ⚠️ Scroll infini | ✅ Filtrage intelligent |
| **Accessibilité** | ✅ Native | ✅ Clavier + souris |
| **Mobile** | ⚠️ Select natif | ✅ Responsive |

---

## 🚀 Exemples d'utilisation

### Recherche rapide
```
1. Tape "ly" dans le champ
2. LYON apparaît en premier (372 orthos)
3. Appuie sur Enter
4. Sélectionne un arrondissement si besoin
5. Clique "Générer l'itinéraire"
```

### Navigation clavier
```
1. Tape "par"
2. Appuie sur ↓ deux fois
3. Surligne PARON
4. Appuie sur Enter
5. Ville sélectionnée !
```

### Correction de faute
```
Tape "marseil" → MARSEILLE apparaît quand même
Tape "pris" → rien
Corrige en "paris" → PARIS apparaît
```

---

## 🐛 Gestion des cas limites

### Aucun résultat
```
Tape "zzzzz" → affiche "Aucune ville trouvée"
```

### Ville déjà sélectionnée
```
Clique dans le champ → dropdown affiche les résultats filtrés
Change le texte → sélection précédente annulée
```

### Génération sans sélection
```
Efface le texte → selectedCity = null
Clique "Générer" → toast "Veuillez sélectionner une ville"
```

---

## 🎯 Prochaines améliorations possibles

1. **Recherche fuzzy** : "pris" → "PARIS"
2. **Tri par pertinence** : afficher les villes avec le plus d'orthos d'abord
3. **Highlights** : surligner le texte de recherche dans les résultats
4. **Historique** : mémoriser les dernières villes consultées
5. **Raccourcis** : Ctrl+K pour focus rapide sur le champ
