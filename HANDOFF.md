# Handoff Notes

## Auth hardening changes (2026-02-07)

- Le bootstrap admin n'est plus automatique. Pour créer un administrateur au démarrage,
  définir **toutes** les variables suivantes dans `backend/.env` :
  - `BOOTSTRAP_ADMIN_USERNAME`
  - `BOOTSTRAP_ADMIN_EMAIL`
  - `BOOTSTRAP_ADMIN_PASSWORD` (minimum 12 caractères)
- `SECRET_KEY` est désormais exigée quand `DEBUG=false`.
- L'inscription locale refuse la création d'utilisateurs admin et impose un mot de passe
  d'au moins 12 caractères.
- Les états CSRF du flux SSO expirent après 10 minutes.

## Points d'attention pour la suite

- Mettre à jour `.env.example` pour refléter les nouvelles variables si besoin.
- Prévoir une politique de rotation et de stockage sécurisé des secrets en production.
