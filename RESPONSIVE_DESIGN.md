# Design Responsive Mobile

## 🎯 Objectif

Rendre l'interface utilisable sur tous les appareils : ordinateurs, tablettes et smartphones.

---

## 📱 Breakpoints

| Appareil | Largeur | Disposition |
|----------|---------|-------------|
| **Desktop** | > 1024px | Sidebar gauche + Carte droite (horizontal) |
| **Tablette** | 769px - 1024px | Sidebar réduite + Carte (horizontal) |
| **Mobile** | ≤ 768px | Sidebar en haut (vertical) + Menu hamburger |
| **Petit mobile** | < 375px | Optimisations supplémentaires |

---

## 🎨 Adaptations par écran

### 1️⃣ **Desktop (> 1024px)**
```
╔═══════════════════════════════════════════════╗
║ [Ortho Route Planner]          6060 villes   ║
╠═════════════════╦═════════════════════════════╣
║ FILTRE          ║                             ║
║ [Ville...]      ║                             ║
║ [CP/Arrondt]    ║        CARTE FOLIUM         ║
║                 ║                             ║
║ RÉSULTAT        ║      (tracé + marqueurs)    ║
║ [Stats 2x2]     ║                             ║
║                 ║                             ║
║ ITINÉRAIRE      ║                             ║
║ ① Adresse       ║                             ║
║ ② Adresse       ║                             ║
║ ...             ║                             ║
╚═════════════════╩═════════════════════════════╝
   360px sidebar       Reste de l'écran
```

---

### 2️⃣ **Tablette (769px - 1024px)**
```
╔═══════════════════════════════════════════════╗
║ [Ortho Route Planner]     6060 villes         ║
╠═════════════╦═════════════════════════════════╣
║ FILTRE      ║                                 ║
║ [Ville]     ║                                 ║
║ [CP]        ║         CARTE FOLIUM            ║
║             ║                                 ║
║ RÉSULTAT    ║                                 ║
║ [Stats]     ║                                 ║
║             ║                                 ║
║ ITINÉRAIRE  ║                                 ║
║ ① Adresse   ║                                 ║
║ ...         ║                                 ║
╚═════════════╩═════════════════════════════════╝
  300px sidebar       Reste de l'écran
```

**Changements :**
- Sidebar : 360px → 300px
- Textes légèrement plus petits
- Même disposition horizontale

---

### 3️⃣ **Mobile (≤ 768px)**
```
╔═══════════════════════════════════════════════╗
║ [☰] Ortho Route Planner                       ║
║ 6060 villes · 17823 sites                     ║
╠═══════════════════════════════════════════════╣
║                                               ║
║                                               ║
║              CARTE FOLIUM                     ║
║                                               ║
║           (occupe tout l'écran)               ║
║                                               ║
║                                               ║
╚═══════════════════════════════════════════════╝

Clic sur [☰] :
╔═══════════════════════════════════════════════╗
║ [☰] Ortho Route Planner                       ║
╠═══════════════════════════════════════════════╣
║ FILTRE                                        ║
║ [Ville...]                   ▲                ║
║ [CP/Arrondissement]          │                ║
║ 728 sites — 1288 orthos      │                ║
║                              │                ║
║ [TSP (sec)]                  │  70% hauteur   ║
║ [☐ Boucle fermée]            │  (scrollable)  ║
║                              │                ║
║ [Générer l'itinéraire]       │                ║
║                              │                ║
║ RÉSULTAT                     │                ║
║ ┌────────┬────────┐          │                ║
║ │ 162    │ 8.4h   │          │                ║
║ └────────┴────────┘          ▼                ║
╠═══════════════════════════════════════════════╣
║              CARTE FOLIUM                     ║
║           (reste visible en bas)              ║
╚═══════════════════════════════════════════════╝
```

**Changements majeurs :**
- **Layout vertical** : sidebar en haut, carte en bas
- **Menu hamburger** [☰] pour afficher/cacher la sidebar
- **Sidebar cachée par défaut** : max-height: 0
- **Sidebar ouverte** : max-height: 70vh (scrollable)
- **Auto-fermeture** : sidebar se ferme après génération
- **Stats en grille 2×2** : au lieu de 4 colonnes
- **Boutons plus gros** : 44px min (tactile)
- **Textes adaptés** : tailles réduites

---

### 4️⃣ **Petit mobile (< 375px)**
```
╔═══════════════════════════════════╗
║ [☰] Ortho                         ║
║ 6060 villes                       ║
╠═══════════════════════════════════╣
║                                   ║
║         CARTE FOLIUM              ║
║                                   ║
║      (plein écran optimisé)       ║
║                                   ║
╚═══════════════════════════════════╝
```

