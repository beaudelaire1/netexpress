# NetExpress — production OVH + Coolify

Ce document décrit la cible de production du dépôt. Il ne remplace pas les sauvegardes ni les secrets configurés dans Coolify.

## 1. Architecture cible

NetExpress doit être déployé avec quatre ressources distinctes dans le même projet/environnement Coolify :

1. **PostgreSQL** — base de données de production, stockage persistant et sauvegardes activées.
2. **Redis** — cache Django et broker/backend Celery.
3. **NetExpress Web** — application Dockerfile exposée en HTTP interne sur le port `8000`.
4. **NetExpress Worker** — seconde application construite avec le même dépôt et le même Dockerfile, sans domaine public, avec `PROCESS_TYPE=worker`.

Le web et le worker doivent utiliser exactement la même `DJANGO_SECRET_KEY`, la même `DATABASE_URL`, la même `REDIS_URL` et les mêmes variables métier.

## 2. Source Git

Pour les deux applications :

- Repository : `beaudelaire1/netexpress`
- Branch de production : `for_prod`
- Build Pack : **Dockerfile**
- Base Directory : `src/src_netexpress`
- Dockerfile Location : `Dockerfile`

Le Dockerfile écoute sur `0.0.0.0:8000` pour le web. Ne pas ajouter de commande de démarrage différente dans Coolify : `start.sh` sélectionne le processus à partir de `PROCESS_TYPE`.

## 3. Application Web

Variables spécifiques :

```env
PROCESS_TYPE=web
PORT=8000
RUN_MIGRATIONS_ON_START=true
WEB_CONCURRENCY=2
WEB_THREADS=4
GUNICORN_TIMEOUT=120
GUNICORN_GRACEFUL_TIMEOUT=30
```

Configurer `Ports Exposes` sur `8000` et associer le domaine HTTPS public choisi à l'application.

Le conteneur exécute avant Gunicorn :

1. `python manage.py check --deploy --fail-level WARNING` ;
2. `python manage.py deploy_migrate` ;
3. Gunicorn uniquement si les deux étapes précédentes réussissent.

`deploy_migrate` prend un verrou consultatif PostgreSQL. Deux nouveaux conteneurs peuvent donc démarrer simultanément sans exécuter les migrations en concurrence.

Les migrations ne reposent pas sur le champ « Pre-deployment command » de Coolify : ce mécanisme n'est pas exécuté lorsqu'il n'existe encore aucun conteneur, notamment au premier déploiement.

Le verrou évite deux exécutions concurrentes, mais il ne rend pas une migration destructive compatible avec un rolling update. Toute migration qui supprime ou renomme immédiatement une colonne/table encore utilisée par l'ancienne version doit être déployée en plusieurs étapes « expand/contract » ou pendant une fenêtre de maintenance contrôlée.

## 4. Worker Celery

Créer une seconde application avec le même dépôt, la même branche, le même Base Directory et le même Dockerfile.

Variables spécifiques :

```env
PROCESS_TYPE=worker
RUN_MIGRATIONS_ON_START=false
CELERY_QUEUES=celery,messaging,documents,notifications
CELERY_LOG_LEVEL=INFO
CELERY_WORKER_CONCURRENCY=2
CELERY_MAX_TASKS_PER_CHILD=200
```

Ne pas attribuer de domaine ni de port public au worker. Les formulaires NetExpress utilisent déjà des tâches Celery ; Redis sans worker ne constitue donc pas une architecture complète.

Les routes Celery existantes envoient les tâches métier vers les files `messaging`, `documents` et `notifications`. Le worker doit donc consommer explicitement ces files, en plus de la file `celery` par défaut. Ne pas retirer une file de `CELERY_QUEUES` sans avoir d'abord vérifié qu'aucune tâche n'y est routée.

## 5. Variables obligatoires

Les valeurs suivantes doivent être définies dans Coolify. Le démarrage de production échoue volontairement si un prérequis critique manque :

