#!/bin/bash
# Sauvegarde NetExpress : base PostgreSQL + volumes de documents.
#
# La base seule ne suffit pas : /app/private_media contient les devis et
# factures signés, dont la base ne garde que le chemin. Restaurer l'une sans
# l'autre donne des documents dont le fichier a disparu.
#
# Le mot de passe n'est jamais écrit ici : pg_dump s'exécute dans le conteneur,
# qui porte déjà POSTGRES_USER et POSTGRES_PASSWORD dans son environnement.
set -euo pipefail

DB_CONTENEUR=abmde3b74fv4y50vhznowcdq
DESTINATION=/var/backups/netexpress
RETENTION_JOURS=14
HORODATAGE=$(date +%Y%m%d-%H%M%S)

mkdir -p "$DESTINATION"

# --- Base de données -------------------------------------------------------
# --format=custom : compressé, et restaurable table par table avec pg_restore.
docker exec "$DB_CONTENEUR" sh -c   'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner'   > "$DESTINATION/base-$HORODATAGE.dump"

# --- Documents -------------------------------------------------------------
for VOLUME in cyaybpy99ywtxqmpp4nyekmc-app-media cyaybpy99ywtxqmpp4nyekmc-media-pv; do
  CHEMIN=/var/lib/docker/volumes/$VOLUME/_data
  [ -d "$CHEMIN" ] || continue
  tar czf "$DESTINATION/$VOLUME-$HORODATAGE.tar.gz" -C "$CHEMIN" .
done

# --- Rotation --------------------------------------------------------------
find "$DESTINATION" -type f \( -name '*.dump' -o -name '*.tar.gz' \)   -mtime +$RETENTION_JOURS -delete

# Une sauvegarde vide est un échec silencieux : mieux vaut refuser tout de suite.
TAILLE=$(stat -c%s "$DESTINATION/base-$HORODATAGE.dump")
if [ "$TAILLE" -lt 1024 ]; then
  echo "ECHEC : la sauvegarde fait $TAILLE octets" >&2
  exit 1
fi

echo "OK $HORODATAGE — base $((TAILLE / 1024)) Ko"
