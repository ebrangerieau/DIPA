# Guide de Démarrage Rapide - Cockpit IT (Authentification Locale)

## 🚀 Démarrage en 3 Minutes

Cette version utilise l'**authentification locale** (username/password) pour le développement. Le SSO Microsoft sera configuré plus tard.

### Prérequis
- Docker et Docker Compose installés
- Token API Zammad

---

## Étape 1 : Configuration Backend

```bash
cd backend
cp .env.example .env
```

Éditez `backend/.env` et remplissez **uniquement** les valeurs suivantes :

```env
# Authentification locale activée
ENABLE_LOCAL_AUTH=true

# API Zammad (OBLIGATOIRE)
ZAMMAD_API_URL=https://votre-instance.zammad.com
ZAMMAD_API_TOKEN=votre_token_api_zammad

# Sécurité (Générer une clé secrète)
SECRET_KEY=$(openssl rand -hex 32)
```

> **Note :** Les variables Azure AD ne sont pas nécessaires pour le moment.

---

## Étape 2 : Configuration Frontend

```bash
cd ../frontend
cp .env.example .env
```

Le fichier `.env` par défaut fonctionne :
```env
VITE_API_URL=http://localhost:8000
```

---

## Étape 3 : Démarrage de l'Application

Depuis la racine du projet :

```bash
docker-compose up -d
```

**Vérification des logs :**
```bash
docker-compose logs -f backend
```

Vous devriez voir :
```
✅ Base de données initialisée
� Utilisateur admin créé (username: admin, password: admin123)
⚠️  IMPORTANT: Changez ce mot de passe !
```

---

## Étape 4 : Connexion

1. Ouvrir http://localhost:5173
2. Vous serez redirigé vers la page de login
3. Utiliser les identifiants par défaut :
   - **Username :** `admin`
   - **Password :** `admin123`

---

## 🔐 Gestion des Utilisateurs

### Créer un Nouvel Utilisateur

**Via l'API (Swagger) :**
1. Aller sur http://localhost:8000/docs
2. Endpoint : `POST /auth/register`
3. Body :
```json
{
  "username": "john",
  "email": "john@example.com",
  "password": "motdepasse123",
  "full_name": "John Doe",
  "is_admin": false
}
```

### Changer le Mot de Passe Admin

Pour le moment, utilisez l'API ou la base de données directement. Une interface de gestion des utilisateurs sera ajoutée plus tard.

---

## 📊 Tester l'Application

### 1. Créer un Contrat de Test

**Via l'API (Swagger) :**
1. Aller sur http://localhost:8000/docs
2. Cliquer sur le cadenas 🔒 en haut à droite
3. Utiliser le formulaire OAuth2 :
   - Username: `admin`
   - Password: `admin123`
4. Endpoint : `POST /contracts`
5. Body :
```json
{
  "name": "Licence Microsoft 365",
  "supplier": "Microsoft",
  "amount": 50000,
  "start_date": "2024-01-01",
  "end_date": "2025-12-31",
  "notice_period_days": 90,
  "sharepoint_file_url": "https://votreentreprise.sharepoint.com/contrat.pdf"
}
```

### 2. Vérifier la Timeline

1. Retourner sur http://localhost:5173
2. Vous devriez voir :
   - Le contrat sur la timeline
   - Les tickets Zammad avec tag #Projet
   - L'histogramme des tickets quotidiens

---

## � Commandes Utiles

### Arrêter l'Application
```bash
docker-compose down
```

### Voir les Logs
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Reconstruire les Images
```bash
docker-compose build
docker-compose up -d
```

---

## � Passer au SSO Microsoft (Plus Tard)

Quand vous serez prêt à configurer le SSO :

1. Modifier `backend/.env` :
```env
ENABLE_LOCAL_AUTH=false
```

2. Configurer les variables Azure AD :
```env
AZURE_TENANT_ID=votre_tenant_id
AZURE_CLIENT_ID=votre_client_id
AZURE_CLIENT_SECRET=votre_client_secret
```

3. Redémarrer le backend :
```bash
docker-compose restart backend
```

---

## 🐛 Dépannage

### Problème : "Utilisateur admin créé" n'apparaît pas dans les logs

**Solution :**
```bash
docker-compose down -v
docker-compose up -d
```

### Problème : Erreur "Token invalide"

**Solution :**
1. Se déconnecter
2. Vider le cache du navigateur (localStorage)
3. Se reconnecter

---

## ✅ Checklist de Démarrage

- [ ] Docker et Docker Compose installés
- [ ] Token API Zammad récupéré
- [ ] `backend/.env` configuré (ZAMMAD_API_URL, ZAMMAD_API_TOKEN)
- [ ] `ENABLE_LOCAL_AUTH=true` dans `.env`
- [ ] `docker-compose up -d` exécuté
- [ ] Message "Utilisateur admin créé" visible dans les logs
- [ ] Connexion réussie sur http://localhost:5173
- [ ] Dashboard accessible

---

**Bon pilotage avec Cockpit IT ! 🚀**
