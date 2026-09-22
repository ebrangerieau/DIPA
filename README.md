# Cockpit IT

Application web interne de pilotage du service informatique : échéances des contrats
fournisseurs, projets et activité du support issus de Zammad, sur un même écran.

![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.12-blue.svg)
![React](https://img.shields.io/badge/react-18-blue.svg)

## 📋 Fonctionnalités

**Tableau de bord**
- Indicateurs clés : contrats en cours / en préavis, échéances à traiter, budget annuel,
  tickets ouverts (dont non assignés), tickets de plus de 30 jours, clôtures sur 30 jours,
  délai médian de résolution, projets en cours.
- **Échéances à traiter** : contrats dont la date limite de résiliation approche ou en préavis,
  triés par date, avec la décision de renouvellement.
- **Smart Timeline** (vis-timeline) : contrats et tickets `#Projet` sur deux lignes, empilement
  automatique sans collision, couleurs du cahier des charges (vert, orange, rouge, gris, bleu).
- **Activité du support** : histogramme 7 / 30 / 90 jours (hors projets), calendrier annuel,
  flux hebdomadaire créés / clos, charge par technicien, tickets ouverts les plus anciens.
- Budget annuel par catégorie et par fournisseur. Impression / export PDF.

**Contrats**
- Liste filtrable (statut réel calculé, fournisseur, catégorie, recherche), export Excel (CSV).
- Création, modification, suppression réservées aux administrateurs.
- Date limite de résiliation calculée (`échéance − préavis`), reconduction tacite,
  **décision de renouvellement** tracée (à reconduire / renégocier / résilier + justification),
  renouvellement en un clic, **historique** complet des actions.
- Reconduction tacite automatique à l'échéance (si non résilié).

**Alertes e-mail** : récapitulatif quotidien avant les dates limites de résiliation
(J-60, J-30, J-7 par défaut) et avant la fin des contrats sans reconduction, envoyé une seule fois.

**Administration** : comptes (validation des nouveaux comptes Microsoft), état des connecteurs,
alertes (aperçu, test, exécution), sauvegarde / restauration JSON, journal des actions.

## 🏗️ Architecture

```
Navigateur ──HTTPS──> Reverse proxy du serveur ──> frontend (Nginx) ──/api──> backend (FastAPI) ──> PostgreSQL
                                                   (fichiers React)                 │
                                                                                     ├──> Zammad (API, lecture seule)
                                                                                     └──> Microsoft Entra ID / Graph
```

- **Backend** : Python 3.12, FastAPI, SQLAlchemy, PostgreSQL 15.
- **Frontend** : React 18, Tailwind CSS, React Query, vis-timeline, Recharts.
- L'application et l'API partagent **la même origine** (`/api` est relayé par Nginx en production,
  par Vite en développement) : la session est un **cookie httpOnly**, jamais accessible en JavaScript.

```
DIPA/
├── backend/
│   ├── app/
│   │   ├── models/        # Modèles SQLAlchemy (contrats, historique, alertes, utilisateurs)
│   │   ├── schemas/       # Schémas Pydantic de l'API
│   │   ├── routers/       # Endpoints (auth, users, contracts, tickets, dashboard, system)
│   │   ├── services/      # Zammad, Microsoft Graph, alertes, e-mails, règles métier
│   │   ├── config.py      # Configuration (.env)
│   │   └── main.py        # Point d'entrée FastAPI
│   ├── migrations/        # Migrations SQL appliquées automatiquement au démarrage
│   ├── scripts/           # create_admin.py (administrateur de secours)
│   └── tests/             # Tests (pytest, Zammad simulé)
├── frontend/src/
│   ├── pages/             # Tableau de bord, Contrats, Administration, Connexion
│   ├── components/        # Timeline, graphiques, fiches, administration
│   ├── services/          # Appels API
│   └── lib/               # Client HTTP, formatage, référentiels
├── scripts/backup_db.sh   # Sauvegarde PostgreSQL (cron)
├── docker-compose.yml     # Développement
└── docker-compose.prod.yml
```

## 🚀 Démarrage

Voir **[QUICKSTART.md](QUICKSTART.md)** pour l'environnement de développement.

## ⚙️ Configuration

Toute la configuration du backend est dans `backend/.env` (modèle commenté :
[`backend/.env.example`](backend/.env.example)). Principales variables :

| Variable | Rôle |
|---|---|
| `SECRET_KEY` | Signature des sessions, **obligatoire** hors DEBUG (`openssl rand -hex 32`) |
| `ZAMMAD_API_URL`, `ZAMMAD_API_TOKEN` | Accès à Zammad (token d'un agent, lecture seule) |
| `ZAMMAD_PROJECT_TAG` | Tag des tickets projet affichés sur la timeline (défaut `#Projet`) |
| `ENABLE_LOCAL_AUTH` | `false` = connexion Microsoft uniquement |
| `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_REDIRECT_URI` | SSO Entra ID |
| `SSO_AUTO_ACTIVATE`, `SSO_ADMIN_EMAILS`, `SSO_ALLOWED_ROLES`, `SSO_ADMIN_ROLES` | Qui peut entrer, qui est administrateur |
| `ALERTS_ENABLED`, `ALERT_RECIPIENTS`, `ALERT_DAYS_BEFORE_DEADLINE`, `ALERT_HOUR` | Alertes d'échéance |
| `MAIL_BACKEND`, `MAIL_FROM`, `SMTP_*` | Envoi des e-mails (`graph` ou `smtp`) |

Les valeurs d'exemple (contenant « votre », « exemple »…) sont traitées comme non renseignées :
le SSO, par exemple, n'est proposé que lorsqu'il est réellement configuré.

### Zammad

- Créer un token d'accès pour un compte agent (Profil › Token d'accès, permission `ticket.agent`).
  Le Cockpit n'effectue que des lectures.
- **Tickets projet** : ajouter le tag `#Projet` (ou celui défini par `ZAMMAD_PROJECT_TAG`) aux
  tickets de fond pour qu'ils apparaissent sur la timeline. Les autres tickets alimentent les
  statistiques d'activité.
- Les résultats de Zammad sont mis en cache 5 minutes (`ZAMMAD_CACHE_SECONDS`).

### SSO Microsoft Entra ID

1. **Entra ID › Inscriptions d'applications › Nouvelle inscription** (comptes de ce tenant uniquement).
2. **Authentification** : plateforme *Web*, URI de redirection `https://<cockpit>/api/auth/callback`
   (en développement : `http://localhost:5173/api/auth/callback`).
3. **Certificats et secrets** : créer un secret client, le reporter dans `AZURE_CLIENT_SECRET`.
4. **Autorisations** : `User.Read` (délégué) suffit pour la connexion.
5. **Restreindre l'accès** (fortement recommandé dans un établissement où élèves et personnels
   ont un compte) : *Applications d'entreprise › Cockpit IT › Propriétés › Affectation requise = Oui*,
   puis affecter uniquement le groupe du service informatique.
