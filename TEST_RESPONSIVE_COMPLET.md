# Test Responsive Complet - Point de Départ & Rayon

## 🎯 Nouveaux éléments à tester

Avec l'ajout des fonctionnalités **Point de départ** et **Rayon de recherche**, il faut s'assurer que ces champs s'affichent correctement sur tous les écrans.

---

## 📐 Breakpoints et adaptations

### Desktop (> 1024px)

**Sidebar : 360px**

```
┌────────────────────────────────────┐
│ 📍 Point de départ (optionnel)     │
│ ┌──────────────────────────────┐   │
│ │ 15 Avenue des Champs-Élysées…│   │
│ └──────────────────────────────┘   │
│ Laissez vide pour partir du...    │
│                                    │
│ 🌐 Rayon de recherche              │
│ ┌──────────────────────────────┐   │
│ │ Dans un rayon de 10 km ▼    │   │
│ └──────────────────────────────┘   │
│ Active si un point de départ...   │
└────────────────────────────────────┘
```

**Styles appliqués :**
- Labels : 13px
- Input/Select : 14px, padding 8px 12px
- Texte d'aide : 11px
- Placeholder complet

---

### Tablette (769px - 1024px)

**Sidebar : 320px**

```
┌─────────────────────────────────┐
│ 📍 Point de départ             │
│ ┌───────────────────────────┐   │
│ │ 15 Avenue des Champs...   │   │
│ └───────────────────────────┘   │
│ Laissez vide pour...           │
│                                 │
│ 🌐 Rayon de recherche           │
│ ┌───────────────────────────┐   │
│ │ Dans un rayon de 10 km ▼ │   │
│ └───────────────────────────┘   │
│ Active si un point...          │
└─────────────────────────────────┘
```

**Styles appliqués :**
- Mêmes styles que desktop
- Largeur réduite mais lisible

---

### Mobile (≤ 768px)

**Layout vertical, sidebar en haut**

```
╔═══════════════════════════════════════╗
║ [☰] Ortho Route Planner              ║
╠═══════════════════════════════════════╣
║ FILTRE                                ║
║ ┌───────────────────────────────────┐ ║
║ │ Paris                              │ ║
║ └───────────────────────────────────┘ ║
║                                       ║
║ 📍 Point de départ                    ║
║ ┌───────────────────────────────────┐ ║
║ │ Ex: 15 Avenue des Champs-Élysées…│ ║
║ └───────────────────────────────────┘ ║
║ Laissez vide...                       ║
║                                       ║
║ 🌐 Rayon de recherche                 ║
║ ┌───────────────────────────────────┐ ║
║ │ Dans un rayon de 10 km        ▼  │ ║
║ └───────────────────────────────────┘ ║
║ Active si...                          ║
╠═══════════════════════════════════════╣
║              CARTE                    ║
╚═══════════════════════════════════════╝
```

**Styles appliqués (max-width: 768px) :**
- Labels : 12px
- Input/Select : 14px, padding 10px 12px
- Texte d'aide : 10px
- Placeholder raccourci : "Ex: 15 Avenue des Champs-Élysées..."
- Boutons : 44px min-height (tactile)

---

### Petit mobile (< 375px)

**iPhone SE, petits Android**

```
╔═══════════════════════════════╗
║ [☰] Ortho                     ║
╠═══════════════════════════════╣
║ FILTRE                        ║
║ ┌─────────────────────────┐   ║
║ │ Paris                    │   ║
║ └─────────────────────────┘   ║
║                               ║
║ 📍 Point de départ            ║
║ ┌─────────────────────────┐   ║
║ │ Ex: 15 Ave Champs-Élysées│  ║
║ └─────────────────────────┘   ║
║ Laissez vide...               ║
║                               ║
║ 🌐 Rayon                      ║
║ ┌─────────────────────────┐   ║
║ │ 10 km              ▼    │   ║
║ └─────────────────────────┘   ║
║ Active si...                  ║
╠═══════════════════════════════╣
║           CARTE               ║
╚═══════════════════════════════╝
```

**Styles appliqués (max-width: 374px) :**
- Labels : 11px
- Input/Select : 13px, padding 8px 10px
- Texte d'aide : 9px, line-height 1.3
- Placeholder très court : "Ex: 15 Ave Champs-Élysées..."
- Padding réduit partout

---

## ✅ Checklist de tests

### iPhone SE (320px × 568px)

- [ ] Champ "Point de départ" visible et cliquable
- [ ] Placeholder adapté : "Ex: 15 Ave Champs-Élysées..."
- [ ] Texte d'aide lisible (9px)
- [ ] Dropdown "Rayon" affiche toutes les options
- [ ] Menu hamburger fonctionne
- [ ] Sidebar scroll si contenu trop haut
- [ ] Clavier mobile ne cache pas le champ actif
- [ ] Boutons tactiles (44px+)

### iPhone 12/13 (390px × 844px)

- [ ] Champ "Point de départ" bien espacé
- [ ] Placeholder adapté : "Ex: 15 Avenue des Champs-Élysées..."
- [ ] Labels 12px lisibles
- [ ] Dropdown bien dimensionné
- [ ] Pas de débordement horizontal
- [ ] Sidebar ouverte = 60vh max

### iPad Mini (768px × 1024px)

- [ ] Sidebar visible par défaut (320px)
- [ ] Champs full-width dans la sidebar
- [ ] Labels 13px
- [ ] Placeholder complet visible
- [ ] Pas de menu hamburger (desktop layout)

### iPad Pro (1024px × 1366px)

