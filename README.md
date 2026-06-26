# Nettoyage Express

Site vitrine et plateforme métier (devis, factures, portails client/ouvrier/admin)
pour **Nettoyage Express** — entretien, espaces verts, peinture et bricolage en Guyane.

Application **Django 5.2** déployée sur **Render** (Docker), médias sur **Cloudinary**,
emails transactionnels via **Brevo**, tâches asynchrones via **Celery/Redis**.

## Stack

- Python 3.11 / Django 5.2
- PostgreSQL (prod) · SQLite (dev/test)
- WhiteNoise (statiques) · Cloudinary (médias)
- Celery + Redis (asynchrone, optionnel)
- Brevo API (emails) · Cloudflare Turnstile (anti-bot) · django-axes (anti-brute-force)
- Jazzmin (admin) · TinyMCE (éditeur)

## Structure du dépôt

```
src/src_netexpress/
├── netexpress/          # Projet Django (settings/, urls.py, wsgi.py, celery.py)
│   └── settings/        # base.py, dev.py, local.py, prod.py, test.py
├── core/                # Pages publiques, portails, middlewares, services
├── services/            # Catalogue de prestations
├── devis/               # Demandes de devis et génération PDF
├── factures/            # Facturation
├── contact/             # Formulaire de contact
├── tasks/               # Planification / interventions
├── messaging/           # Messagerie interne et emails
├── accounts/            # Comptes, profils, contrôle d'accès par rôle
├── templates/           # Gabarits HTML (base.html, base_v2.html, …)
├── static/              # CSS / JS / images
├── tests/               # Suite de tests (pytest/Django)
└── requirements/        # base.txt, dev.txt, prod.txt
docs/                    # ARCHITECTURE.md, manuel utilisateur, UX/UI
render.yaml              # Configuration de déploiement Render
```

## Démarrage local

```bash
cd src/src_netexpress
python -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt

export DJANGO_SETTINGS_MODULE=netexpress.settings.dev
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Le site est servi sur http://127.0.0.1:8000/ — l'administration sur `/gestion/`.

## Variables d'environnement (prod)

Définies dans le dashboard Render (cf. `render.yaml`) :

| Variable | Rôle |
|---|---|
| `DJANGO_SECRET_KEY` | Clé secrète Django (**obligatoire**) |
| `DATABASE_URL` | URL PostgreSQL |
| `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | Hôtes / origines autorisés |
| `BREVO_API_KEY` | Envoi d'emails (clé `xkeysib-…`) |
| `CLOUDINARY_CLOUD_NAME` / `_API_KEY` / `_API_SECRET` | Stockage médias |
| `REDIS_URL` | Broker Celery + cache (optionnel) |
| `TURNSTILE_SITE_KEY` / `TURNSTILE_SECRET_KEY` | Anti-bot des formulaires |

> Sans `TURNSTILE_SECRET_KEY`, la vérification anti-bot est désactivée (« fail-open »).
> Sans `CLOUDINARY_*`, les médias sont stockés localement et **perdus** à chaque redéploiement.

## Tests

```bash
cd src/src_netexpress
python manage.py test --settings=netexpress.settings.test
```

## Sécurité (prod)

`netexpress.settings.prod` active : `DEBUG=False`, HSTS (1 an, preload), redirection
HTTPS, cookies `Secure`, `X-Content-Type-Options`, `X-Frame-Options: DENY`,
`Referrer-Policy`. Le middleware `core.middleware.security_headers` ajoute une
`Content-Security-Policy` et une `Permissions-Policy` (surcouchables via les réglages
`CONTENT_SECURITY_POLICY` / `PERMISSIONS_POLICY`).

## Pages légales

Mentions légales (`/mentions-legales/`) et politique de confidentialité
(`/politique-de-confidentialite/`). Les informations de la société (forme juridique
SARL, SIRET, TVA, capital social, RCS, gérant) proviennent de `INVOICE_BRANDING`
dans `netexpress/settings/base.py` — source unique partagée avec les devis et
factures. Renseigner `capital` et `manager` avec les valeurs réelles : laissés vides,
les champs correspondants ne s'affichent pas (le numéro RCS est dérivé du SIRET).
