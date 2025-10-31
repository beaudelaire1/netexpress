services:
  - type: web
    name: netexpress
    env: python
    rootDir: src/netexpress
    buildCommand: |
      pip install --upgrade pip
      pip install -r requirements/prod.txt
      python manage.py collectstatic --noinput
      python manage.py migrate
    startCommand: gunicorn netexpress.wsgi:application
    

    envVars:
      # Django settings
      - key: DJANGO_SETTINGS_MODULE
        value: netexpress.settings.base
      - key: DJANGO_SECRET_KEY
        generateValue: true
      - key: DEBUG
        value: "False"
      - key: ALLOWED_HOSTS
        value: "nettoyage-express.fr,www.nettoyage-express.fr,localhost,127.0.0.1"

      # WhiteNoise (serve static files)
      - key: STATIC_ROOT
        value: /opt/render/project/src/src/netexpress/staticfiles
      - key: STATIC_URL
        value: /static/
      - key: MEDIA_ROOT
        value: /opt/render/project/src/src/netexpress/media
      - key: MEDIA_URL
        value: /media/

      # Email config (ex: Zoho)
      - key: EMAIL_HOST
        value: smtp.zoho.com
      - key: EMAIL_PORT
        value: "587"
      - key: EMAIL_USE_TLS
        value: "true"
      - key: EMAIL_HOST_USER
        value: noreply@nettoyage-express.fr
      - key: EMAIL_HOST_PASSWORD
        sync: false  # tu le rempliras manuellement sur Render
      - key: DEFAULT_FROM_EMAIL
        value: noreply@nettoyage-express.fr

      # Base de données (Render PostgreSQL)
      - key: DATABASE_URL
        fromDatabase:
          name: netexpress-db
          property: connectionString

databases:
  - name: netexpress-db
    plan: free