```text
DJANGO_SECRET_KEY
SITE_URL
DATABASE_URL
REDIS_URL
EMAIL_HOST
EMAIL_HOST_USER
EMAIL_HOST_PASSWORD
DEFAULT_FROM_EMAIL
CONTACT_RECEIVER_EMAIL
TURNSTILE_SITE_KEY
TURNSTILE_SECRET_KEY
COMPANY_SIRET
BANK_ACCOUNT_NAME
BANK_ACCOUNT_NUMBER
```

Le courrier part par SMTP standard : n'importe quel hébergeur de messagerie convient (Brevo, OVH, IONOS…), aucune API propriétaire n'est requise. `EMAIL_PORT` vaut 587 et `EMAIL_USE_TLS` vaut `True` par défaut ; pour un relais en SSL implicite, poser `EMAIL_PORT=465` et `EMAIL_USE_SSL=True`. La production refuse de démarrer si le chiffrement est désactivé des deux côtés, car les identifiants du relais transiteraient en clair.

Pour revenir à l'API Brevo, poser `EMAIL_BACKEND=core.backends.brevo_backend.BrevoEmailBackend` et `BREVO_API_KEY` à la place des trois variables SMTP.

Une fois déployé, `python manage.py send_test_email` affiche le transport réellement actif et envoie un message de contrôle.

`COMPANY_BIC` reste facultatif ; s'il est renseigné, son format est contrôlé. `BANK_ACCOUNT_NUMBER` est validé avec la clé de contrôle IBAN et est ensuite formaté pour l'affichage sur les PDF.

Ne mettre aucune vraie coordonnée bancaire dans Git. Les valeurs réelles appartiennent uniquement à l'environnement Coolify.

### Domaine

Exemple si `www.nettoyageexpresse.fr` est l'origine canonique :

```env
SITE_URL=https://www.nettoyageexpresse.fr
ALLOWED_HOSTS=nettoyageexpresse.fr
CSRF_TRUSTED_ORIGINS=https://nettoyageexpresse.fr
```

`SITE_URL` doit être une origine HTTPS, sans chemin, query string ou identifiants. Ne pas utiliser `*` dans `ALLOWED_HOSTS`.

## 6. Stockage persistant

Le système distingue volontairement médias publics et documents privés.

Pour l'application Web, créer deux volumes persistants distincts :

| Destination conteneur | Usage |
| --- | --- |
| `/app/media` | médias publics locaux si Cloudinary n'est pas utilisé |
| `/app/private_media` | devis, factures et autres documents privés |

Les volumes doivent être inscriptibles par l'utilisateur du conteneur, UID `10001`.

Ne pas monter `private_media` sous `/app/media` et ne jamais exposer `/app/private_media` directement via le proxy. Les téléchargements privés passent par les contrôles d'autorisation Django.

Ne pas partager un volume entre le web et le worker par défaut. Le worker actuel n'a pas besoin d'écrire les FileField privés ; si un futur traitement asynchrone le nécessite, choisir un stockage partagé approprié et auditer explicitement les accès concurrents.

Un volume persistant n'est pas une sauvegarde. Dans Coolify, créer un **Scheduled Backup** du volume `/app/private_media` vers un stockage S3-compatible validé et conserver au moins une copie hors du VPS. Tester la restauration de cette archive dans un environnement séparé : la page de sauvegarde de stockage crée l'archive mais ne constitue pas, à elle seule, une procédure de restauration testée.

Si les médias publics restent en stockage local, sauvegarder également `/app/media`. Si Cloudinary est utilisé pour ces médias, ne pas dupliquer inutilement cette sauvegarde locale.

## 7. Santé des conteneurs

Le Dockerfile fournit son propre `HEALTHCHECK` :

- web : `GET /readyz/`, qui vérifie PostgreSQL et Redis ;
- worker : `celery inspect ping` ciblé sur le worker courant.

