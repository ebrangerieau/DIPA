# Cockpit IT

Application web interne pour le pilotage visuel des contrats IT et des projets issus de Zammad.

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![React](https://img.shields.io/badge/react-18.2-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 📋 Description

Cockpit IT est une application de pilotage visuel qui permet de gérer deux échelles de temps :

- **Temps long** : Renouvellements de contrats avec calcul automatique des périodes de préavis
- **Temps opérationnel** : Projets de fond issus de Zammad (tickets avec tag #Projet)

### Fonctionnalités Principales

✨ **Smart Timeline** : Timeline interactive avec positionnement intelligent (Smart Stacking) pour éviter les collisions visuelles

📊 **Histogramme des Tickets** : Visualisation du volume quotidien des tickets clos

🔐 **Authentification SSO** : Connexion via Microsoft Entra ID (Azure AD)

📄 **Intégration SharePoint** : Accès direct aux PDF des contrats stockés sur SharePoint

🎯 **Filtrage Intelligent** : Seuls les tickets avec tag #Projet apparaissent sur la timeline

## 🏗️ Architecture

### Stack Technologique

- **Backend** : Python FastAPI 
- **Frontend** : React 18 + Tailwind CSS
- **Base de données** : PostgreSQL 15
- **Timeline** : vis-timeline
- **Graphiques** : Recharts
- **Conteneurisation** : Docker + Docker Compose

### Structure du Projet

```
DIPA/
├── backend/
│   ├── app/
│   │   ├── models/          # Modèles SQLAlchemy
│   │   ├── routers/         # Endpoints API
│   │   ├── services/        # Services (Zammad, Graph API)
│   │   ├── config.py        # Configuration
│   │   ├── database.py      # Connexion PostgreSQL
│   │   └── main.py          # Point d'entrée FastAPI
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/      # Composants React
│   │   ├── pages/           # Pages
│   │   ├── services/        # Services API
│   │   └── config/          # Configuration
│   ├── Dockerfile
│   ├── package.json
│   └── .env.example
└── docker-compose.yml
```

## 🚀 Installation et Démarrage

### Prérequis

- Docker et Docker Compose
- Token API Zammad
- App Registration Azure AD (pour le SSO)

### Configuration

1. **Cloner le dépôt**
```bash
git clone <url-du-repo>
cd DIPA
```

2. **Configurer le backend**
```bash
cd backend
cp .env.example .env
# Éditer .env avec vos valeurs
```

Variables à configurer dans `backend/.env` :
- `ZAMMAD_API_URL` : URL de votre instance Zammad
- `ZAMMAD_API_TOKEN` : Token API Zammad
- `AZURE_TENANT_ID` : ID du tenant Azure AD
- `AZURE_CLIENT_ID` : ID client de l'App Registration
- `AZURE_CLIENT_SECRET` : Secret client
- `SHAREPOINT_SITE_URL` : URL du site SharePoint

3. **Configurer le frontend**
```bash
cd ../frontend
cp .env.example .env
# Par défaut, VITE_API_URL=http://localhost:8000
```

4. **Démarrer l'application**
```bash
cd ..
docker-compose up -d
```

L'application sera accessible sur :
- Frontend : http://localhost:5173
- Backend API : http://localhost:8000
- Documentation API : http://localhost:8000/docs

## 📊 Schéma de Base de Données

### Table `contracts`

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Identifiant unique |
| name | VARCHAR(255) | Nom du contrat |
| supplier | VARCHAR(255) | Fournisseur |
| amount | DECIMAL(10,2) | Montant annuel |
| start_date | DATE | Date de début |
| end_date | DATE | Date de fin |
| notice_period_days | INTEGER | Préavis en jours |
| sharepoint_file_url | TEXT | Lien vers le PDF |
| status | VARCHAR(50) | Statut |

### Table `ticket_cache` (optionnelle)

Cache local des tickets Zammad pour améliorer les performances.

## 🎨 Smart Timeline - Fonctionnement

### Algorithme de Smart Stacking

1. **Récupération des données** : Contrats + Tickets #Projet
2. **Détection des collisions** : Vérification des chevauchements temporels
3. **Assignation automatique** : Création de lignes horizontales si collision
4. **Affichage** :
   - **Contrats** :
     - Point vert avant le préavis
     - Barre orange (> 30 jours avant échéance)
     - Barre rouge (< 30 jours avant échéance)
   - **Tickets** : Barres bleues (création → clôture)

### Interactivité

- Clic sur un élément → Modal avec détails
- Zoom et navigation temporelle
- Lien direct vers SharePoint (contrats) ou Zammad (tickets)

## 🔧 Développement

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Tests

```bash
# Backend
cd backend
pytest tests/ --cov=app

# Frontend
cd frontend
npm run test
```

## 📝 API Endpoints

### Authentification
- `GET /auth/login` : Redirection SSO
- `GET /auth/callback` : Callback OAuth
- `GET /auth/me` : Informations utilisateur

### Contrats
- `GET /contracts` : Liste des contrats
- `POST /contracts` : Créer un contrat
- `PUT /contracts/{id}` : Mettre à jour
- `DELETE /contracts/{id}` : Supprimer
- `GET /contracts/timeline/data` : Données timeline

### Tickets
- `GET /tickets/projects` : Tickets #Projet
- `GET /tickets/stats` : Statistiques (histogramme)
- `GET /tickets/timeline/data` : Données timeline

## 🔐 Configuration Azure AD

1. Créer une App Registration dans Azure Portal
2. Configurer les permissions :
   - `User.Read`
   - `Files.Read.All`
   - `Sites.Read.All`
3. Ajouter l'URL de redirection : `http://localhost:8000/auth/callback`
4. Générer un secret client
5. Copier Tenant ID, Client ID et Client Secret dans `.env`

## 📦 Déploiement en Production

1. **Build de production**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

2. **Variables d'environnement**
   - Modifier `SECRET_KEY` (générer avec `openssl rand -hex 32`)
   - Désactiver `DEBUG=false`
   - Configurer les CORS pour votre domaine

3. **Reverse Proxy** (Nginx/Traefik recommandé)

## 🤝 Contribution

Ce projet suit l'architecture en 3 couches définie dans `AGENT.md` :
1. **Directives** : SOPs en Markdown
2. **Orchestration** : Décisions intelligentes
3. **Exécution** : Scripts Python déterministes

## 📄 License

MIT

## 👥 Auteur

Développé pour le pilotage IT interne.

## 📞 Support

Pour toute question, consulter la documentation API : http://localhost:8000/docs
