# Prompt Engineering Pro - NetExpress

## Comment obtenir une aide efficace sur ton projet

---

## TEMPLATE GÉNÉRAL

```
## Contexte
Je travaille sur NetExpress, une application Django pour une entreprise de nettoyage en Guyane.
- Stack : Django 3.2, Celery, WeasyPrint, SQLite/PostgreSQL
- Fonctionnalités : Devis, Factures, Services, Contact

## Fichiers concernés
- [liste des fichiers pertinents]

## Problème actuel
[Description précise du problème ou de la fonctionnalité voulue]

## Ce que j'ai essayé
[Tes tentatives et leurs résultats]

## Résultat attendu
[Ce que tu veux obtenir concrètement]

## Contraintes
[Limitations techniques, délais, etc.]
```

---

## PROMPTS SPÉCIFIQUES PAR CAS D'USAGE

### 1. Génération PDF - Debug

```
## Contexte
NetExpress - App Django de devis/factures
Le système PDF utilise WeasyPrint + templates HTML

## Problème
Le PDF généré pour le devis [numéro] a un problème :
- [logo ne s'affiche pas / mise en page cassée / texte tronqué / etc.]

## Fichiers concernés
- core/services/pdf_generator.py
- templates/pdf/quote.html
- static/css/pdf.css

## Erreur (si applicable)
```
[Coller le traceback exact]
```

## Ce que j'ai vérifié
- [ ] Le fichier logo existe à [chemin]
- [ ] WeasyPrint est installé (version: X.X)
- [ ] Les dépendances système sont installées (Pango, Cairo)

## Question
Comment corriger [le problème spécifique] ?
```

---

### 2. Envoi Email - Debug

```
## Contexte
NetExpress utilise Django EmailMessage + Celery pour les emails async

## Configuration actuelle
- EMAIL_HOST: smtp.gmail.com
- EMAIL_PORT: 587
- EMAIL_USE_TLS: True
- Backend: smtp (console en DEBUG)

## Problème
Les emails [ne partent pas / arrivent en spam / n'ont pas le PDF / etc.]

## Logs Celery
```
[Coller les logs pertinents]
```

## Test effectué
```python
from django.core.mail import send_mail
send_mail('Test', 'Body', 'from@test.com', ['to@test.com'])
# Résultat: [succès/échec + message]
```

## Question
Pourquoi [le problème] et comment le résoudre ?
```

---

### 3. Nouvelle fonctionnalité PDF

```
## Contexte
NetExpress - Génération de devis PDF avec WeasyPrint

## Fonctionnalité souhaitée
Je veux ajouter [description précise] au PDF de devis :
- [Élément 1 : ex. QR code de paiement]
- [Élément 2 : ex. signature électronique]
- [Élément 3 : ex. conditions générales en page 2]

## Template actuel
Le template est dans templates/pdf/quote.html et utilise pdf.css

## Contraintes
- Doit fonctionner sur A4
- Doit supporter [X] lignes de prestations
- Le logo est en [format PNG/SVG]

## Question
Peux-tu implémenter [fonctionnalité] en modifiant le template et le service ?
```

---

### 4. Amélioration template email

```
## Contexte
NetExpress - Emails transactionnels (devis, factures, contact)

## Template concerné
templates/emails/[nom_template].html

## Modification souhaitée
Je veux :
- [ ] Changer le design (couleurs, layout)
- [ ] Ajouter un élément (bouton, image, section)
- [ ] Rendre responsive pour mobile
- [ ] Ajouter des variables dynamiques

## Branding actuel
- Couleur principale: #0f6d4e (vert)
- Logo: static/img/logo.svg
- Police: Inter, Playfair Display

## Clients email ciblés
- Gmail, Outlook, Apple Mail, Orange

## Question
Peux-tu modifier le template pour [objectif] tout en restant compatible avec les principaux clients email ?
```

---

### 5. Intégration Celery - Problème

```
## Contexte
NetExpress utilise Celery + Redis pour :
- Envoi emails async (devis, notifications)
- Génération PDF en background

## Configuration
```python
CELERY_BROKER_URL = "redis://localhost:6379/0"
```

## Problème
Les tâches [ne s'exécutent pas / échouent / restent en pending]

## Commande worker
```bash
celery -A netexpress worker -l INFO
```

## Output worker
```
[Coller la sortie]
```

## Status Redis
```bash
redis-cli ping
# Résultat: [PONG ou erreur]
```

## Question
Comment diagnostiquer et résoudre [le problème Celery] ?
```