`/healthz/` reste un endpoint de liveness Django sans accès à PostgreSQL ni Redis.

Le `HEALTHCHECK` du Dockerfile est la source de vérité. Éviter de créer un second healthcheck contradictoire dans l'interface Coolify.

## 8. PostgreSQL

La production refuse SQLite. `DATABASE_URL` doit pointer vers PostgreSQL sur le réseau privé Coolify.

Avant mise en ligne :

- conserver le volume PostgreSQL par défaut de Coolify ;
- créer une sauvegarde planifiée PostgreSQL ;
- envoyer une copie vers un stockage S3-compatible hors du VPS ;
- définir une rétention locale et distante ;
- déclencher un « Backup Now » avant la bascule ;
- effectuer au moins une restauration de test dans une base jetable ;
- conserver les identifiants PostgreSQL hors Git ;
- ne pas exposer le port PostgreSQL publiquement sans nécessité.

## 9. Redis

`REDIS_URL` est obligatoire car Redis sert simultanément :

- le cache Django ;
- le broker Celery ;
- le backend de résultat Celery.

Utiliser la ressource Redis Coolify avec son stockage persistant `/data` et ne pas publier son port sur Internet. Le workflow de sauvegarde « base de données » de Coolify ne couvre pas Redis ; PostgreSQL et les documents privés restent les sources à sauvegarder impérativement. Redis doit toutefois conserver sa persistance afin qu'un simple remplacement de conteneur n'efface pas systématiquement les tâches en attente.

`/readyz/` renvoie `503` si Redis ou PostgreSQL n'est pas disponible : le web ne doit pas être considéré comme prêt dans cet état.

## 10. Factures et coordonnées bancaires

Les nouvelles factures utilisent le template `pdf/invoice_premium.html`. Le bloc de règlement affiche, lorsqu'ils sont configurés :

- titulaire du compte ;
- IBAN ;
- BIC.

En production, le titulaire et l'IBAN sont obligatoires. Ainsi, NetExpress ne peut pas démarrer avec une configuration qui produirait de nouvelles factures sans coordonnées de règlement.

Les PDF historiques déjà émis restent immuables : une migration de production ne doit pas régénérer silencieusement une facture ancienne.

## 11. Contrôle avant bascule DNS

Le déploiement n'est considéré prêt que lorsque les vérifications suivantes sont réalisées sur la vraie instance :

- `/healthz/` retourne HTTP 200 ;
- `/readyz/` retourne HTTP 200 ;
- l'application est servie en HTTPS sur le domaine final ;
- connexion administrateur fonctionnelle ;
- création d'un devis test ;
- conversion en facture test ;
- contrôle visuel du PDF : identité, SIRET, montants, titulaire, IBAN et BIC éventuel ;
- téléchargement privé impossible sans autorisation ;
- envoi de courriel fonctionnel (`python manage.py send_test_email`) ;
- formulaire de contact public : le message arrive bien sur `CONTACT_RECEIVER_EMAIL` ;
- formulaire public protégé par Turnstile ;
- worker Celery sain et traitement d'une tâche réelle dans une file métier ;
- sauvegarde PostgreSQL effectuée puis restauration de test ;
- sauvegarde S3-compatible de `/app/private_media` effectuée puis restauration de test ;
- aucun secret présent dans les logs ou le dépôt.

## 12. Bascule depuis Render

`for_prod` ne doit plus dépendre d'un domaine `onrender.com`, d'une variable propre à Render ni de `render.yaml`.

Procédure de bascule :

1. déployer et valider l'instance Coolify sans modifier le DNS public ;
2. restaurer/importer la base et les documents privés nécessaires ;
3. exécuter les contrôles de la section précédente ;
4. changer le DNS vers l'OVH/Coolify ;
5. vérifier le certificat TLS, les redirections et les formulaires ;
6. conserver l'ancienne instance uniquement pendant la fenêtre de retour arrière définie ;
7. supprimer les anciens secrets Render après validation définitive.
