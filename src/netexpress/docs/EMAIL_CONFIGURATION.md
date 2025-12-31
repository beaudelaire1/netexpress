# Configuration Email pour NetExpress

Ce document explique comment configurer l'envoi d'emails dans l'application NetExpress.

## Deux Options Disponibles

L'application supporte deux méthodes d'envoi d'emails :

### 1. SMTP (Gmail, Zoho, etc.) - **Recommandé pour débuter**

Configuration classique via un serveur SMTP. Idéal pour Gmail, Zoho Mail ou tout autre fournisseur SMTP.

**Variables d'environnement requises :**

```bash
EMAIL_BACKEND_TYPE=smtp          # ou laissez vide (smtp par défaut)
EMAIL_HOST=smtp.gmail.com        # Serveur SMTP
EMAIL_PORT=465                   # Port (465 pour SSL, 587 pour TLS)
EMAIL_USE_SSL=True              # True pour port 465, False pour 587
EMAIL_USE_TLS=False             # False pour port 465, True pour 587
EMAIL_HOST_USER=votre@email.com  # Votre adresse email
EMAIL_HOST_PASSWORD=xxxx         # Mot de passe d'application
DEFAULT_FROM_EMAIL=votre@email.com
```

**Pour Gmail :** Vous devez créer un "Mot de passe d'application" :
1. Allez sur https://myaccount.google.com/security
2. Activez la validation en deux étapes
3. Créez un mot de passe d'application
4. Utilisez ce mot de passe (sans espaces) comme `EMAIL_HOST_PASSWORD`

### 2. Brevo API (ancien Sendinblue) - **Recommandé pour production**

API REST moderne, plus fiable et avec des statistiques détaillées.

**Variables d'environnement requises :**

```bash
EMAIL_BACKEND_TYPE=brevo
BREVO_API_KEY=votre-cle-api-brevo
DEFAULT_FROM_EMAIL=votre@email.com
```

**Pour obtenir votre clé API Brevo :**
1. Créez un compte sur https://www.brevo.com (gratuit jusqu'à 300 emails/jour)
2. Allez dans "Settings" > "SMTP & API" > "API Keys"
3. Créez une nouvelle clé API v3
4. Copiez la clé et ajoutez-la comme variable d'environnement `BREVO_API_KEY`

## Résolution des Erreurs

### Erreur : "Erreur API Brevo (status 401): Unauthorized - Key not found"

Cette erreur signifie que :
- Vous avez configuré `EMAIL_BACKEND_TYPE=brevo`
- Mais la variable `BREVO_API_KEY` est manquante ou invalide

**Solution :**
1. Vérifiez que `BREVO_API_KEY` est bien définie dans vos variables d'environnement
2. Vérifiez que la clé API est valide sur https://app.brevo.com/settings/keys/api
3. Ou revenez au mode SMTP en définissant `EMAIL_BACKEND_TYPE=smtp`

### Erreur : "Échec de l'envoi de l'e‑mail" (SMTP)

**Solutions possibles :**
1. Vérifiez que `EMAIL_HOST_PASSWORD` est correctement défini
2. Pour Gmail, utilisez un mot de passe d'application (pas votre mot de passe normal)
3. Vérifiez que les ports et SSL/TLS sont corrects :
   - Port 465 → `EMAIL_USE_SSL=True` et `EMAIL_USE_TLS=False`
   - Port 587 → `EMAIL_USE_SSL=False` et `EMAIL_USE_TLS=True`

## Configuration sur Render.com

Pour configurer les variables d'environnement sur Render :

1. Allez dans votre dashboard Render
2. Sélectionnez votre service
3. Allez dans "Environment"
4. Ajoutez les variables nécessaires selon la méthode choisie

**Important :** Les variables d'environnement définies sur Render remplacent celles du fichier `.env`.

## Test de Configuration

Pour tester votre configuration email, vous avez deux options :

### Option 1 : Commande personnalisée (Recommandée)

Utilisez la commande de test personnalisée qui affiche des informations détaillées :

```bash
# Activez votre environnement virtuel
source venv/bin/activate  # ou .venv\Scripts\activate sur Windows

# Testez avec votre email
python manage.py test_email_config votre@email.com
```

Cette commande affiche :
- La configuration email actuelle (SMTP ou Brevo)
- Le statut de chaque paramètre (✓ ou ✗)
- Des suggestions si l'envoi échoue

### Option 2 : Commande Django standard

Vous pouvez aussi utiliser la commande Django intégrée :

```bash
python manage.py sendtestemail votre@email.com
```

Si vous recevez l'email, votre configuration fonctionne ! ✅

## Recommandations

- **Développement local** : Utilisez SMTP avec Gmail (plus simple à configurer)
- **Production** : Utilisez Brevo API (plus fiable, avec statistiques)
- **Ne commitez jamais** vos clés API ou mots de passe dans Git
- Utilisez toujours des variables d'environnement pour les secrets
