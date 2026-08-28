# Portail comptable NetExpress

## Un dossier partagé avec le cabinet

NetExpress (rôle `admin_business` ou `admin_technical`) dispose d’un accès **Comptabilité** dans la navigation et d’une entrée dans les actions rapides après les KPI. NetExpress dépose et complète les pièces, puis suit leur traitement. Seul le cabinet effectue les contrôles. Le cabinet (`accountant`, adresse activée) consulte, télécharge, annote les contrôles et exporte ; il ne dépose ni ne modifie les pièces et n’accède pas à l’administration.

- **Factures clients** : disponibles automatiquement dès leur émission, y compris les avoirs et les factures archivées.
- **Devis** : disponibles automatiquement après leur passage hors brouillon (envoyé, accepté, refusé ou facturé). Consultation et PDF uniquement. Ils sont exclus du chiffre d’affaires et ont leur propre CSV dans l’archive.
- **Factures fournisseurs** : seul le fichier est obligatoire au dépôt. Les détails sont facultatifs et repliés. Les valeurs inconnues restent vides, jamais estimées à zéro. Avant le contrôle, NetExpress complète fournisseur, numéro, date, TTC et TVA (0 si la facture le justifie).
- **Autres documents** : relevés bancaires, documents fiscaux ou sociaux, contrats, assurances et autres pièces. Le nom du fichier et la date du dépôt servent au classement par défaut. Aucun impact sur les totaux.

Les documents sont stockés hors des médias publics. PDF, PNG et JPEG sont acceptés, jusqu’à 10 Mo. Les doublons de fichier sont détectés. Une modification remet le contrôle en attente et les éditions concurrentes sont détectées. Les archives sont limitées à 100 pièces / 100 Mo ; aucun ZIP partiel n’est livré si une pièce est indisponible.

Les factures fournisseurs sans date sont retrouvées via leur date de dépôt dans les filtres. Les montants affichés additionnent uniquement les valeurs connues ; le nombre de factures à compléter est visible. La signature Trait d’Union Studio reste discrète dans l’interface.

## Installation et vérification

Depuis `src/src_netexpress`, avec l’environnement Python du projet :

```powershell
.venv/Scripts/python.exe manage.py migrate --settings=netexpress.settings.local
.venv/Scripts/python.exe manage.py create_accounting_demo --settings=netexpress.settings.local
.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000 --settings=netexpress.settings.local
```

La commande affiche un mot de passe aléatoire et crée `cabinet_test` sans droits d’administration. Elle refuse de remplacer un compte existant et refuse les configurations de production. Aucun mot de passe n’est enregistré dans Git. Ce compte voit le dossier de la base locale : il ne crée pas un espace isolé ni un accès au site en production. Aucun email n’est envoyé.

Pour un cabinet réel, utiliser **Accès du cabinet** : invitation nominative avec choix du mot de passe. Appliquer la migration `accounting.0002_simplify_deposits_and_documents` et collecter les fichiers statiques lors du déploiement. La migration conserve les factures et contrôles existants. Ne pas revenir à l’ancien schéma sans traiter les dépôts incomplets et sauvegarder les nouveaux documents.

```powershell
.venv/Scripts/python.exe -m pytest tests/test_accounting_security.py -q
```

## Vérifications du 28 août 2026

- 50 tests comptables réussis ; 1 test de concurrence réservé à PostgreSQL ignoré sous SQLite.
- Migration appliquée après sauvegarde de la base locale ; `makemigrations --check --dry-run`, `manage.py check`, `git diff --check` et syntaxe JavaScript validés.
- Parcours navigateur exécuté dans une base isolée : connexion entreprise, accès depuis la navigation, dépôt d’une facture avec le fichier seul, dépôt d’un relevé, connexion cabinet, lecture et contrôle de ce relevé.
- Nouvel en-tête contrôlé sur ordinateur et à 390 px ; retour au tableau de bord vérifié sur mobile. Menu de compte opérationnel. Les données fictives de vérification sont séparées de la base utilisateur.
- Quatre suites historiques (portails administrateur/client/ouvrier et routage) : 45 tests réussis, 42 échecs. Les 42 identifiants de tests en échec correspondent exactement à ceux du commit sauvegardé `54b24097`. Cette livraison ne prétend pas corriger ces problèmes antérieurs.
- Compte `cabinet_test` actif dans la base locale, rôle comptable confirmé, sans droits d’administration. Aucun compte de démonstration créé en production.
