#!/bin/sh
set -eu

PROCESS_TYPE="${PROCESS_TYPE:-web}"

case "$PROCESS_TYPE" in
  web)
    # Les checks de sécurité/configuration doivent échouer avant toute mise en trafic.
    python manage.py check --deploy --fail-level WARNING

    # Le premier déploiement Coolify n'exécute pas toujours une commande de
    # pré-déploiement. Les migrations sont donc exécutées ici sous verrou
    # PostgreSQL, avant que Gunicorn n'ouvre le port de l'application.
    if [ "${RUN_MIGRATIONS_ON_START:-true}" = "true" ]; then
      python manage.py deploy_migrate
    fi

    exec gunicorn netexpress.wsgi:application \
      --bind "0.0.0.0:${PORT:-8000}" \
      --workers "${WEB_CONCURRENCY:-2}" \
      --threads "${WEB_THREADS:-4}" \
      --timeout "${GUNICORN_TIMEOUT:-120}" \
      --graceful-timeout "${GUNICORN_GRACEFUL_TIMEOUT:-30}" \
      --access-logfile - \
      --error-logfile -
    ;;

  worker)
    # CELERY_TASK_ROUTES répartit actuellement les tâches sur les files
    # messaging, documents et notifications. Un worker limité à la file
    # Celery par défaut laisserait donc ces tâches en attente indéfiniment.
    exec celery -A netexpress worker \
      --hostname="worker@%h" \
      --queues="${CELERY_QUEUES:-celery,messaging,documents,notifications}" \
      --loglevel="${CELERY_LOG_LEVEL:-INFO}" \
      --concurrency="${CELERY_WORKER_CONCURRENCY:-2}" \
      --max-tasks-per-child="${CELERY_MAX_TASKS_PER_CHILD:-200}"
    ;;

  *)
    echo "PROCESS_TYPE invalide: $PROCESS_TYPE (attendu: web ou worker)" >&2
    exit 64
    ;;
esac
