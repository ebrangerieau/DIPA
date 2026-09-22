# Guide de démarrage rapide – Cockpit IT (développement)

## Prérequis
- Docker et Docker Compose
- Un token API Zammad (compte agent, lecture seule)

---

## Étape 1 : configuration du backend

```bash
cd backend
cp .env.example .env
```

Renseigner au minimum dans `backend/.env` :

```env
DEBUG=true
ENABLE_LOCAL_AUTH=true

# Zammad
ZAMMAD_API_URL=https://votre-instance-zammad
ZAMMAD_API_TOKEN=<token>

# Clé de signature des sessions : openssl rand -hex 32
SECRET_KEY=<64 caractères hexadécimaux>

# Administrateur initial (créé seulement s'il n'existe aucun administrateur)
BOOTSTRAP_ADMIN_USERNAME=admin
BOOTSTRAP_ADMIN_EMAIL=admin@votre-domaine.fr
BOOTSTRAP_ADMIN_PASSWORD=<12 caractères minimum, propre à votre installation>
```

> Les variables Microsoft Entra ID ne sont pas nécessaires pour commencer : le bouton
> « Se connecter avec Microsoft » n'apparaît que lorsqu'elles sont renseignées.

Le frontend n'a besoin d'aucun secret : ne mettez jamais de token dans `frontend/.env`
(les variables `VITE_*` sont envoyées aux navigateurs).

---

## Étape 2 : démarrage

Depuis la racine du projet :

```bash
docker compose up -d --build
docker compose logs -f backend
```

Au premier démarrage, le backend crée les tables, applique les migrations et, si les variables
`BOOTSTRAP_ADMIN_*` sont définies, l'administrateur initial.

- Application : http://localhost:5173
- Documentation de l'API : http://localhost:8001/api/docs

---

## Étape 3 : première connexion

1. Ouvrir http://localhost:5173 et se connecter avec le compte `BOOTSTRAP_ADMIN_*`.
2. Le changement du mot de passe initial est **imposé** à la première connexion.
3. Créer les contrats (bouton « Nouveau contrat ») ; ils apparaissent sur la timeline.
4. Dans Zammad, taguer les tickets de fond avec `#Projet` pour les voir sur la timeline.

---

## 🔐 Gestion des utilisateurs

Administration › Utilisateurs : création de comptes locaux (mot de passe temporaire à changer),
droits administrateur, activation / désactivation, réinitialisation du mot de passe.
L'inscription libre n'existe plus : seuls les administrateurs créent des comptes.

Administrateur de secours (mot de passe oublié, compte bloqué) :

```bash
docker compose exec backend python scripts/create_admin.py admin admin@votre-domaine.fr
```

---

## 🔧 Commandes utiles

```bash
docker compose down                   # arrêter
docker compose logs -f frontend       # journaux
docker compose exec backend pytest    # tests du backend
docker compose build && docker compose up -d   # reconstruire après une mise à jour
```

La base PostgreSQL de développement est accessible depuis le poste sur `localhost:5436`
(utilisateur `cockpit`).

---

## 🔐 Passer au SSO Microsoft

1. Créer l'App Registration (voir README, section « SSO Microsoft Entra ID »).
2. Renseigner `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` et
   `AZURE_REDIRECT_URI=http://localhost:5173/api/auth/callback`.
3. `SSO_ADMIN_EMAILS=<votre adresse>` pour être administrateur dès la première connexion.
4. `docker compose restart backend`.
5. Une fois le SSO validé : `ENABLE_LOCAL_AUTH=false`.

---

## 🐛 Dépannage

| Problème | Solution |
|---|---|
| « Session invalide ou expirée » | Se reconnecter (la session dure `ACCESS_TOKEN_EXPIRE_MINUTES`) |
| « Ce mot de passe a été publié… » | Réinitialiser le compte avec `scripts/create_admin.py` |
| Indicateurs Zammad indisponibles | Vérifier `ZAMMAD_API_URL` / `ZAMMAD_API_TOKEN` (Administration › Connecteurs) |
| Aucun projet sur la timeline | Aucun ticket ne porte encore le tag `ZAMMAD_PROJECT_TAG` |
| Le backend refuse de démarrer (`SECRET_KEY`) | Définir une clé de 32 caractères minimum ou `DEBUG=true` en local |
