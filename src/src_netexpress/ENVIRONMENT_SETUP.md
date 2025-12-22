# Configuration des Variables d'Environnement

## 🔐 Sécurité des Clés API

**IMPORTANT** : Les clés API et autres informations sensibles ne doivent JAMAIS être commitées dans le repository Git.

## 📋 Variables Requises

### Configuration de Base
```bash
DEBUG=False
DJANGO_SECRET_KEY=your-django-secret-key
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
```

### Base de Données
```bash
# PostgreSQL (Production)
DATABASE_URL=postgresql://user:password@host:port/database

# SQLite (Développement) - laissez vide ou commentez
# DATABASE_URL=
```

### Email Brevo
```bash
EMAIL_BACKEND=core.backends.brevo_backend.BrevoEmailBackend
BREVO_API_KEY=your-brevo-api-key
DEFAULT_FROM_EMAIL=contact@yourdomain.com
DEFAULT_FROM_NAME=Your Company Name
```

## 🚀 Configuration sur Render

1. **Accédez à votre dashboard Render**
2. **Sélectionnez votre service web**
3. **Allez dans "Environment"**
4. **Ajoutez les variables d'environnement** :

| Variable | Valeur | Description |
|----------|--------|-------------|
| `DJANGO_SECRET_KEY` | `your-secret-key` | Clé secrète Django |
| `BREVO_API_KEY` | `xsmtpsib-...` | Clé API Brevo pour les emails |
| `DATABASE_URL` | `postgresql://...` | URL de la base PostgreSQL |
| `ALLOWED_HOSTS` | `yourdomain.com` | Domaines autorisés |

## 🏠 Configuration Locale

1. **Copiez le fichier exemple** :
   ```bash
   cp .env.example .env
   ```

2. **Éditez `.env`** avec vos vraies valeurs :
   ```bash
   # Pour le développement local
   DEBUG=True
   DJANGO_SETTINGS_MODULE=netexpress.settings.dev
   BREVO_API_KEY=your-actual-api-key
   ```

## ⚠️ Bonnes Pratiques

- ✅ Utilisez `.env.example` pour documenter les variables
- ✅ Gardez `.env` dans `.gitignore`
- ✅ Utilisez des clés différentes pour dev/prod
- ✅ Régénérez les clés si elles sont compromises
- ❌ Ne commitez JAMAIS de vraies clés API
- ❌ Ne partagez pas les clés par email/chat

## 🔄 Rotation des Clés

Si une clé API est compromise :

1. **Générez une nouvelle clé** sur Brevo
2. **Mettez à jour la variable d'environnement** sur Render
3. **Redéployez l'application**
4. **Révoqué l'ancienne clé** sur Brevo