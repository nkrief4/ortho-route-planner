# 🚀 Guide de Déploiement sur Render

## ✅ Fichiers créés

Les fichiers suivants ont été créés automatiquement :
- ✅ `requirements.txt` - Dépendances Python
- ✅ `render.yaml` - Configuration Render
- ✅ `.gitignore` - Mis à jour pour inclure les données nécessaires

## 📋 ÉTAPE 1 : Préparer GitHub

### 1.1 Créer un compte GitHub
1. Allez sur [github.com](https://github.com)
2. Cliquez sur "Sign up"
3. Créez votre compte (gratuit)

### 1.2 Créer un nouveau repository
1. Une fois connecté, cliquez sur le bouton **"+"** en haut à droite
2. Sélectionnez **"New repository"**
3. Remplissez :
   - **Repository name** : `ortho-route-planner` (ou un nom de votre choix)
   - **Description** : `Application de calcul d'itinéraires pour orthophonistes`
   - Cochez **Private** si vous voulez que ce soit privé (recommandé)
   - ⚠️ **NE PAS** cocher "Add a README file"
   - ⚠️ **NE PAS** ajouter de .gitignore (on a déjà le nôtre)
4. Cliquez sur **"Create repository"**

### 1.3 Initialiser Git localement
Ouvrez un terminal dans le dossier du projet et exécutez :

```bash
# Se placer dans le dossier du projet
cd /Users/nathankrief/Desktop/get_ortho

# Initialiser git (si pas déjà fait)
git init

# Ajouter tous les fichiers
git add .

# Créer le premier commit
git commit -m "Initial commit - Ortho Route Planner"

# Ajouter l'URL de votre repo GitHub
# ⚠️ REMPLACEZ "VOTRE_USERNAME" par votre nom d'utilisateur GitHub
git remote add origin https://github.com/VOTRE_USERNAME/ortho-route-planner.git

# Pousser le code sur GitHub
git branch -M main
git push -u origin main
```

**⚠️ Important** : GitHub va vous demander de vous authentifier. Utilisez votre nom d'utilisateur et un **Personal Access Token** (pas votre mot de passe).

#### Comment créer un Personal Access Token :
1. Sur GitHub, cliquez sur votre avatar en haut à droite
2. **Settings** → **Developer settings** (en bas à gauche)
3. **Personal access tokens** → **Tokens (classic)**
4. **Generate new token** → **Generate new token (classic)**
5. Donnez un nom : `Render Deploy`
6. Cochez la case **repo** (full control of private repositories)
7. Cliquez sur **Generate token**
8. **COPIEZ LE TOKEN** (vous ne le reverrez plus jamais !)
9. Utilisez ce token comme mot de passe quand Git vous le demande

---

## 🎨 ÉTAPE 2 : Créer un compte Render

1. Allez sur [render.com](https://render.com)
2. Cliquez sur **"Get Started"**
3. Inscrivez-vous avec **GitHub** (c'est plus simple)
4. Autorisez Render à accéder à votre GitHub

---

## 🔗 ÉTAPE 3 : Déployer l'application

### 3.1 Créer un nouveau Web Service
1. Sur le dashboard Render, cliquez sur **"New +"**
2. Sélectionnez **"Web Service"**
3. Connectez votre repository GitHub :
   - Si vous ne voyez pas votre repo, cliquez sur **"Configure account"**
   - Donnez accès à votre repository `ortho-route-planner`
4. Sélectionnez votre repository dans la liste

### 3.2 Configurer le service
Remplissez les informations suivantes :

| Champ | Valeur |
|-------|--------|
| **Name** | `ortho-route-planner` (ou un nom unique) |
| **Region** | `Frankfurt (EU Central)` (plus proche de vous) |
| **Branch** | `main` |
| **Root Directory** | (laisser vide) |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 app:app` |

### 3.3 Choisir le plan
- Sélectionnez **"Free"** (gratuit)
- Cliquez sur **"Create Web Service"**

---

## ⏳ ÉTAPE 4 : Attendre le déploiement

1. Render va commencer à construire votre application
2. Vous verrez les logs en temps réel
3. Le processus prend environ **5-10 minutes**
4. Une fois terminé, vous verrez **"Your service is live 🎉"**

---

## 🎉 ÉTAPE 5 : Accéder à votre application

1. En haut de la page, vous verrez une URL comme :
   ```
   https://ortho-route-planner.onrender.com
   ```
2. Cliquez dessus pour ouvrir votre application !
3. **Ajoutez cette URL en favori sur votre téléphone** 📱

---

## ⚠️ Points importants

### ⏰ Cold Starts
- Le plan gratuit met l'app en veille après 15 minutes d'inactivité
- La première visite après une période d'inactivité prendra **30-60 secondes** à charger
- Les visites suivantes seront instantanées

### 🔄 Mises à jour
Pour mettre à jour l'application après avoir fait des modifications :

```bash
# Dans le dossier du projet
git add .
git commit -m "Description des modifications"
git push
```

Render détectera automatiquement le push et redéploiera l'application !

---

## 🆘 Dépannage

### Erreur de déploiement ?
1. Vérifiez les logs dans Render (onglet "Logs")
2. Vérifiez que tous les fichiers sont bien sur GitHub
3. Vérifiez que `data/enriched/contacts_orthophonistes_basic.csv` est présent

### L'application ne répond pas ?
1. Attendez 60 secondes (cold start)
2. Rechargez la page
3. Vérifiez les logs dans Render

### Erreur "File not found" ?
Vérifiez que les fichiers de données sont bien sur GitHub :
```bash
git add data/enriched/contacts_orthophonistes_basic.csv
git add output/cache/geocode_cache.json
git commit -m "Add data files"
git push
```

---

## 📱 Utilisation sur mobile

1. Ouvrez Safari ou Chrome sur votre téléphone
2. Allez sur votre URL Render
3. Ajoutez la page à l'écran d'accueil :
   - **iPhone** : Touchez le bouton de partage → "Sur l'écran d'accueil"
   - **Android** : Menu → "Ajouter à l'écran d'accueil"

C'est comme si vous aviez une vraie app ! 🎯

---

## 💰 Coûts

- **Plan Free** : 0€/mois
- Limitations : 750 heures/mois (largement suffisant pour un usage personnel)
- Si vous dépassez, passez au plan Starter (7$/mois)

---

🎉 **Voilà ! Votre application est maintenant accessible depuis n'importe où !**
