import os
from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netexpress.settings')

# Définition correcte de la variable application
application = get_wsgi_application()

# Ajout de WhiteNoise après avoir défini application
application = WhiteNoise(application)

