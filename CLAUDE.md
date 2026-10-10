# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**IMPORTANT : toutes les réponses doivent être en français.** Le code, les commentaires, les messages
de l'API et les messages de commit du projet sont eux aussi en français.

## Projet

**Cockpit IT** (dépôt DIPA) : application web interne de pilotage du service informatique. Elle
réunit sur un même écran les échéances des contrats fournisseurs (préavis, reconduction, budget),
les projets et l'activité du support issus de Zammad. Le code cite le cahier des charges par section
(« CDC §4.3 »), mais ce document ne figure pas dans le dépôt. `HANDOFF.md` contient les notes de
passation par version : actions attendues de l'administrateur et pistes d'évolution.

## Commandes

Backend (`backend/`, Python 3.12) :

```bash
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8001        # lit backend/.env (modèle : backend/.env.example)
pytest                                           # SQLite en mémoire, Zammad simulé, aucun .env lu
pytest tests/test_contracts.py::test_create_and_read_contract   # un seul test
pytest --cov=app
pip-audit -r requirements.txt                    # failles connues des dépendances
```

Frontend (`frontend/`, Node 24 / npm 11) :

```bash
npm ci
npm run dev       # http://localhost:5173, /api relayé vers VITE_PROXY_TARGET (défaut localhost:8001)
npm run lint      # --max-warnings 0
npm run build
```

Il n'existe pas de tests frontend. Modifier `package-lock.json` avec **npm 11** (celui de Node 24,
comme la CI et l'image Docker) : npm 10 supprime les champs `libc` qui servent à choisir les
binaires musl de l'image Alpine.

Pile complète : `docker compose up -d --build` (développement, rechargement à chaud, PostgreSQL sur
`localhost:5436`) ou `docker compose -f docker-compose.prod.yml up -d --build` (production).
La CI (`.github/workflows/ci.yml`) exécute gitleaks, pytest + pip-audit, puis lint + build +
`npm audit` (dépendances de production, niveau modéré). Elle tourne aussi chaque lundi.

## Architecture

**Même origine.** Toutes les routes du backend sont sous `/api`. Vite (dev) et Nginx
(`frontend/nginx.conf`, prod) relaient `/api` vers le backend : pas de CORS en pratique.

**Session et autorisations** (`app/auth.py`, `app/security.py`) :
- La session est un JWT dans un cookie httpOnly `SameSite=Lax` limité au chemin `/api`. Elle est
  glissante : le cookie est renouvelé passé la moitié de sa durée.
- Les requêtes modifiantes authentifiées par cookie exigent l'en-tête
  `X-Requested-With: XMLHttpRequest` (anti-CSRF). `frontend/src/lib/api.js` l'ajoute partout.
- `Authorization: Bearer` est aussi accepté (Swagger `/api/docs`, scripts).
- Les sessions sont révoquées en incrémentant `User.token_version` (claim `ver`).
- `get_current_user` donne la lecture à tout compte actif ; `require_admin` protège toute écriture.

**Contrats** :
- Le statut n'est jamais stocké : il est calculé par les propriétés de `app/models/contract.py`
  (`computed_status`, `termination_deadline = end_date − notice_period_days`, `timeline_color`,
  `annual_cost = amount / (duration_months / 12)`). La colonne `status` est un vestige, ne pas
  l'utiliser.
- « Aujourd'hui » s'obtient avec `timeutils.today()` (fuseau `TIMEZONE`), jamais `date.today()`.
  Les tests figent cette date au 22/09/2026 (`FIXED_TODAY` dans `tests/conftest.py`).
- Les règles métier sont dans `app/services/contract_service.py` : historique (`log_event`,
  `snapshot` / `diff`), renouvellement, reconduction tacite, indicateurs, échéances à traiter,
  export CSV.
- Ajouter un champ de contrat touche : le modèle, une migration SQL, les schémas Pydantic,
  `TRACKED_FIELDS` (historique et sauvegarde JSON de `routers/system.py`), l'export CSV,
  `_FIELD_LABELS` dans `main.py` et le formulaire `ContractFormModal.jsx`.
- Les référentiels (catégories, décisions, couleurs) sont dupliqués dans
  `frontend/src/lib/constants.js` : les garder alignés avec `app/models/contract.py`.

**Zammad** (`app/services/zammad_service.py`, lecture seule) :
- Les particularités de l'API réelle sont documentées en tête de fichier : filtre `state.name:`
  (la syntaxe `state:` ne renvoie rien), pagination à 200 résultats, états classés par
  `state_type_id`, `last_close_at` pour les tickets réouverts, tags absents des résultats de recherche.
- Les résultats sont mis en cache en mémoire (`ZAMMAD_CACHE_SECONDS`).
- `ZammadError` devient une réponse HTTP 502 (gestionnaire dans `main.py`). Le tableau de bord
  (`routers/dashboard.py`) renvoie alors `tickets_error` sans échouer.
- Les tickets portant `ZAMMAD_PROJECT_TAG` vont sur la timeline ; les autres alimentent les
  statistiques.
- Tests : `tests/zammad_fake.py` (`httpx.MockTransport`), injecté via la dépendance
  `get_zammad_service`.

**Tâche planifiée** (`app/scheduler.py`) : chaque heure à partir de `ALERT_HOUR`, elle applique les
reconductions tacites puis envoie les alertes e-mail (`services/alerts_service.py`, chaque alerte
une seule fois grâce à `notification_log`). Elle tourne dans le processus : **un seul worker
uvicorn**.

**Base de données** : au démarrage, `init_db()` exécute `create_all` puis les migrations
`backend/migrations/NNN_*.sql` (PostgreSQL uniquement, suivies dans la table `schema_migrations`).
Pour faire évoluer le schéma : modifier le modèle **et** ajouter un fichier numéroté idempotent
(`IF NOT EXISTS`), sans jamais modifier les fichiers précédents.

**Configuration** (`app/config.py`, pydantic-settings, `backend/.env`) :
- Une valeur d'exemple (« votre », « exemple », « change »…) compte comme non renseignée
  (`_is_configured`). Le SSO, Zammad et l'envoi d'e-mails ne s'activent qu'une fois réellement
  configurés.
- `SECRET_KEY` est obligatoire hors `DEBUG`.
- `APP_VERSION` est définie dans le code. La reporter aussi dans `frontend/package.json` et dans
  le badge du README.

**SSO Entra ID** : `routers/auth.py` et `services/graph_service.py` (MSAL, PKCE, état du flux dans un
cookie signé). Les comptes sont provisionnés par `user_service.provision_sso_user` : rôles
d'application, comptes inactifs jusqu'à validation par un administrateur.

**Frontend** : React 18, React Query, Tailwind, vis-timeline, Recharts. Les routes sont en français
(`/contrats`, `/admin`, `/login`, voir `App.jsx`). Les appels API passent par
`src/services/*Service.js`. Les erreurs de validation du backend sont déjà traduites en français
(`_french_message` dans `main.py`).

## Conventions

- Commits au format Conventional Commits, en français : `feat(frontend): …`, `fix(backend): …`,
  `chore(ci): …`, `docs: …`.
- Politique des mots de passe dans `app/security.py` : 12 caractères minimum, 72 octets maximum
  (bcrypt), mots de passe déjà publiés refusés par empreinte.
- gitleaks tourne en CI : marquer `# gitleaks:allow` une valeur factice volontaire.
- Administrateur de secours : `python scripts/create_admin.py <identifiant> <email>`.
