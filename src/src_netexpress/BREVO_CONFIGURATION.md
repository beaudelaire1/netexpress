# Configuration Brevo pour NetExpress

## Vue d'ensemble

NetExpress utilise maintenant **Brevo** (ex-Sendinblue) pour l'envoi d'emails transactionnels via leur API REST. Cette configuration remplace l'ancien système SMTP pour une meilleure fiabilité et des fonctionnalités avancées.

## Configuration

### Variables d'environnement

```bash
# Backend email personnalisé
EMAIL_BACKEND=core.backends.brevo_backend.BrevoEmailBackend

# Clé API Brevo
BREVO_API_KEY=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

# Configuration de l'expéditeur
DEFAULT_FROM_EMAIL=contact@nettoyageexpresse.fr
DEFAULT_FROM_NAME=Nettoyage Express
```

### Fichiers modifiés

- **Backend personnalisé** : `core/backends/brevo_backend.py`
- **Configuration dev** : `netexpress/settings/dev.py`
- **Variables locales** : `.env.local`
- **Variables production** : `.env`

## Fonctionnalités

### ✅ Emails transactionnels
- Notifications de contact
- Envoi automatique de devis avec PDF
- Messages système
- Invitations utilisateurs

### ✅ Support des formats
- **Texte brut** : Messages simples
- **HTML** : Templates avec mise en forme
- **Pièces jointes** : PDFs, documents

### ✅ Gestion des erreurs
- Logs détaillés des envois
- Gestion des échecs d'API
- Mode `fail_silently` configurable

## Utilisation

### Envoi simple
```python
from django.core.mail import send_mail

send_mail(
    subject='Sujet du message',
    message='Contenu texte',
    from_email='contact@nettoyageexpresse.fr',
    recipient_list=['client@example.com'],
)
```

### Envoi HTML avec pièce jointe
```python
from django.core.mail import EmailMultiAlternatives

msg = EmailMultiAlternatives(
    subject='Votre devis',
    body='Version texte',
    from_email='contact@nettoyageexpresse.fr',
    to=['client@example.com']
)
msg.attach_alternative('<h1>Version HTML</h1>', "text/html")
msg.attach_file('/path/to/devis.pdf')
msg.send()
```

## Avantages de Brevo

### 🚀 Performance
- API REST rapide et fiable
- Pas de limitations SMTP
- Meilleure délivrabilité

### 📊 Suivi
- Statistiques d'envoi
- Tracking des ouvertures
- Gestion des bounces

### 🔒 Sécurité
- Authentification par clé API
- Chiffrement des communications
- Conformité RGPD

## Monitoring

### Logs
Les envois sont loggés dans le système Django :
```
INFO core.backends.brevo_backend Email envoyé via Brevo: <message_id>
```

### Erreurs
Les erreurs API sont capturées et loggées :
```
ERROR core.backends.brevo_backend Erreur API Brevo: [détails]
```

## Fallback

En cas de problème avec Brevo, il est possible de revenir temporairement au backend console :
```bash
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

## Tests

Pour tester la configuration :
```bash
python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail('Test', 'Message test', 'contact@nettoyageexpresse.fr', ['test@example.com'])
```

## Support

- **Documentation Brevo** : https://developers.brevo.com/
- **API Reference** : https://developers.brevo.com/reference/sendtransacemail
- **Dashboard Brevo** : https://app.brevo.com/

---

**Note** : La clé API Brevo est sensible et ne doit jamais être commitée dans le code source. Elle est stockée dans les variables d'environnement.