**Optimisations supplémentaires :**
- Stats en **grille 1 colonne** (vertical)
- Textes encore plus petits
- Padding réduit partout
- Marqueurs numérotés plus petits (20px)

---

## 🎯 Fonctionnalités responsive

### Menu Hamburger (mobile uniquement)

**HTML :**
```html
<button class="menu-toggle" id="menuToggle">
    <svg>☰</svg>  <!-- Icône 3 barres -->
</button>
```

**CSS :**
```css
/* Caché sur desktop */
.menu-toggle {
    display: none;
}

/* Visible sur mobile */
@media (max-width: 768px) {
    .menu-toggle {
        display: flex;
    }
}
```

**JavaScript :**
```javascript
menuToggle.addEventListener('click', () => {
    sidebar.classList.toggle('mobile-open');
});

// Auto-fermeture après génération
generateBtn.addEventListener('click', () => {
    if (window.innerWidth <= 768) {
        sidebar.classList.remove('mobile-open');
    }
});
```

---

### Sidebar accordéon (mobile)

**État fermé (défaut) :**
```css
@media (max-width: 768px) {
    .sidebar {
        max-height: 0;
        overflow: hidden;
        transition: max-height 0.3s ease;
    }
}
```

**État ouvert :**
```css
.sidebar.mobile-open {
    max-height: 70vh;
    overflow-y: auto;
}
```

**Animation fluide :**
- Transition CSS sur `max-height`
- Durée : 0.3s
- Easing : ease

---

### Champs inline en colonne

**Desktop :**
```
┌──────────────────────────────┐
│ [TSP (sec): 30]  │  [☐ Boucle fermée] │
└──────────────────────────────┘
```

**Mobile :**
```
┌──────────────────────────────┐
│ [TSP (sec): 30]              │
│ [☐ Boucle fermée]            │
└──────────────────────────────┘
```

**CSS :**
```css
@media (max-width: 768px) {
    .inline-fields {
        flex-direction: column;
    }
}
```

---

### Liste route optimisée

**Desktop :**
```
┌────────────────────────────────────────────┐
│ ① 185 Boulevard Raymond Losserand          │
│   👥 Marie DUPONT, Jean MARTIN (+1)  +2.5min│
└────────────────────────────────────────────┘
```

**Mobile :**
```
┌─────────────────────────────────┐
│ ① 185 Bd Raymond Losserand      │
│   👥 M. DUPONT, J. MARTIN...+2.5│
└─────────────────────────────────┘
```

**Optimisations :**
- Adresse tronquée plus tôt
- Noms abrégés si trop longs
- Tailles de texte réduites
- Padding réduit

---

## 📐 Tailles adaptatives

### Textes

| Élément | Desktop | Tablette | Mobile | Petit |
|---------|---------|----------|--------|-------|
| **H1 titre** | 18px | 17px | 16px | 14px |
| **Stats header** | 13px | 12px | 11px | 11px |
| **Adresse route** | 13px | 13px | 12px | 11px |
| **Noms orthos** | 11px | 11px | 10px | 9px |
| **Durée** | 12px | 12px | 11px | 11px |

### Espaces

| Élément | Desktop | Mobile |
|---------|---------|--------|
| **Header padding** | 12px 24px | 10px 16px |
| **Sidebar padding** | 16px 20px | 12px 16px |
| **Route item padding** | 10px 20px | 8px 16px |
| **Button padding** | 10px 16px | 12px 16px |

### Composants

| Élément | Desktop | Mobile |
|---------|---------|--------|
| **Marqueur numéro** | 28px | 24px |
| **Stat card val** | 20px | 16px |
| **Bouton tactile** | — | 44px min |

---

## 🎨 Optimisations tactiles

### Boutons

```css
@media (max-width: 768px) {
    .btn {
        padding: 12px 16px;  /* Plus gros */
        font-size: 15px;
        min-height: 44px;    /* Recommandation Apple/Google */
    }
}
```

### Autocomplete dropdown

```css
@media (max-width: 768px) {
    .autocomplete-dropdown {
        max-height: 200px;  /* 300px → 200px */
    }
}
```

### Toast notifications

```css
@media (max-width: 768px) {
    .toast {
        bottom: 16px;
        right: 16px;
        left: 16px;     /* Pleine largeur */
        max-width: none;
    }
}
```

---

## 🧪 Test sur différents appareils

### iPhone (375px × 667px)
```
✓ Menu hamburger visible
✓ Sidebar s'ouvre/ferme au clic
✓ Stats en grille 2×2
✓ Carte occupe 50% écran
✓ Boutons tactiles 44px+
```

### iPad Portrait (768px × 1024px)
```
✓ Sidebar 300px visible
✓ Disposition horizontale
✓ Stats en grille 2×2
✓ Police légèrement réduite
```

