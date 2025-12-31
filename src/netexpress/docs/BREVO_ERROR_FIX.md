# Fix pour l'Erreur Brevo 401

## Problème
Vous rencontriez l'erreur suivante :
```
Erreur lors de l'envoi de l'email : Erreur lors de l'envoi de l'email via Brevo: 
Erreur API Brevo (status 401): Unauthorized - Key not found
```

## Cause
Cette erreur se produit lorsque :
1. L'environnement de production est configuré pour utiliser l'API Brevo
2. Mais la clé API Brevo (`BREVO_API_KEY`) n'est pas définie ou est invalide

## Solution

### Méthode 1 : Utiliser Brevo API (Recommandé pour production)

1. Créez un compte Brevo gratuit sur https://www.brevo.com
2. Allez dans "Settings" > "SMTP & API" > "API Keys"
3. Créez une nouvelle clé API v3
4. Dans votre environnement de déploiement (Render.com, etc.), ajoutez ces variables :
   ```bash
   EMAIL_BACKEND_TYPE=brevo
   BREVO_API_KEY=votre-cle-api-ici
   DEFAULT_FROM_EMAIL=votre@email.com
   ```

### Méthode 2 : Utiliser SMTP (Gmail, Zoho, etc.)

Si vous préférez utiliser un serveur SMTP classique :

1. Dans votre environnement de déploiement, définissez :
   ```bash
   EMAIL_BACKEND_TYPE=smtp
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=465
   EMAIL_USE_SSL=True
   EMAIL_HOST_USER=votre@email.com
   EMAIL_HOST_PASSWORD=votre-mot-de-passe-app
   DEFAULT_FROM_EMAIL=votre@email.com
   ```

2. Pour Gmail, créez un mot de passe d'application :
   - https://myaccount.google.com/security
   - Activez la validation en 2 étapes
   - Créez un mot de passe d'application

## Tester la Configuration

Après avoir configuré vos variables d'environnement :

```bash
python manage.py test_email_config votre@email.com
```

Cette commande :
- ✓ Affiche votre configuration actuelle
- ✓ Indique les problèmes éventuels
- ✓ Envoie un email de test
- ✓ Fournit des suggestions si ça ne fonctionne pas

## Documentation Complète

Consultez `docs/EMAIL_CONFIGURATION.md` pour des instructions détaillées.

## Changements Apportés

1. ✅ Ajout du support pour l'API Brevo via `django-anymail`
2. ✅ Configuration flexible SMTP ou Brevo via `EMAIL_BACKEND_TYPE`
3. ✅ Avertissements clairs quand des clés sont manquantes
4. ✅ Commande `test_email_config` pour le diagnostic
5. ✅ Documentation complète avec exemples

## Support

Si vous avez encore des problèmes :
1. Vérifiez que toutes les variables d'environnement sont définies
2. Utilisez `python manage.py test_email_config` pour diagnostiquer
3. Consultez les logs d'application pour des détails sur l'erreur