- [ ] Sidebar 360px fixe
- [ ] Carte occupe le reste
- [ ] Layout horizontal
- [ ] Tous les textes à taille normale

### Desktop 1920×1080

- [ ] Sidebar 360px
- [ ] Carte large et confortable
- [ ] Placeholder complet : "15 Avenue des Champs-Élysées, Paris..."
- [ ] Textes bien espacés

---

## 🧪 Tests fonctionnels par appareil

### Test 1 : Mobile (iPhone)

1. Ouvrir http://127.0.0.1:5000 sur iPhone
2. Cliquer sur [☰] pour ouvrir la sidebar
3. Rechercher "Paris"
4. Entrer "15 Avenue des Champs-Élysées, Paris" dans Point de départ
5. Sélectionner "Dans un rayon de 5 km"
6. Cliquer "Générer l'itinéraire"

**Résultat attendu :**
- ✅ Sidebar se ferme automatiquement
- ✅ Carte affiche le marqueur vert au point de départ
- ✅ Seuls les sites dans 5km sont affichés
- ✅ Itinéraire commence au point de départ

### Test 2 : Tablette (iPad)

1. Ouvrir en mode portrait (768px)
2. Sidebar visible par défaut
3. Entrer une adresse longue
4. Observer si le texte ne déborde pas

**Résultat attendu :**
- ✅ Pas de scroll horizontal
- ✅ Texte tronqué avec ellipsis si nécessaire

### Test 3 : Rotation mobile

1. Ouvrir sur mobile en portrait
2. Ouvrir la sidebar
3. Tourner en paysage

**Résultat attendu :**
- ✅ Sidebar se ferme automatiquement (> 768px)
- ✅ Layout passe en horizontal

### Test 4 : Petit écran (320px)

1. DevTools Chrome → Responsive mode
2. Régler à 320px de large
3. Vérifier tous les champs

**Résultat attendu :**
- ✅ Stats en grille 1 colonne
- ✅ Placeholder court : "Ex: 15 Ave Champs-Élysées..."
- ✅ Labels 11px lisibles
- ✅ Texte d'aide 9px (compact mais lisible)

---

## 🎨 Règles CSS appliquées

### Mobile (≤ 768px)

```css
@media (max-width: 768px) {
    select, input[type="text"], input[type="number"] {
        font-size: 14px;
        padding: 10px 12px;
    }

    .field label {
        font-size: 12px;
    }

    .field small {
        font-size: 10px !important;
    }

    #startAddress::placeholder {
        font-size: 13px;
    }
}
```

### Petit mobile (< 375px)

```css
@media (max-width: 374px) {
    select, input[type="text"], input[type="number"] {
        font-size: 13px;
        padding: 8px 10px;
    }

    .field label {
        font-size: 11px;
    }

    .field small {
        font-size: 9px !important;
        line-height: 1.3;
    }

    #startAddress::placeholder {
        font-size: 12px;
    }
}
```

### JavaScript : Adaptation dynamique

```javascript
function updatePlaceholders() {
    const startAddressInput = document.getElementById('startAddress');
    const width = window.innerWidth;

    if (width <= 374) {
        startAddressInput.placeholder = "Ex: 15 Ave Champs-Élysées...";
        cityInput.placeholder = "Ville...";
    } else if (width <= 768) {
        startAddressInput.placeholder = "Ex: 15 Avenue des Champs-Élysées...";
        cityInput.placeholder = "Rechercher une ville...";
    } else {
        startAddressInput.placeholder = "15 Avenue des Champs-Élysées, Paris...";
        cityInput.placeholder = "Rechercher une ville...";
    }
}

window.addEventListener('resize', updatePlaceholders);
```

---

## 🚀 Commandes de test

### DevTools Chrome (Desktop)

```bash
1. F12 pour ouvrir DevTools
2. Ctrl+Shift+M pour activer le mode responsive
3. Tester ces tailles :
   - 320×568 (iPhone SE)
   - 375×667 (iPhone 8)
   - 390×844 (iPhone 12)
   - 414×896 (iPhone 11 Pro Max)
   - 768×1024 (iPad)
   - 1024×1366 (iPad Pro)
```

### Depuis un vrai smartphone

```bash
# 1. Trouver l'IP du Mac
ifconfig | grep "inet " | grep -v 127.0.0.1

# 2. Lancer le serveur
venv/bin/python app.py --host 0.0.0.0

# 3. Sur le téléphone
http://[IP]:5000
```

---

## 📊 Tableau récapitulatif

| Écran | Sidebar | Labels | Input | Placeholder | Texte aide | Layout |
|-------|---------|--------|-------|-------------|------------|--------|
| **> 1024px** | 360px fixe | 13px | 14px / 8-12px pad | Complet | 11px | Horizontal |
| **769-1024px** | 320px fixe | 13px | 14px / 8-12px pad | Complet | 11px | Horizontal |
| **≤ 768px** | 100% (top) | 12px | 14px / 10-12px pad | Moyen | 10px | Vertical |
| **< 375px** | 100% (top) | 11px | 13px / 8-10px pad | Court | 9px | Vertical |

---

## ✅ Résultat final

Les nouveaux champs **Point de départ** et **Rayon de recherche** sont maintenant :

- ✅ Responsifs sur tous les écrans (320px → 4K)
- ✅ Tactiles sur mobile (boutons 44px+)
- ✅ Placeholders adaptés dynamiquement
- ✅ Textes lisibles même sur petits écrans (9px min)
- ✅ Intégrés au layout existant (sidebar vertical/horizontal)
- ✅ Testables sur tous les appareils

**Pas de débordement, pas de scroll horizontal, expérience fluide partout !**
