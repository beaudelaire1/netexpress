#!/bin/bash
# Sauvegarde NetExpress : base PostgreSQL + volumes de documents, puis copie
# hors-site vers Cloudflare R2.
#
# La base seule ne suffit pas : /app/private_media contient les devis et
# factures signés, dont la base ne garde que le chemin. Restaurer l'une sans
# l'autre donne des documents dont le fichier a disparu.
#
# Aucun secret n'est écrit ici. pg_dump s'exécute dans le conteneur, qui porte
# déjà ses identifiants ; les accès R2 viennent de /etc/netexpress-r2.env,
# lisible par root seul.
set -euo pipefail

DB_CONTENEUR=abmde3b74fv4y50vhznowcdq
DESTINATION=/var/backups/netexpress
RETENTION_JOURS=14
HORODATAGE=$(date +%Y%m%d-%H%M%S)
VOLUMES="cyaybpy99ywtxqmpp4nyekmc-app-media cyaybpy99ywtxqmpp4nyekmc-media-pv"

mkdir -p "$DESTINATION"

# --- Base de données -------------------------------------------------------
# --format=custom : compressé, et restaurable table par table avec pg_restore.
docker exec "$DB_CONTENEUR" sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner' \
  > "$DESTINATION/base-$HORODATAGE.dump"

# Une sauvegarde vide est un échec silencieux : refuser tout de suite plutôt
# que de la publier et de croire le site protégé.
TAILLE=$(stat -c%s "$DESTINATION/base-$HORODATAGE.dump")
if [ "$TAILLE" -lt 1024 ]; then
  echo "ECHEC : la sauvegarde de base fait $TAILLE octets" >&2
  exit 1
fi

# --- Documents -------------------------------------------------------------
for VOLUME in $VOLUMES; do
  CHEMIN=/var/lib/docker/volumes/$VOLUME/_data
  [ -d "$CHEMIN" ] || continue
  tar czf "$DESTINATION/$VOLUME-$HORODATAGE.tar.gz" -C "$CHEMIN" .
done

# --- Copie hors-site -------------------------------------------------------
# Sans elle, les archives partagent le sort du serveur qu'elles protègent.
HORS_SITE="non (/etc/netexpress-r2.env absent)"
if [ -r /etc/netexpress-r2.env ]; then
  set -a
  . /etc/netexpress-r2.env
  set +a

  # Le dépôt distant est défini par l'environnement : pas de second fichier de
  # configuration, donc pas de secret dupliqué sur le disque.
  export RCLONE_CONFIG_R2_TYPE=s3
  export RCLONE_CONFIG_R2_PROVIDER=Cloudflare
  export RCLONE_CONFIG_R2_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID"
  export RCLONE_CONFIG_R2_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY"
  export RCLONE_CONFIG_R2_ENDPOINT="$R2_ENDPOINT"
  export RCLONE_CONFIG_R2_REGION=auto

  # Deux incompatibilités de R2 avec rclone, constatées et non supposées :
  #   --s3-no-check-bucket : R2 n'implémente pas la création de bucket que
  #     rclone tente au préalable.
  #   --s3-no-head : après l'envoi, rclone relit les métadonnées de l'objet ;
  #     R2 répond 501. Le fichier arrivait bien, mais rclone signalait un échec
  #     et les tentatives suivantes ne « réussissaient » que parce que l'objet
  #     existait déjà — un faux succès qui aurait masqué de vraies pannes.
  OPTS=(--s3-no-check-bucket --s3-no-head --retries=3 --low-level-retries=5)

  rclone copy "$DESTINATION" "r2:$R2_BUCKET/sauvegardes/" \
    --include "*-$HORODATAGE.*" "${OPTS[@]}"

  # Rotation côté distant, alignée sur la rétention locale.
  rclone delete "r2:$R2_BUCKET/sauvegardes/" \
    --min-age "${RETENTION_JOURS}d" --s3-no-check-bucket

  # On ne se fie pas au code de retour : on vérifie que l'objet existe vraiment
  # et qu'il a la bonne taille.
  TAILLE_DISTANTE=$(rclone size "r2:$R2_BUCKET/sauvegardes/base-$HORODATAGE.dump" \
    --s3-no-check-bucket --json 2>/dev/null | grep -oE '"bytes":[0-9]+' | cut -d: -f2)
  if [ "${TAILLE_DISTANTE:-0}" != "$TAILLE" ]; then
    echo "ECHEC : sur R2, ${TAILLE_DISTANTE:-0} octets au lieu de $TAILLE" >&2
    exit 1
  fi
  HORS_SITE="oui"
fi

# --- Rotation locale -------------------------------------------------------
find "$DESTINATION" -type f \( -name '*.dump' -o -name '*.tar.gz' \) \
  -mtime +$RETENTION_JOURS -delete

echo "OK $HORODATAGE — base $((TAILLE / 1024)) Ko — hors-site : $HORS_SITE"