6. **Rôles d'application** (facultatif) : créer un rôle de valeur `Cockpit.Admin` et l'affecter
   aux administrateurs ; les autres comptes affectés sont en lecture seule.

Sans rôle d'application, un nouveau compte Microsoft est créé **inactif** (`SSO_AUTO_ACTIVATE=false`)
et doit être activé par un administrateur (Administration › Utilisateurs). `SSO_ADMIN_EMAILS` permet
de désigner les premiers administrateurs. Une fois le SSO opérationnel, passer
`ENABLE_LOCAL_AUTH=false` (CDC §4.3 : pas de compte local).

### Alertes e-mail

Chaque jour à partir de `ALERT_HOUR`, le backend applique les reconductions tacites échues puis
envoie **un** récapitulatif à `ALERT_RECIPIENTS` s'il y a du nouveau. Chaque alerte n'est envoyée
qu'une fois (table `notification_log`). Administration › Connecteurs et alertes permet un aperçu,
un e-mail de test et une exécution immédiate.

- **Microsoft 365 (recommandé)** : `MAIL_BACKEND=graph`, `MAIL_FROM=<boîte d'envoi>`. Ajouter la
  permission d'**application** `Mail.Send` (consentement administrateur) à l'App Registration, puis
  **limiter** l'application à la seule boîte d'envoi (Exchange Online, *RBAC for Applications* ou
  `New-ApplicationAccessPolicy`). Sans cette restriction, l'application pourrait écrire au nom de
  n'importe quelle boîte du tenant.
- **Relais SMTP** : `MAIL_BACKEND=smtp` et `SMTP_*`. L'authentification SMTP basique d'Exchange
  Online est en cours de retrait par Microsoft : préférer Graph pour Microsoft 365.

