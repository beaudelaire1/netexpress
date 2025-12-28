# Configuration Email - Brevo (ex-Sendinblue)

## Objectif

- **En dev**: envoyer de vrais emails via **SMTP Brevo**
- **En prod**: idem (via variables d'environnement)

## Configuration SMTP Brevo (recommandée)

Dans Brevo: **Paramètres → SMTP & API → SMTP**

Tu dois récupérer:
- **Serveur SMTP**: `smtp-relay.brevo.com`
- **Port**: `587`
- **Connexion (login)**: ex `9e61f6001@smtp-brevo.com`
- **Mot de passe SMTP**: la **clé SMTP** (générée dans Brevo)

## Variables d'environnement à définir (local)

Crée/édite `src_netexpress/.env.local`:

```bash
BREVO_SMTP_HOST=smtp-relay.brevo.com
BREVO_SMTP_PORT=587
BREVO_SMTP_USE_TLS=True
BREVO_SMTP_LOGIN=9e61f6001@smtp-brevo.com
BREVO_SMTP_PASSWORD=VOTRE_CLE_SMTP_ICI

DEFAULT_FROM_EMAIL=contact@nettoyageexpresse.fr
DEFAULT_FROM_NAME=Nettoyage Express
```

Important:
- `BREVO_SMTP_PASSWORD` **ne doit pas être une clé API** (API != SMTP)
- `DEFAULT_FROM_EMAIL` doit être une **adresse expéditeur validée** dans Brevo (sender/domain)

## Erreurs courantes

- **`SMTPSenderRefused (502, 5.7.0 Please authenticate first, ...)`**
  - Cause: identifiants SMTP manquants/vides → l'app tente d'envoyer sans auth.
  - Fix: définir **`BREVO_SMTP_LOGIN`** et **`BREVO_SMTP_PASSWORD`**, puis redémarrer le serveur.

- **`535 5.7.8 Authentication failed`**
  - Cause: login/mot de passe SMTP incorrects (clé SMTP révoquée/erronée).
  - Fix: regénérer une **clé SMTP** dans Brevo et mettre à jour `BREVO_SMTP_PASSWORD`.

## Tests rapides

Test SMTP direct:

```bash
python src_netexpress/test_smtp.py
```

Test envoi via Django (utilise `netexpress.settings.dev`):

```bash
python src_netexpress/test_email_console.py
```
