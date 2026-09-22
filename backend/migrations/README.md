# Migrations de la base de données

Les migrations sont **appliquées automatiquement au démarrage** du backend (PostgreSQL) :

1. `create_all` crée les tables absentes avec le schéma courant ;
2. chaque fichier `NNN_*.sql` non encore appliqué est exécuté une seule fois, puis enregistré
   dans la table `schema_migrations`.

Les scripts sont idempotents (`IF NOT EXISTS`) : ils restent sans effet sur une base neuve.
Pour une nouvelle évolution du schéma, ajouter un fichier numéroté (`004_…sql`) sans modifier
les précédents.

## Migrations disponibles

### 001_add_duration_months.sql (2026-02-07)

Durée variable des contrats (`duration_months`, 1 à 240 mois) : le montant saisi est le montant
total et le **coût annuel moyen** est calculé (montant / nombre d'années). Rendue idempotente
le 2026-09-22 : la durée n'est recalculée que si la colonne vient d'être créée.

Exemples : 2 500 € sur 36 mois → 833,33 €/an ; 15 000 € sur 60 mois → 3 000 €/an.

### 002_contract_lifecycle.sql (2026-09-22)

Cycle de vie des contrats : `category` (budget par poste), `auto_renewal` (reconduction tacite),
`notes`, décision de renouvellement (`renewal_decision`, `decision_comment`, `decision_by`,
`decision_at`). Les tables `contract_events` (historique) et `notification_log` (alertes envoyées)
sont créées automatiquement.

### 003_users_sso.sql (2026-09-22)

Comptes Microsoft Entra ID (`auth_provider`, `entra_oid`, mot de passe local facultatif),
révocation des sessions (`token_version`) et changement de mot de passe imposé
(`must_change_password`).

## Application manuelle (si besoin)

```bash
docker compose exec -T postgres psql -U cockpit -d cockpit_db < backend/migrations/002_contract_lifecycle.sql
```
