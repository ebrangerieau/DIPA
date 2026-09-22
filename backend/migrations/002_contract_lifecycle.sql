-- Migration 002 : cycle de vie des contrats
-- Date : 2026-09-22
-- Catégorie (budget par poste), reconduction tacite, notes et suivi de la décision
-- de renouvellement. Les tables contract_events et notification_log sont créées
-- automatiquement au démarrage (create_all).

ALTER TABLE contracts ADD COLUMN IF NOT EXISTS category VARCHAR(50) NOT NULL DEFAULT 'autre';
ALTER TABLE contracts ADD COLUMN IF NOT EXISTS auto_renewal BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE contracts ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE contracts ADD COLUMN IF NOT EXISTS renewal_decision VARCHAR(20) NOT NULL DEFAULT 'pending';
ALTER TABLE contracts ADD COLUMN IF NOT EXISTS decision_comment TEXT;
ALTER TABLE contracts ADD COLUMN IF NOT EXISTS decision_by VARCHAR(255);
ALTER TABLE contracts ADD COLUMN IF NOT EXISTS decision_at TIMESTAMP;

CREATE INDEX IF NOT EXISTS ix_contracts_category ON contracts (category);

COMMENT ON COLUMN contracts.auto_renewal IS 'Reconduction tacite à l''échéance';
COMMENT ON COLUMN contracts.renewal_decision IS 'pending | renew | renegotiate | terminate';