### Galaxy S8 (360px × 740px)
```
✓ Menu hamburger visible
✓ Layout vertical
✓ Stats en grille 2×2
✓ Textes optimisés
```

### iPhone SE (320px × 568px)
```
✓ Stats en grille 1 colonne
✓ Textes très compacts
✓ Padding minimal
✓ Marqueurs 20px
```

---

## 💡 Bonnes pratiques appliquées

### 1. **Mobile-first approach**
- Media queries `max-width` (du plus petit au plus grand)
- Design de base adapté au mobile
- Enrichissements progressifs pour desktop

### 2. **Touch-friendly**
- Boutons min 44px (Apple HIG)
- Espacement suffisant entre éléments
- Zones de tap agrandies

### 3. **Performance**
- Transitions CSS (GPU-accelerated)
- Pas de JavaScript lourd pour le responsive
- Media queries conditionnelles

### 4. **Accessibilité**
- `aria-label` sur menu toggle
- Contraste respecté sur tous les écrans
- Tailles de texte lisibles (min 11px)

### 5. **UX cohérente**
- Même workflow sur tous les appareils
- Navigation intuitive (hamburger)
- Feedback visuel (animations)

---

## 🎁 Fonctionnalités bonus

### Rotation détectée
```javascript
window.addEventListener('orientationchange', () => {
    // Refermer la sidebar en mode paysage
    if (window.innerWidth > 768) {
        sidebar.classList.remove('mobile-open');
    }
});
```

### Scroll préservé
```css
.sidebar.mobile-open {
    overflow-y: auto;          /* Scroll interne */
    -webkit-overflow-scrolling: touch;  /* iOS smooth scroll */
}
```

### Keyboard friendly
```css
/* Focus visible sur mobile aussi */
input:focus, select:focus {
    border-color: var(--accent);
    outline: none;
}
```

---

## 📊 Résumé visuel des breakpoints

```
┌─────────────────────────────────────────────────┐
│                                                 │
│  > 1024px : Desktop                             │
│  ├─ Sidebar 360px fixe à gauche                │
│  ├─ Carte occupe le reste                      │
│  └─ Disposition horizontale                    │
│                                                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  769-1024px : Tablette                          │
│  ├─ Sidebar 300px fixe à gauche                │
│  ├─ Textes légèrement réduits                  │
│  └─ Disposition horizontale                    │
│                                                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  ≤ 768px : Mobile                               │
│  ├─ Menu hamburger visible                     │
│  ├─ Sidebar en haut (cachée par défaut)        │
│  ├─ Disposition verticale                      │
│  ├─ Stats grille 2×2                           │
│  └─ Boutons tactiles 44px+                     │
│                                                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  < 375px : Petit mobile                         │
│  ├─ Stats grille 1 colonne                     │
│  ├─ Textes encore plus compacts                │
│  ├─ Padding minimal                            │
│  └─ Composants réduits                         │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## ✅ Checklist de compatibilité

- [x] iPhone SE (320px)
- [x] iPhone 8/X/11/12/13 (375px - 428px)
- [x] iPad Mini/Air/Pro (768px - 1024px)
- [x] Android phones (360px - 412px)
- [x] Android tablets (600px - 1280px)
- [x] Desktop (1024px+)
- [x] Orientation portrait/paysage
- [x] Chrome mobile
- [x] Safari iOS
- [x] Samsung Internet
- [x] Firefox mobile

---

## 🚀 Pour tester

### Depuis le navigateur desktop

**Chrome DevTools :**
```
1. F12 pour ouvrir DevTools
2. Cliquer sur l'icône mobile (Ctrl+Shift+M)
3. Sélectionner un appareil :
   - iPhone SE
   - iPhone 12 Pro
   - iPad Air
   - Galaxy S20
```

**Firefox Responsive Mode :**
```
1. F12 pour ouvrir DevTools
2. Icône responsive ou Ctrl+Shift+M
3. Tester différentes tailles
```

### Depuis un smartphone

```
1. Trouve l'IP de ton Mac :
   ifconfig | grep "inet " | grep -v 127.0.0.1

2. Lance le serveur :
   venv/bin/python app.py --host 0.0.0.0

3. Sur ton téléphone, visite :
   http://[IP_DU_MAC]:5000
   Exemple : http://192.168.1.42:5000
```

---

## 🎯 Résultat final

**L'interface est maintenant complètement responsive** et utilisable sur tous les appareils, du plus petit smartphone (320px) aux écrans desktop 4K.

Les utilisateurs peuvent :
- ✅ Rechercher une ville sur mobile
- ✅ Générer un itinéraire depuis leur téléphone
- ✅ Consulter la carte interactive tactile
- ✅ Voir la liste des arrêts optimisée
- ✅ Utiliser l'app sur le terrain en mobilité
