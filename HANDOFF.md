# Notes de passation

## Version 1.1.0 (2026-09-22) – sécurisation et pilotage

### Actions à réaliser par l'administrateur

1. **Mots de passe d'exemple** : les mots de passe présents dans l'historique du dépôt (anciens
   exemples et ancien écran de connexion) sont désormais **refusés** à la connexion et pour
   l'administrateur initial. Si un compte en utilise un, le réinitialiser :
   `docker compose exec backend python scripts/create_admin.py <identifiant> <email>`,
   et choisir une nouvelle valeur pour `BOOTSTRAP_ADMIN_PASSWORD` dans `backend/.env`.
2. **Tag projet** : taguer dans Zammad les tickets de fond avec `#Projet` (aucun ne l'était encore),
   ou changer `ZAMMAD_PROJECT_TAG`.
3. **SSO Entra ID** : créer l'App Registration, activer « Affectation requise » sur l'application
   d'entreprise, puis `ENABLE_LOCAL_AUTH=false` (voir README).
4. **Alertes** : `ALERTS_ENABLED=true`, destinataires, `MAIL_BACKEND=graph` + permission
   `Mail.Send` limitée à la boîte d'envoi.
5. **Sauvegardes** : planifier `scripts/backup_db.sh` (cron) et copier les fichiers hors du serveur.
6. Facultatif : `ACCESS_TOKEN_EXPIRE_MINUTES=480` (la session se prolonge tant que l'utilisateur
   est actif ; 30 minutes imposent de se reconnecter souvent).

### Corrections

- **Sécurité** : aucune authentification sur les API contrats / tickets (lecture, modification et
  suppression ouvertes à tous) ; inscription publique ouverte ; SSO non fonctionnel (le jeton
  Microsoft était renvoyé tel quel) ; jeton de session en `localStorage` au lieu d'un cookie
  httpOnly (CDC §8) ; messages d'erreur exposant les exceptions ; pas de `.dockerignore`
  (les `.env` étaient copiés dans les images) ; token Zammad inutilement présent dans `frontend/.env`
  (retiré localement, il n'a jamais été commité) ; dépendances vulnérables (python-jose,
  python-multipart, Starlette, axios, react-router, Vite…).
- **Zammad** : la syntaxe `state:closed` ne renvoie rien (il faut `state.name:closed`) ; les
  recherches sont plafonnées à 200 résultats (statistiques tronquées, pagination ajoutée) ;
  états personnalisés et tickets réouverts (`last_close_at`) pris en compte ; jours comptés en
  heure de Paris ; erreurs Zammad remontées (502) au lieu de listes vides silencieuses.
- **Contrats** : filtre sur le statut stocké (jamais mis à jour) au lieu du statut calculé ;
  modification sans validation ; date de fin recalculée et écrasée à l'édition ; décalage d'un
  jour lié au fuseau horaire ; champs de formulaire sans bordure.
- **Divers** : port PostgreSQL mal mappé (`5436:5436`), tests cassés (SQLite / types PostgreSQL,
  champ obligatoire manquant), calendrier d'activité (année figée à 2026, masquage des week-ends
  défaillant), migration 001 non rejouable sans risque, Google Fonts (transfert d'IP, RGPD).

### Évolutions (CDC Phase 1 manquante et Phase 2)

- Autorisations CDC §4.3 (lecture / administration), SSO Entra ID complet (PKCE, cookie, rôles
  d'application, validation des nouveaux comptes), gestion des utilisateurs.
- Timeline conforme au CDC (§2.1), fiches contrat et ticket (lien Zammad), liste des contrats
  filtrable, histogramme 7 / 30 / 90 jours (§2.2).
- Tableau de bord KPI, échéances à traiter, charge par technicien, flux créés / clos.
- Cycle de vie des contrats : catégorie, reconduction tacite (automatique), décision de
  renouvellement tracée, renouvellement, historique, export Excel, impression PDF.
- Alertes e-mail quotidiennes (Graph ou SMTP), sauvegarde / restauration JSON, journal d'audit.
- Déploiement : `docker-compose.prod.yml`, images non-root, Nginx (CSP, en-têtes de sécurité),
  script de sauvegarde, CI GitHub (tests, lint, build, audit, gitleaks).

### Notes techniques

- Toutes les routes sont sous `/api` ; Nginx (production) et Vite (développement) relaient `/api`
  vers le backend : même origine, cookie `SameSite=Lax` limité au chemin `/api`.
- Requêtes modifiantes authentifiées par cookie : en-tête `X-Requested-With: XMLHttpRequest`
  obligatoire (anti-CSRF). Les clients API utilisent `Authorization: Bearer`.
- Migrations SQL automatiques (`backend/migrations/`, table `schema_migrations`).
- Tâche planifiée interne (reconductions, alertes) : prévoir **un seul** worker uvicorn.
- `APP_VERSION` n'est plus lue depuis le `.env` (version du code, `app/config.py`).

### Pistes pour la suite

- Workflow d'approbation à plusieurs niveaux (proposition par l'équipe, validation par la direction).
- Création automatique d'un ticket Zammad à l'approche d'une date limite de résiliation.
- Dépôt des PDF de contrats sur SharePoint depuis le Cockpit (Graph, `Sites.Selected`).
- Répartition du budget par établissement ou par centre de coût.
