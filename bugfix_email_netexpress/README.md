# NetExpress ERP – Version 2.2

Bienvenue dans la version 2.2 de **NetExpress**, l’ERP destiné à la société de
nettoyage.  Cette mise à jour fournit une base de code prête pour le
déploiement en production, sécurisée et simplifiée.  Les principales
améliorations incluent :

- **Un modèle unifié de client** via l’application `crm`.  Le nouveau
  modèle `crm.Customer` centralise toutes les informations relatives aux
  clients et remplace l’ancien `devis.Client`.  Pour conserver la
  compatibilité, `devis.Client` est désormais un alias pointant vers
  `crm.Customer`.
- **Suppression de la couche hexagonale** et du dépôt `django_orm`.
  Les factures sont créées via la fonction
  `devis.services.create_invoice_from_quote` et les méthodes fournies
  par les modèles.  Le code est plus lisible et plus simple à
  maintenir.
- **Génération de PDF avec WeasyPrint** pour les devis et les
  factures.  Aucune dépendance à ReportLab n’est nécessaire.
- **Séparation stricte des secrets**.  Les variables sensibles
  (clé Secrète Django, identifiants SMTP, URL de la base de données)
  sont lues depuis l’environnement.  Le fichier `.env` n’est pas
  commité et doit être créé dans votre environnement d’exécution.
- **Déploiement sur Render** facilité via un `Dockerfile` et un
  fichier `render.yaml`.  L’image Docker installe les dépendances
  système (cairo, pango, gdk-pixbuf) nécessaires à WeasyPrint.

## Installation locale

1. **Cloner le dépôt** puis installez les dépendances :

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements/prod.txt
   ```

2. **Créer et configurer votre fichier `.env`** à la racine du projet
   (ou exporter les variables dans votre shell).  Exemple :

   ```env
   DJANGO_SECRET_KEY=change-me
   DATABASE_URL=postgres://user:password@localhost:5432/netexpress
   ALLOWED_HOSTS=localhost,127.0.0.1
   CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1
   EMAIL_HOST=mail.infomaniak.com
   EMAIL_PORT=465
   EMAIL_USE_SSL=True
   EMAIL_HOST_USER=adresse@example.com
   EMAIL_HOST_PASSWORD=motdepasse
   DEFAULT_FROM_EMAIL=adresse@example.com
   ```

3. **Exécuter les migrations et lancer le serveur** :

   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py runserver
   ```

## Déploiement sur Render

Le fichier `render.yaml` configure un service web de type Docker.  Lors
de la création du service dans l’interface Render :

1. Sélectionnez « Docker » comme environnement.  Render détectera le
   `Dockerfile` à la racine de `src_netexpress`.
2. Ajoutez les variables d’environnement nécessaires dans l’onglet
   « Environment » (voir l’exemple ci-dessus).  **N’exposez jamais la
   clé secrète ou les mots de passe SMTP dans votre dépôt !**
3. Reliez un service de base de données PostgreSQL et référez-vous à
   l’URL fournie via la variable `DATABASE_URL`.

Une fois déployé, Render exécutera automatiquement `collectstatic` et
lancera Gunicorn pour servir l’application.  Le port est configuré
via la variable `PORT` que Render fournit implicitement.

## Variables d’environnement indispensables

- `DJANGO_SECRET_KEY` : clé secrète utilisée par Django en production.
- `DATABASE_URL` : URL PostgreSQL complète (format
  `postgres://user:password@host:port/dbname`).
- `ALLOWED_HOSTS` : liste des hôtes autorisés séparés par des virgules.
- `CSRF_TRUSTED_ORIGINS` : origines autorisées pour les requêtes CSRF.
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_SSL`, `EMAIL_HOST_USER`,
  `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` : paramètres SMTP.

## Nettoyage des dépendances obsolètes

Cette version ne dépend plus de ReportLab.  Tous les PDF sont générés
via WeasyPrint et un CSS moderne.  Assurez-vous que les paquets
`reportlab` ou `svglib` sont désinstallés pour éviter des
confusions.

## Contribution

Avant toute contribution, vérifiez que les tests s’exécutent sans
erreur :

```bash
pytest
```

Les nouvelles fonctionnalités doivent inclure des tests unitaires et
respecter la ligne directrice de simplicité introduite dans cette version.