---

### 6. Déploiement production

```
## Contexte
Déploiement NetExpress sur [Render / Railway / VPS / etc.]

## Stack actuel
- Django + Gunicorn
- WhiteNoise pour static
- [PostgreSQL / SQLite]
- Celery + Redis (optionnel)

## Problème de déploiement
[Le PDF ne génère pas / les emails ne partent pas / erreur 500 / etc.]

## Logs serveur
```
[Coller les logs pertinents]
```

## Variables d'environnement configurées
- [ ] SECRET_KEY (générée)
- [ ] DEBUG=False
- [ ] ALLOWED_HOSTS
- [ ] DATABASE_URL
- [ ] EMAIL_* (tous configurés)

## Question
Comment résoudre [problème] en production ?
```

---

## PROMPTS RAPIDES (Copier-Coller)

### Debug rapide PDF
```
Mon PDF de devis ne génère pas. Erreur: [ERREUR].
Fichiers: core/services/pdf_generator.py, templates/pdf/quote.html
Que vérifier ?
```

### Debug rapide Email
```
Les emails ne partent pas. Config: Gmail SMTP port 587 TLS.
Erreur: [ERREUR ou "aucune erreur visible"]
Le test send_mail() en shell Django [fonctionne/échoue].
```

### Modification template
```
Dans templates/pdf/quote.html, je veux ajouter [X] après le tableau des prestations.
Montre-moi le HTML/CSS à ajouter.
```

### Nouveau champ PDF
```
Je veux afficher le champ [nom_champ] du modèle Quote dans le PDF.
Le champ est de type [CharField/TextField/ForeignKey/etc.].
Où l'ajouter dans le template quote.html ?
```

---

## CONSEILS POUR DES RÉPONSES PRÉCISES

1. **Toujours donner le traceback complet** - Pas juste "ça marche pas"

2. **Préciser l'environnement** :
   - Dev local ou production ?
   - DEBUG=True ou False ?
   - Celery actif ou non ?

3. **Donner le contexte métier** :
   - "Pour un client qui demande un devis de nettoyage"
   - "Quand l'admin convertit le devis en facture"

4. **Montrer ce que tu as essayé** - Évite les suggestions déjà testées

5. **Une question = un problème** - Pas 5 sujets en un message

---

## EXEMPLE COMPLET

```
## Contexte
NetExpress - Django 3.2, WeasyPrint 59, Celery 5.3
Environnement: Dev local, DEBUG=True, Celery worker actif

## Problème
Quand je crée un devis depuis l'admin Django et que je clique "Convertir en facture",
le PDF de facture est généré mais le logo n'apparaît pas (carré blanc à la place).

## Fichiers concernés
- factures/models.py (méthode generate_pdf)
- core/services/pdf_service.py (InvoicePdfService)
- templates/pdf/invoice_premium.html
- static/img/logo.png (existe, 150x50px)

## Configuration branding
```python
INVOICE_BRANDING = {
    "logo_path": str(BASE_DIR / "static" / "img" / "logo.png"),
    # ...
}
```

## Ce que j'ai vérifié
- Le fichier logo.png existe et s'affiche correctement sur le site web
- En ouvrant le HTML généré, la balise img pointe vers le bon chemin
- WeasyPrint est installé avec ses dépendances (apt install libpango-1.0-0)

## Logs
Aucune erreur dans la console Django ni Celery.

## Question
Pourquoi le logo ne s'affiche pas dans le PDF WeasyPrint alors que le chemin semble correct ?
```

---

## ANTI-PATTERNS À ÉVITER

❌ "Ça marche pas" → ✅ "Erreur X quand je fais Y"

❌ "Corrige mon code" → ✅ "Voici mon code, voici l'erreur, voici ce que j'attends"

❌ "Fais tout le projet" → ✅ "Aide-moi sur cette fonctionnalité spécifique"

❌ "C'est urgent" → ✅ [Donne juste le contexte technique nécessaire]

❌ Questions multiples → ✅ Un problème par conversation

---

*Ce guide t'aidera à obtenir des réponses précises et actionnables pour ton projet NetExpress.*