## 📦 Déploiement en production

```bash
cp .env.example .env                  # POSTGRES_PASSWORD (openssl rand -hex 24), port d'écoute
cp backend/.env.example backend/.env  # SECRET_KEY, Zammad, Entra ID, alertes…
docker compose -f docker-compose.prod.yml up -d --build
```

- L'application écoute sur `127.0.0.1:8080` : la publier via le reverse proxy HTTPS du serveur
  (celui qui publie Zammad). **HTTPS est obligatoire** : les cookies de session sont `Secure`.
- Les migrations de la base sont appliquées automatiquement au démarrage (`backend/migrations/`).
- Un seul worker backend (les tâches planifiées sont internes au processus).

Exemple de bloc Nginx sur le serveur hôte :

```nginx
server {
    listen 443 ssl;
    server_name cockpit.exemple.fr;
    ssl_certificate     /etc/ssl/certs/cockpit.pem;
    ssl_certificate_key /etc/ssl/private/cockpit.key;
    add_header Strict-Transport-Security "max-age=31536000" always;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

### Sauvegardes

- **Base complète** : `scripts/backup_db.sh` (pg_dump compressé, rétention 30 jours) à planifier
  chaque nuit par cron ; copier les fichiers hors du serveur. Restauration : voir l'en-tête du script.
- **Contrats** : Administration › Sauvegarde exporte / restaure un fichier JSON validé
  (fusion ou remplacement). Les comptes utilisateurs n'y figurent pas.

### Administrateur de secours

```bash
docker compose -f docker-compose.prod.yml exec backend python scripts/create_admin.py <identifiant> <email>
```

Le mot de passe est demandé de façon masquée ; il sert aussi à réinitialiser un compte existant.

## 🔐 Sécurité

- Lecture pour tout utilisateur connecté, écriture réservée aux administrateurs (CDC §4.3).
- Session par cookie httpOnly `SameSite=Lax`, en-tête anti-CSRF exigé sur les requêtes modifiantes,
  sessions révoquées au changement de mot de passe ou à la désactivation d'un compte.
- Mots de passe bcrypt, 12 caractères minimum, limitation des tentatives de connexion ;
  les mots de passe publiés (anciens exemples du dépôt) sont refusés.
- Liens de documents limités à `http(s)://`, contenus de la timeline insérés en texte brut,
  formules neutralisées dans l'export Excel, en-têtes de sécurité (CSP, X-Frame-Options…).
- **Secrets** : `.env` n'est jamais commité ni copié dans les images Docker (`.dockerignore`) ;
  la CI GitHub exécute **gitleaks** à chaque push pour détecter une fuite. En cas de doute sur
  un secret, le révoquer (token Zammad, secret Entra ID) puis le remplacer.

## 🔧 Développement

```bash
# Backend
cd backend
python -m venv .venv && .venv\Scripts\activate    # Linux/macOS : source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8001
pytest                                            # 78 tests (Zammad simulé, SQLite en mémoire)

# Frontend
cd frontend
npm install
npm run dev        # http://localhost:5173, /api relayé vers localhost:8001
npm run lint
npm run build
```

## 📝 API

Documentation interactive : `/api/docs` (Swagger). Principaux endpoints :

| Domaine | Endpoints |
|---|---|
| Authentification | `GET /api/auth/config`, `POST /api/auth/login/local`, `POST /api/auth/logout`, `GET /api/auth/me`, `POST /api/auth/change-password`, `GET /api/auth/login` (SSO), `GET /api/auth/callback` |
| Contrats | `GET/POST /api/contracts`, `GET/PUT/DELETE /api/contracts/{id}`, `POST /api/contracts/{id}/decision`, `POST /api/contracts/{id}/renew`, `GET /api/contracts/{id}/events`, `GET /api/contracts/export.csv`, `GET /api/contracts/timeline/data` |
| Tickets | `GET /api/tickets/projects`, `GET /api/tickets/stats`, `GET /api/tickets/timeline/data`, `GET /api/tickets/{id}` |
| Tableau de bord | `GET /api/dashboard/summary` |
| Administration | `/api/users`, `/api/system/backup`, `/api/system/restore`, `/api/system/status`, `/api/system/alerts/*`, `/api/system/events` |
