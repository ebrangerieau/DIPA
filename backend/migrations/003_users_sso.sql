-- Migration 003 : comptes SSO Microsoft Entra ID et durcissement des sessions
-- Date : 2026-09-22
-- Les comptes SSO n'ont pas de mot de passe local ; token_version permet
-- d'invalider les sessions ouvertes (changement de mot de passe, désactivation).

ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_provider VARCHAR(20) NOT NULL DEFAULT 'local';
ALTER TABLE users ADD COLUMN IF NOT EXISTS entra_oid VARCHAR(64);
ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE;

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_entra_oid ON users (entra_oid);
