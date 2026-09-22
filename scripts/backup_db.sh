#!/bin/sh
# Sauvegarde complète de la base PostgreSQL du Cockpit IT (production).
#
# À planifier sur le serveur, par exemple chaque nuit à 2 h (crontab -e) :
#   0 2 * * * cd /opt/cockpit-it && ./scripts/backup_db.sh >> /var/log/cockpit-backup.log 2>&1
#
# Restauration (base vide ou à écraser) :
#   gunzip -c /var/backups/cockpit-it/cockpit_db_AAAA-MM-JJ_HHMM.sql.gz \
#     | docker compose -f docker-compose.prod.yml exec -T postgres psql -U cockpit -d cockpit_db
#
# Variables : BACKUP_DIR (défaut /var/backups/cockpit-it), RETENTION_DAYS (défaut 30),
#             COMPOSE_FILE (défaut docker-compose.prod.yml).
# Pensez à copier ces fichiers hors du serveur (NAS, stockage externe) : ils contiennent
# les montants des contrats et les comptes utilisateurs.
set -eu

BACKUP_DIR="${BACKUP_DIR:-/var/backups/cockpit-it}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

umask 077
mkdir -p "$BACKUP_DIR"
FILE="$BACKUP_DIR/cockpit_db_$(date +%Y-%m-%d_%H%M).sql.gz"

docker compose -f "$COMPOSE_FILE" exec -T postgres \
    pg_dump -U cockpit -d cockpit_db --no-owner --clean --if-exists | gzip > "$FILE"

# Contrôle minimal : une sauvegarde vide signale un problème
if [ ! -s "$FILE" ] || [ "$(gunzip -c "$FILE" | head -c 100 | wc -c)" -lt 100 ]; then
    echo "ERREUR : sauvegarde vide ($FILE)" >&2
    exit 1
fi

find "$BACKUP_DIR" -name 'cockpit_db_*.sql.gz' -mtime +"$RETENTION_DAYS" -delete
echo "$(date '+%Y-%m-%d %H:%M') Sauvegarde OK : $FILE ($(du -h "$FILE" | cut -f1))"
