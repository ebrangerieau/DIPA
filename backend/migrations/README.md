# Migrations de la base de données

Ce dossier contient les scripts de migration SQL pour mettre à jour le schéma de la base de données.

## Migrations disponibles

### 001_add_duration_months.sql (2026-02-07)

**Description** : Ajoute le champ `duration_months` à la table `contracts` pour gérer des contrats de durée variable.

**Changements** :
- Ajout de la colonne `duration_months` (INTEGER NOT NULL DEFAULT 12)
- Calcul automatique de la durée pour les contrats existants basé sur les dates de début et de fin
- Ajout de commentaires sur les colonnes pour clarifier leur usage

**Application** :
```bash
docker-compose exec -T postgres psql -U cockpit -d cockpit_db < backend/migrations/001_add_duration_months.sql
```

## Nouvelle fonctionnalité

Les contrats supportent maintenant des durées variables (de 1 à 120 mois / 10 ans) avec :

- **Montant total** : Le montant global du contrat (au lieu de "montant annuel")
- **Durée en mois** : La durée réelle du contrat
- **Coût annuel moyen** : Calculé automatiquement (montant total / nombre d'années)

### Exemples d'utilisation

- Contrat Solidworks : 2500€ pour 36 mois (3 ans) → Coût annuel : 833.33€/an
- Licence Office 365 : 1200€ pour 12 mois (1 an) → Coût annuel : 1200€/an
- Maintenance serveurs : 15000€ pour 60 mois (5 ans) → Coût annuel : 3000€/an

### Affichage dans l'interface

Le formulaire de création de contrat affiche maintenant :
1. Le montant total du contrat
2. La durée en mois (avec conversion en années)
3. Le **coût annuel moyen calculé en temps réel**

Cela permet une meilleure comparaison entre contrats de durées différentes.
