-- Migration 001 : durée variable des contrats (colonne duration_months)
-- Date : 2026-02-07 (rendue idempotente le 2026-09-22 pour l'exécution automatique)
-- La durée n'est recalculée que si la colonne vient d'être créée : une base où la
-- migration avait déjà été appliquée à la main n'est pas modifiée.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'contracts' AND column_name = 'duration_months'
    ) THEN
        ALTER TABLE contracts ADD COLUMN duration_months INTEGER NOT NULL DEFAULT 12;

        -- Durée approximative à partir des dates (du 01/01 au 31/12 = 12 mois)
        UPDATE contracts
        SET duration_months = GREATEST(1, (
            EXTRACT(YEAR FROM AGE(end_date + 1, start_date)) * 12
            + EXTRACT(MONTH FROM AGE(end_date + 1, start_date))
        )::INTEGER);
    END IF;
END $$;

COMMENT ON COLUMN contracts.duration_months IS 'Durée du contrat en mois';
COMMENT ON COLUMN contracts.amount IS 'Montant total du contrat';
