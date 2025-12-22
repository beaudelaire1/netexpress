# 🏢 NetExpress - Mini ERP pour Services

**Application Django professionnelle de gestion commerciale (Devis, Factures, Contact, Tâches)**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-3.2%20LTS-green.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

---

## 📋 Table des matières

- [Fonctionnalités](#-fonctionnalités)
- [Installation](#-installation)
- [Configuration](#️-configuration)
- [Utilisation](#-utilisation)
- [Déploiement Production](#-déploiement-production)
- [Architecture](#️-architecture)
- [Sécurité](#-sécurité)
- [Support](#-support)

---

## ✨ Fonctionnalités

### 💼 Gestion Commerciale
- ✅ **Devis** : Création, modification, envoi PDF par email
- ✅ **Factures** : Génération automatique depuis devis, numérotation séquentielle
- ✅ **Clients** : Base de données clients avec historique
- ✅ **Services** : Catalogue de services avec catégories

### 📧 Communication
- ✅ **Formulaire de contact** : Capture leads avec géolocalisation Guyane
- ✅ **Emails HTML** : Templates brandés professionnels
- ✅ **Notifications** : Emails asynchrones (Celery)

### 📊 Gestion Interne
- ✅ **Tâches** : Planification et suivi avec statuts
- ✅ **Dashboard** : Vue d'ensemble KPIs (tâches, factures, devis)
- ✅ **Historique** : Traçabilité complète des actions

### 🎨 Interface
- ✅ **Design moderne** : UI responsive (mobile-first)
- ✅ **Admin Jazzmin** : Interface d'administration intuitive
- ✅ **Accessibilité** : Labels ARIA, navigation clavier

### 📄 PDF Professionnel
- ✅ **Devis PDF** : Génération avec ReportLab
- ✅ **Factures PDF** : Génération avec WeasyPrint
- ✅ **Branding** : Logo, coordonnées, mentions légales

---

## 🚀 Installation

### Prérequis

- **Python 3.11+**
- **PostgreSQL 14+** (production)
- **Redis 6+** (tâches asynchrones)
- **Git**

### Installation locale (développement)

```bash
# 1. Cloner le repository
git clone https://github.com/votre-org/netexpress.git
cd netexpress/src/src_netexpress

# 2. Créer environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 3. Installer dépendances
pip install -r requirements/dev.txt

# 4. Configurer variables d'environnement
cp ../../.env.example .env
# Éditer .env avec vos paramètres

# 5. Créer base de données
python manage.py migrate

# 6. Créer superutilisateur
python manage.py createsuperuser

# 7. Collecter fichiers statiques
python manage.py collectstatic --noinput

# 8. Lancer serveur développement
python manage.py runserver
```

**🎉 Application accessible sur:** `http://localhost:8000`
**🔑 Admin accessible sur:** `http://localhost:8000/gestion/`

---

## ⚙️ Configuration

### Variables d'environnement (.env)

Copier `.env.example` vers `.env` et configurer:

```bash
# Django
DJANGO_SECRET_KEY=votre-clef-secrete-50-caracteres-minimum
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Base de données (PostgreSQL recommandé)
DATABASE_URL=postgresql://user:password@localhost:5432/netexpress

# Email SMTP
EMAIL_HOST=smtp.example.com
EMAIL_HOST_USER=contact@votre-domaine.com
EMAIL_HOST_PASSWORD=votre-mot-de-passe

# Celery / Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_TASK_ALWAYS_EAGER=True  # False en production

# Site
SITE_URL=http://localhost:8000
```

### Celery Workers (tâches asynchrones)

```bash
# Terminal 1: Lancer worker
celery -A netexpress worker -l info

# Terminal 2: Lancer beat (tâches programmées)
celery -A netexpress beat -l info

# Optionnel: Flower (monitoring Celery)
celery -A netexpress flower
# Accès: http://localhost:5555
```

### Redis (si pas installé)

```bash
# MacOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:alpine
```

---

## 💻 Utilisation

### Interface Publique

- **Accueil:** `/` - Page d'accueil avec services
- **Services:** `/services/` - Catalogue de services
- **Contact:** `/contact/` - Formulaire de contact
- **Devis:** `/devis/request/` - Demande de devis

### Interface Admin (`/gestion/`)

**Accès:** Compte superuser ou staff

#### Créer un devis

1. Admin → Devis → Demandes de devis
2. Sélectionner une demande
3. Cliquer "Créer devis"
4. Ajouter lignes de prestation
5. Statut = "Envoyé" → Génération PDF + email automatique

#### Convertir devis en facture

1. Admin → Devis → Devis
2. Sélectionner devis validé
3. Action → "Convertir en facture"
4. Facture créée automatiquement

#### Dashboard

- **URL:** `/dashboard/`
- **KPIs:** Tâches, Factures, Devis, Messages
- **Filtrage:** Par date, statut
- **Actions rapides:** Voir, Éditer, PDF

### API REST (si activée)

```bash
# Exemple: Lister devis
curl -H "Authorization: Token YOUR_TOKEN" \
     http://localhost:8000/api/quotes/

# Créer contact
curl -X POST http://localhost:8000/api/contact/ \
     -H "Content-Type: application/json" \
     -d '{"full_name": "Test", "email": "test@example.com", ...}'
```

---

## 🌐 Déploiement Production

### Checklist pré-déploiement

- [ ] `.env` configuré avec credentials production
- [ ] `DJANGO_DEBUG=False`
- [ ] `DATABASE_URL` PostgreSQL configuré
- [ ] `ALLOWED_HOSTS` configuré
- [ ] `SECRET_KEY` unique et sécurisée (50+ caractères)
- [ ] Certificat SSL/TLS actif
- [ ] Redis configuré
- [ ] Celery workers lancés
- [ ] Collectstatic exécuté
- [ ] Migrations appliquées

### Déploiement Render.com (recommandé)

```bash
# 1. Créer compte Render.com

# 2. Créer PostgreSQL database
# Copier DATABASE_URL

# 3. Créer Redis instance
# Copier REDIS_URL

# 4. Créer Web Service
Build Command: pip install -r requirements/prod.txt && python manage.py collectstatic --noinput && python manage.py migrate
Start Command: gunicorn netexpress.wsgi:application

# 5. Configurer variables d'environnement
DJANGO_SETTINGS_MODULE=netexpress.settings.prod
DJANGO_SECRET_KEY=...
DATABASE_URL=...
CELERY_BROKER_URL=...
# (voir .env.example pour toutes les variables)

# 6. Créer Background Worker (Celery)
Start Command: celery -A netexpress worker -l info
```

### Déploiement Docker (optionnel)

```dockerfile
# Créer Dockerfile (exemple simple)
FROM python:3.11-slim
WORKDIR /app
COPY requirements/prod.txt .
RUN pip install -r prod.txt
COPY . .
CMD gunicorn netexpress.wsgi:application --bind 0.0.0.0:8000
```

```bash
# Build
docker build -t netexpress .

# Run
docker run -p 8000:8000 --env-file .env netexpress
```

### Commandes Post-Déploiement

```bash
# Vérifier configuration
python manage.py check --deploy

# Créer superuser
python manage.py createsuperuser

# Collecter fichiers statiques
python manage.py collectstatic --no-input

# Appliquer migrations
python manage.py migrate
```

---

## 🏗️ Architecture

### Structure du projet

```
netexpress/
├── src/src_netexpress/
│   ├── contact/           # App formulaire contact
│   ├── core/              # Services partagés (email, PDF)
│   ├── devis/             # Gestion devis
│   ├── factures/          # Gestion factures
│   ├── services/          # Catalogue services
│   ├── tasks/             # Gestion tâches
│   ├── messaging/         # Historique emails
│   ├── netexpress/        # Configuration projet
│   │   └── settings/
│   │       ├── base.py    # Settings communs
│   │       ├── dev.py     # Settings développement
│   │       └── prod.py    # Settings production
│   ├── templates/         # Templates HTML
│   ├── static/            # CSS, JS, images
│   └── requirements/      # Dépendances
│       ├── base.txt       # Dépendances communes
│       ├── dev.txt        # Outils développement
│       └── prod.txt       # Outils production
├── .env.example           # Variables d'environnement
├── README.md              # Ce fichier
└── AUDIT_TECHNIQUE_COMPLET.md  # Audit détaillé
```

### Technologies

| Composant | Technologie |
|-----------|-------------|
| **Framework** | Django 3.2 LTS |
| **Base de données** | PostgreSQL 14+ |
| **Cache/Queue** | Redis 6+ |
| **Tâches async** | Celery 5.3+ |
| **PDF** | WeasyPrint + ReportLab |
| **Serveur Web** | Gunicorn + Uvicorn |
| **Frontend** | HTML/CSS/JS vanilla |
| **Admin UI** | Jazzmin |

---

## 🔒 Sécurité

### Mesures implémentées

✅ **HTTPS forcé** - `SECURE_SSL_REDIRECT=True`
✅ **HSTS** - 1 an (headers HTTPS strict)
✅ **Cookies sécurisés** - HttpOnly, Secure, SameSite
✅ **Protection CSRF** - Tokens anti-CSRF
✅ **Protection XSS** - Auto-escaping templates
✅ **Protection Clickjacking** - X-Frame-Options: DENY
✅ **Fichiers media protégés** - Auth requise pour PDF
✅ **Validations** - SECRET_KEY, ALLOWED_HOSTS, DB
✅ **Logging** - Toutes erreurs loggées

### Fichiers sensibles protégés

- **PDF Devis/Factures** : Accessible uniquement aux staff (login requis)
- **Admin** : URL custom `/gestion/` (pas `/admin/`)
- **Media files** : Protection path traversal

### Bonnes pratiques

🔐 **JAMAIS** commiter `.env` dans Git
🔐 **Changer** `SECRET_KEY` par environnement
🔐 **Utiliser** PostgreSQL en production (pas SQLite)
🔐 **Activer** Sentry pour monitoring erreurs
🔐 **Configurer** backups DB automatiques

---

## 📚 Documentation

- **Audit complet:** `AUDIT_TECHNIQUE_COMPLET.md`
- **Configuration production:** `netexpress/settings/prod.py`
- **Variables d'environnement:** `.env.example`
- **Tests:** `pytest --cov` (voir `requirements/dev.txt`)

---

## 🧪 Tests

```bash
# Lancer tous les tests
pytest

# Tests avec couverture
pytest --cov=src_netexpress --cov-report=html

# Tests spécifiques
pytest tests/test_models.py
pytest tests/test_views.py -v
```

---

## 🛠️ Troubleshooting

### Erreur "SECRET_KEY too short"
➡️ Générer nouvelle clé: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`

### Erreur "ALLOWED_HOSTS must be set"
➡️ Configurer dans `.env`: `DJANGO_ALLOWED_HOSTS=votre-domaine.com,www.votre-domaine.com`

### Emails non envoyés
➡️ Vérifier `.env`: `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
➡️ En dev: emails affichés console si `DEBUG=True`

### Celery tasks bloquées
➡️ Vérifier Redis: `redis-cli ping` → doit retourner `PONG`
➡️ Lancer worker: `celery -A netexpress worker -l info`

### PDF non générés
➡️ Vérifier WeasyPrint installé: `pip install weasyprint`
➡️ Ubuntu: `sudo apt install libpango-1.0-0 libpangoft2-1.0-0`

---

## 📞 Support

- **Issues:** Créer une issue GitHub
- **Email:** contact@nettoyage-express.gf
- **Documentation:** Voir `AUDIT_TECHNIQUE_COMPLET.md`

---

## 📝 Changelog

### Version 1.0.0 (2025-01-XX)

**✨ Fonctionnalités:**
- Gestion devis/factures complète
- Génération PDF professionnelle
- Emails HTML brandés
- Dashboard KPIs
- Protection fichiers media

**🔒 Sécurité:**
- HTTPS forcé
- HSTS 1 an
- Cookies sécurisés
- Validations production
- Logging complet

**🚀 Performance:**
- Celery tasks asynchrones
- Connection pooling PostgreSQL
- Cache Redis
- WhiteNoise compression

---

## 📄 License

**Proprietary** - © 2025 Nettoyage Express. Tous droits réservés.

---

**Développé avec ❤️ pour Nettoyage Express - Guyane française 🇬🇫**
