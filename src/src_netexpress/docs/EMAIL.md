# Courrier électronique et notifications

Le site envoie deux familles de messages : les **notifications internes**
(nouveau message de contact, nouvelle facture, tâches) et les **courriels aux
clients** (devis, factures, portail). Tous passent par la même configuration.

## Transport : SMTP standard

Le transport par défaut est `django.core.mail.backends.smtp.EmailBackend`.
Il fonctionne avec le relais de n'importe quel hébergeur de messagerie — Brevo,
OVH, IONOS, Gmail — et ne dépend d'aucune API propriétaire.

| Variable | Rôle | Défaut |
| --- | --- | --- |
| `EMAIL_BACKEND` | Transport | SMTP |
| `EMAIL_HOST` | Serveur du relais | `smtp-relay.brevo.com` |
| `EMAIL_PORT` | Port | `587` |
| `EMAIL_USE_TLS` | STARTTLS (port 587) | `True` |
| `EMAIL_USE_SSL` | SSL implicite (port 465) | `False` |
| `EMAIL_HOST_USER` | Identifiant du relais | — |
| `EMAIL_HOST_PASSWORD` | Mot de passe / clé SMTP | — |
| `EMAIL_TIMEOUT` | Délai maximal d'une connexion, en secondes | `30` |
| `DEFAULT_FROM_EMAIL` | Expéditeur affiché | — |
| `DEFAULT_FROM_NAME` | Nom de l'expéditeur | `Nettoyage Express` |

`EMAIL_USE_TLS` et `EMAIL_USE_SSL` s'excluent : Django refuse les deux à la
fois. Un `EMAIL_USE_SSL=True` explicite désactive automatiquement TLS.

Les anciens noms `BREVO_SMTP_HOST`, `BREVO_SMTP_PORT`, `BREVO_SMTP_LOGIN`,
`BREVO_SMTP_PASSWORD`, `BREVO_SMTP_USE_TLS` et `BREVO_SMTP_USE_SSL` restent
acceptés comme alias, pour ne pas casser un `.env.local` existant.

### Revenir à l'API Brevo

Le backend API reste disponible pour qui en a l'usage :

```bash
EMAIL_BACKEND=core.backends.brevo_backend.BrevoEmailBackend
BREVO_API_KEY=xkeysib-…
```

Aucune variable SMTP n'est alors nécessaire.

## Destinataires des notifications internes

| Variable | Rôle |
| --- | --- |
| `CONTACT_RECEIVER_EMAIL` | Destinataire des messages du formulaire de contact |
| `CONTACT_CC_EMAIL` | Copies, séparées par des virgules |
| `TASK_NOTIFICATION_EMAIL` | Notifications devis, tâches et factures |

Sans `CONTACT_RECEIVER_EMAIL`, la notification de contact retombe sur
`DEFAULT_FROM_EMAIL`, et, à défaut, n'est pas envoyée du tout — l'événement est
alors journalisé en `ERROR`. La production refuse de démarrer si la variable
est absente.

## Envoi synchrone ou par Celery

Les notifications des formulaires publics — contact et demande de devis —
partent **dans le fil de la requête**. Ce sont des messages transactionnels
uniques, et les confier à Celery suppose qu'un worker tourne réellement :
sinon la tâche reste en file et personne n'est jamais prévenu.

`NOTIFY_EMAILS_ASYNC=True` rebascule sur Celery pour les déploiements qui
exploitent bien un worker. Si le courtier est injoignable au moment de la mise
en file, l'envoi se rabat sur le mode synchrone plutôt que de perdre le
message. L'aiguillage est commun aux deux formulaires : `core/notifications.py`.

Dans tous les cas, un échec d'envoi est journalisé mais **n'est jamais
répercuté sur le visiteur** : sa demande est déjà enregistrée en base, il n'a
pas à la ressaisir parce que notre relais est en panne.

## Diagnostic

```bash
python manage.py send_test_email
```

La commande affiche le transport réellement actif — backend, serveur, port,
chiffrement, présence du mot de passe — puis envoie un message de contrôle à
`CONTACT_RECEIVER_EMAIL`. Options : `--to adresse@exemple.fr` pour choisir la
cible, `--dry-run` pour n'afficher que la configuration.

Si la commande réussit mais que rien n'arrive, le problème n'est plus dans
l'application : regarder du côté du relais (expéditeur non vérifié, SPF et DKIM
absents sur le domaine, message classé en indésirable).

## Développement local

`netexpress/settings/dev.py` charge `.env` puis `.env.local` **avant** le reste
des réglages. Renseigner au minimum :

```bash
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_HOST_USER=…
EMAIL_HOST_PASSWORD=…
DEFAULT_FROM_EMAIL=contact@nettoyageexpresse.fr
CONTACT_RECEIVER_EMAIL=…
```

Sans identifiants, le démarrage échoue avec un message explicite, plutôt que
d'envoyer dans le vide. Pour travailler sans envoi réel :

```bash
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```
