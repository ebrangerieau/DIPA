-- Migration: Ajout du champ duration_months à la table contracts
-- Date: 2026-02-07
-- Description: Ajoute le champ duration_months pour stocker la durée du contrat en mois

-- Ajouter la colonne duration_months avec une valeur par défaut de 12 mois
ALTER TABLE contracts
ADD COLUMN IF NOT EXISTS duration_months INTEGER NOT NULL DEFAULT 12;

-- Mettre à jour les contrats existants pour calculer la durée en fonction des dates
-- (approximation basée sur la différence entre start_date et end_date)
UPDATE contracts
SET duration_months = EXTRACT(YEAR FROM AGE(end_date, start_date)) * 12 +
                      EXTRACT(MONTH FROM AGE(end_date, start_date))
WHERE duration_months = 12; -- Ne mettre à jour que ceux avec la valeur par défaut

-- Ajouter un commentaire sur la colonne
COMMENT ON COLUMN contracts.duration_months IS 'Durée du contrat en mois';
COMMENT ON COLUMN contracts.amount IS 'Montant total du contrat';
