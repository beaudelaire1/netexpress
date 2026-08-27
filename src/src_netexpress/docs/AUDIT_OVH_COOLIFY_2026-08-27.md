# Audit NetExpress avant déploiement OVH / Coolify

Date : 27 août 2026. Version examinée : `for_prod`, commit `685eac92`.

## Conclusion

**Ne pas exposer cette version sur Internet.** La base Django est exploitable pour le projet, mais plusieurs défauts permettent une prise de contrôle ou un accès indu aux documents clients. Des erreurs de facturation et des adaptations Docker/Coolify doivent également être traitées.

Le dépôt distant a été récupéré avec `git fetch origin`, puis vérifié avec `git merge --ff-only origin/for_prod`. La branche locale était déjà à jour, sans modification locale préalable. Aucun déploiement, commit, push, changement DNS ou modification de code applicatif n'a été effectué pour cet audit.

## 1. Périmètre et limites

- Application située dans `src/src_netexpress`, et non à la racine du dépôt.
- Huit applications Django : accounts, core, services, devis, factures, tasks, messaging, contact.
- 229 fichiers Python suivis, dont 46 migrations numérotées ; 130 templates HTML suivis.
- Interface Django/Templates, Tailwind, HTMX, Alpine, TinyMCE/Jazzmin ; PostgreSQL prévu en production ; Celery/Redis, Brevo, Cloudinary et génération PDF.
- Lecture du code, des paramètres, des scripts Docker et des dépendances ; vérifications Django ; reproductions sur SQLite en mémoire ; tests existants et audit des paquets.
- Tests exécutés avec l'environnement local Python **3.14.2 / Django 5.2.13**. Le Dockerfile utilise **Python 3.11** : les résultats locaux ne certifient pas le comportement de l'image Linux.
- Les connexions réseau de l'application ont été bloquées dans les tests et reproductions ; les fichiers générés ont été dirigés vers des répertoires temporaires. La base locale existante n'a pas été utilisée pour ces tests.
- Ni le serveur OVH, ni une instance Coolify, ni la base de production, ni les paramètres réels des prestataires n'ont été inspectés. Aucun courriel réel n'a été envoyé.
- Docker CLI est présent, mais le moteur Docker n'est pas démarré : **image non construite et non exécutée**. Pas de test de charge, de recette visuelle complète, de pentest exhaustif ni de validation juridique de conformité.

## 2. Sécurité : corrections avant toute exposition publique

### Critique — inscription publique pouvant créer un superadministrateur

Le formulaire d'inscription accepte tous les rôles de `Profile.ROLE_CHOICES`, dont `admin_technical`, puis enregistre directement ce rôle. Le signal de synchronisation accorde ensuite `is_staff=True` et `is_superuser=True`.

**Preuve locale, avec contrôle CSRF actif :** une inscription anonyme crée effectivement un superutilisateur. La réponse d'inscription est HTTP 500 à cause de l'appel à `login()` sans sélection de backend, mais le compte reste en base. Une connexion classique avec ce compte fonctionne ensuite et `/gestion/` répond HTTP 200.

Références : [formulaire, lignes 22 et 36](C:/Users/vilme/OneDrive/Bureau/netexpress/src/src_netexpress/accounts/forms.py:22), [inscription, lignes 30–33](C:/Users/vilme/OneDrive/Bureau/netexpress/src/src_netexpress/accounts/views.py:30), [attribution des privilèges](C:/Users/vilme/OneDrive/Bureau/netexpress/src/src_netexpress/accounts/signals.py:143).

**Correction :** interdire tout rôle administratif dans les entrées publiques ; affecter le rôle client côté serveur ; réserver les changements de rôle à une opération administrative autorisée. Corriger aussi la connexion après inscription. Le `ProfileForm` expose également le rôle et doit être corrigé même si le middleware limite actuellement certains accès à cette page. Ajouter des tests HTTP de non-escalade pour chaque rôle.

### Critique — identifiants superutilisateur codés en dur

`start.sh` exécute systématiquement `ensure_superuser`. Si aucun superutilisateur n'existe, cette commande crée un compte avec un identifiant et un mot de passe constants présents dans le dépôt.

Références : [commande de création](C:/Users/vilme/OneDrive/Bureau/netexpress/src/src_netexpress/core/management/commands/ensure_superuser.py:23), [appel au démarrage](C:/Users/vilme/OneDrive/Bureau/netexpress/src/src_netexpress/start.sh:6).

**Correction :** supprimer ce provisionnement automatique avec mot de passe fixe ; prévoir une création administrative ponctuelle et contrôlée. Réinitialiser les identifiants concernés si cette commande a déjà été exécutée sur un environnement exposé. Les valeurs sensibles ne sont volontairement pas reproduites ici.

### Critique — accès aux documents fondé sur une adresse email non vérifiée

L'inscription accepte une adresse email libre. L'accès aux devis, factures et documents publiés est ensuite accordé par simple égalité avec l'email du client, sans relation de propriété vérifiée ni étape de validation de l'adresse dans ce parcours.

**Preuve locale :** un compte de rôle `client` créé avec l'adresse d'un client existant obtient `can_access_quote=True` et retrouve son devis dans la liste accessible. Cette faille demeure même si l'inscription est limitée au rôle client.

Références : [adresse libre à l'inscription](C:/Users/vilme/OneDrive/Bureau/netexpress/src/src_netexpress/accounts/forms.py:21), [filtrage des documents](C:/Users/vilme/OneDrive/Bureau/netexpress/src/src_netexpress/core/services/document_service.py:54), [comparaison d'emails](C:/Users/vilme/OneDrive/Bureau/netexpress/src/src_netexpress/core/services/document_service.py:90).

**Correction :** lier explicitement un compte utilisateur à un client après invitation ou vérification d'email. Refuser les rattachements automatiques sur la seule adresse déclarée ; définir une règle d'unicité/normalisation des identités et tester les doublons.

### Urgent — secrets dans la configuration locale et dans l'historique Git

- Un jeton GitHub est intégré en clair à l'URL `origin` dans la configuration Git locale. Il n'est pas nécessaire de le recopier dans Coolify.
- Des fichiers `.env` et `.env.local` ont été suivis dans d'anciens commits. La version de `.env.local` accessible via `867f0b2c^` contient notamment des valeurs non factices pour des paramètres Django et Brevo. Leur validité actuelle n'a pas été testée.
- Ces fichiers ne sont plus suivis dans la version courante ; leur suppression du dernier commit n'efface pas l'historique.

**Correction :** révoquer/remplacer le jeton GitHub ; vérifier puis renouveler les secrets historiques concernés auprès de leurs propriétaires. Utiliser une GitHub App ou une clé de déploiement restreinte pour Coolify. Nettoyer l'historique seulement dans une opération coordonnée, après rotation ; ne pas faire de réécriture ou de force-push improvisé.

### Élevé — confidentialité et persistance des fichiers à définir

En production, le stockage par défaut est `MediaCloudinaryStorage` si les trois paramètres Cloudinary sont présents. Ce backend sert aussi aux documents clients et aux PDF ; aucun réglage applicatif d'upload authentifié n'a été trouvé. Des templates administratifs et de messagerie utilisent directement les URL des fichiers.

Cloudinary rend par défaut les ressources de type `upload` accessibles via son CDN public. La configuration du compte distant n'a pas été inspectée : il faut contrôler les restrictions réellement appliquées, pas présumer une fuite déjà observée. [Documentation Cloudinary](https://cloudinary.com/documentation/control_access_to_media).

Sans Cloudinary, le code revient au stockage dans `/app/media`. Aucun volume persistant n'est défini dans le dépôt et Django ne sert pas `/media/` avec `DEBUG=False`.

Références : [stockage de production](C:/Users/vilme/OneDrive/Bureau/netexpress/src/src_netexpress/netexpress/settings/prod.py:185), [service des médias limité au développement](C:/Users/vilme/OneDrive/Bureau/netexpress/src/src_netexpress/netexpress/urls.py:64).

**Correction :** séparer images publiques et documents privés. Prévoir un stockage privé avec téléchargement soumis aux permissions ou URL signée à durée limitée. Pour un stockage local sur OVH, monter un volume durable partagé si nécessaire avec le worker, sauvegarder ce volume, et ne pas exposer tous les documents via un répertoire public.

## 3. Fiabilité métier

### Élevé — la conversion devis → facture modifie les quantités

Les quantités de devis sont décimales, mais les lignes de facture sont entières. La conversion applique `int(round(...))`.

**Preuve locale :** une ligne de `0,5 × 100 €` vaut `50 €` sur le devis ; elle devient une quantité `0` sur la facture. Le total initial copié reste `50 €`, puis passe à `0 €` après recalcul. Les documents peuvent donc présenter des lignes et totaux incohérents, ou facturer un montant erroné.

Référence : [conversion des lignes](C:/Users/vilme/OneDrive/Bureau/netexpress/src/src_netexpress/devis/services.py:106).

**Correction :** conserver des quantités décimales de bout en bout, avec migration des champs et règles d'arrondi explicites ; tester les quantités `0,5`, `1,5`, les remises et taxes.

### Élevé — numérotation des devis et factures fragile

Les numéros sont calculés à partir du dernier numéro trié comme une chaîne, avec le manager qui masque les documents supprimés logiquement. Les verrous sont libérés avant l'enregistrement final dans les méthodes `save()` hors transaction englobante.

**Deux défauts reproduits pour les devis et les factures :**

1. Avec les suffixes `999` et `1000` présents, le numéro suivant provoque une `IntegrityError` d'unicité.
2. Après suppression logique du dernier document d'une année, la création suivante tente de réutiliser son numéro et provoque également une `IntegrityError`.

Références : [numéros de devis](C:/Users/vilme/OneDrive/Bureau/netexpress/src/src_netexpress/devis/models.py:236), [numéros de facture](C:/Users/vilme/OneDrive/Bureau/netexpress/src/src_netexpress/factures/models.py:98), [filtrage des suppressions](C:/Users/vilme/OneDrive/Bureau/netexpress/src/src_netexpress/core/mixins.py:29).

**Correction :** utiliser un compteur numérique transactionnel par série/année, indépendant des suppressions, avec contrainte d'unicité et gestion de concurrence. Tester sous PostgreSQL. Le scénario concurrent n'a pas été exécuté pendant cet audit.

### Autres défauts confirmés ou visibles dans le code

- **Redirection externe après connexion :** `next` est utilisé sans vérifier le domaine. Un test local obtient une redirection HTTP 302 vers un domaine externe. Utiliser `url_has_allowed_host_and_scheme`. [Vue concernée](C:/Users/vilme/OneDrive/Bureau/netexpress/src/src_netexpress/accounts/views.py:67).
- **Anciennes routes de facturation cassées :** des noms comme `factures: archive` et `factures/archive. html` contiennent des espaces erronés. La création de facture est également autorisée en GET. Corriger ou retirer ces routes et réserver les mutations à POST avec CSRF. [Vues historiques](C:/Users/vilme/OneDrive/Bureau/netexpress/src/src_netexpress/factures/views.py:42).
- **Protection anti-bot permissive :** Turnstile laisse passer si la clé manque ou si la vérification lève une exception. Définir explicitement la politique de production et prévoir une limitation des soumissions. [Vérification](C:/Users/vilme/OneDrive/Bureau/netexpress/src/src_netexpress/core/turnstile.py:35).
- **Aperçu PDF intégré :** les templates utilisent une iframe locale, alors que `frame-src` n'autorise que Cloudflare et que `frame-ancestors 'none'`/`X-Frame-Options: DENY` interdisent l'intégration. Incompatibilité constatée dans le code, sans recette navigateur. Corriger de manière ciblée sur le parcours d'aperçu.

## 4. Dépendances et reproductibilité

La majorité des dépendances Python ne sont pas verrouillées : contraintes `>=`, absence de lockfile. Deux constructions peuvent donc installer des versions différentes. Des exigences sont dupliquées entre `base.txt` et `prod.txt`, et les deux pilotes PostgreSQL `psycopg2-binary` et `psycopg[binary]` sont présents.

Audit de l'environnement local installé : **55 signalements bruts sur 9 paquets**, soit **42 couples paquet/identifiant distincts après dédoublonnage simple**. Cela inclut des outils de développement et ne signifie pas que 42 failles sont exploitables dans l'application ni présentes dans une future image Linux.

| Paquet local | Version auditée | Traitement |
|---|---|---|
| Django | 5.2.13 | Passer à une version corrigée de la série 5.2 et la verrouiller |
| bleach | 6.3.0 | Mettre à jour et retester le nettoyage HTML |
| Pillow | 12.2.0 | Mettre à jour et retester images/PDF |
| sqlparse, urllib3, idna, click | Versions dans la preuve JSON | Mettre à jour les dépendances directes et transitives |
| pip | 25.3 | Actualiser l'outil de construction |
| WeasyPrint | 68.1 | Examiner l'avis et limiter les ressources accessibles au moteur PDF |

Au jour de l'audit, Django indique **5.2.17** comme dernière version de la série LTS 5.2, maintenue jusqu'en avril 2028. Une migration vers Django 6 n'est pas nécessaire pour cet objectif. [Versions officielles](https://www.djangoproject.com/download/).

L'avis WeasyPrint remonté porte sur `presentational_hints=True` et du HTML non fiable ; cet argument n'est pas activé dans l'appel PDF examiné. Le scanner ne donne pas de version corrigée pour cet avis : ne pas conclure à son exploitabilité dans ce projet sur le seul résultat automatique.

`npm audit` signale **2 dépendances de construction de gravité élevée : nanoid et postcss**. Le code CSS est précompilé et versionné ; ces paquets ne constituent pas un serveur Node en production. Mettre à jour le lockfile, reconstruire les assets et retester leur rendu.

Une seconde analyse a été effectuée sur une **résolution neuve de `requirements/prod.txt`**, sans installer ces paquets dans le projet : elle choisit notamment Django 5.2.17 et WeasyPrint 69.0, et ne remonte **aucune vulnérabilité connue** dans le scanner utilisé. Cette résolution a été faite sous Windows/Python 3.14, pas dans l'image Linux/Python 3.11. Cela confirme que le relevé du vieil environnement local ne doit pas être présenté comme celui de la future production ; il reste nécessaire de verrouiller et de tester les versions réellement construites.

**À mettre en place :** verrouillage des versions, audit régulier, installation reproductible en CI et test de l'image finale. Les audits n'ont appliqué aucune mise à jour.

## 5. Préparation Docker / Coolify

| Point | État actuel | Action avant déploiement |
|---|---|---|
| Contexte de construction | Dockerfile sous `src/src_netexpress` ; le `render.yaml` racine vise un Dockerfile absent à la racine | Configurer le répertoire de base `/src/src_netexpress` et le Dockerfile de ce dossier |
| Port | Gunicorn écoute sur `$PORT`, sans valeur par défaut | Définir `PORT=8000`, exposer le port interne 8000, ajouter une valeur de repli au script |
| Paramètres Django | Paramètres prod passés seulement à la commande de construction ; démarrage dépendant de l'environnement | Injecter `DJANGO_SETTINGS_MODULE=netexpress.settings.prod` sur web et worker ; vérifier `DEBUG=False` au runtime |
| Bibliothèques PDF | Image slim avec seulement `gcc` et `libpq-dev` ajoutés | Installer les bibliothèques Pango/HarfBuzz et polices requises, puis générer un vrai devis et une facture dans l'image |
| Arrêt sur erreur | `start.sh` continue après un échec de migration et masque certains échecs de collecte statique | Arrêter le démarrage si une étape obligatoire échoue ; séparer/protéger la phase de migration |
| Identité du conteneur | Aucun utilisateur applicatif déclaré | Exécuter l'application sans root et fixer les droits des volumes |
| Contexte Docker | Aucun `.dockerignore` | Exclure `.env*`, `.venv`, bases locales, médias, caches et dépendances locales ; un build depuis ce dossier copierait actuellement ces fichiers |
| Sondes | `/healthz/` existe, mais passe par les middlewares HTTPS/hôtes | Concevoir une sonde interne qui reçoit réellement 200, sans affaiblir globalement HTTPS |
| Celery | Tâches routées vers `notifications`, `documents`, `messaging` ; commande worker sans sélection de files | Faire consommer au worker les files utilisées, par exemple `-Q celery,notifications,documents,messaging` |
| Persistance | Pas de définition versionnée des volumes/services | Définir PostgreSQL, Redis, stockage des médias et sauvegardes dans Coolify ou un Compose versionné |

**Sondes reproduites avec les paramètres de sécurité prod :** `localhost` en HTTP retourne 400 ; le domaine autorisé en HTTP retourne 301 ; avec le domaine autorisé et l'en-tête du proxy HTTPS, la sonde retourne 200. Un `/healthz/` qui ne teste pas la base constitue seulement une preuve de vie du processus ; prévoir aussi une vérification de disponibilité des dépendances.

**Files Celery reproduites sans broker externe :** le worker par défaut est configuré pour `celery`, alors que `contact.tasks.notify_new_contact` est routée vers `notifications`. La commande du manifeste Render ne les aligne pas. Sans Redis, l'application revient à l'exécution synchrone, ce qui masque ce défaut et allonge les requêtes.

Références : [Dockerfile](C:/Users/vilme/OneDrive/Bureau/netexpress/src/src_netexpress/Dockerfile:11), [script de démarrage](C:/Users/vilme/OneDrive/Bureau/netexpress/src/src_netexpress/start.sh:3), [routage Celery](C:/Users/vilme/OneDrive/Bureau/netexpress/src/src_netexpress/netexpress/settings/base.py:496), [commande worker](C:/Users/vilme/OneDrive/Bureau/netexpress/src/src_netexpress/render.yaml:70).

Coolify permet de définir les sondes dans son interface ou dans le Dockerfile ; les sondes d'interface nécessitent `curl` ou `wget`, absents de l'installation explicite actuelle. Une sonde Python intégrée à l'image est aussi possible. [Documentation des sondes](https://coolify.io/docs/knowledge-base/health-checks). Les dépendances natives WeasyPrint doivent être présentes indépendamment du paquet Python. [Installation WeasyPrint](https://doc.courtbouillon.org/weasyprint/latest/first_steps.html).

## 6. Architecture cible proposée

Sur un VPS OVH Linux avec accès SSH : reverse proxy Coolify avec TLS, service web Django/Gunicorn, worker Celery distinct, PostgreSQL et Redis sur réseau privé, stockage durable séparant fichiers publics et documents confidentiels.

| Élément | Configuration envisagée |
|---|---|
| Dépôt / branche | Dépôt NetExpress, branche de livraison explicitement choisie ; actuellement `for_prod` |
| Web | Image Docker corrigée, port interne 8000, HTTPS via le proxy |
| Worker | Même image et paramètres métier que le web ; commande Celery dédiée |
| PostgreSQL | Volume durable, pas de port ouvert sur Internet, sauvegarde externe et restauration testée |
| Redis | Accès privé, configuration commune web/worker, politique de persistance choisie |
| Fichiers | Volume durable ou stockage objet privé ; restauration testée avec la base |
| Secrets | Variables protégées dans Coolify, jamais dans Git ni dans l'image |
| Email | Brevo configuré, expéditeur vérifié et essai contrôlé après autorisation |

Variables minimales à renseigner : `DJANGO_SETTINGS_MODULE`, `DJANGO_SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `PORT`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SITE_URL`, `BREVO_API_KEY`, `DEFAULT_FROM_EMAIL`, `DEFAULT_FROM_NAME`, `CONTACT_RECEIVER_EMAIL`, `CONTACT_CC_EMAIL`, `TASK_NOTIFICATION_EMAIL`, `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY`, puis les paramètres de stockage et les informations d'entreprise nécessaires aux documents. Le web et le worker doivent partager les paramètres utiles à leurs fonctions.

Le minimum annoncé par la documentation Coolify est de 2 cœurs, 2 Go de RAM et 30 Go libres. Pour héberger aussi PostgreSQL, Redis, les builds et les PDF, **4 vCPU / 8 Go de RAM est une estimation de départ**, à ajuster après mesure ; ce n'est ni une exigence validée par charge ni une recommandation d'offre commerciale particulière. [Prérequis Coolify](https://coolify.io/docs/get-started/installation).

## 7. Vérifications réalisées

| Vérification | Résultat |
|---|---|
| Fetch et comparaison distante | Réussite ; `HEAD` identique à `origin/for_prod` |
| Analyse syntaxique Python | 229 fichiers analysés, aucune erreur de syntaxe |
| `manage.py check` avec paramètres test | Aucun problème signalé |
| `manage.py makemigrations --check --dry-run` | Aucune migration manquante détectée |
| Application des migrations | Réussite sur une base SQLite en mémoire créée pour les reproductions |
| `manage.py check --deploy` avec paramètres prod et secrets factices | Aucun problème signalé ; ne détecte pas les vulnérabilités métier décrites ci-dessus |
| `collectstatic` vers un dossier temporaire | 475 fichiers copiés, 844 traitements ; deux doublons de fichiers admin signalés |
| `pip check` | Aucune incompatibilité déclarée entre paquets installés |
| Audit dépendances Python / npm | Résultats détaillés en section 4 et dans la preuve JSON |
| Résolution neuve de `requirements/prod.txt` | Réussite sans installation ; aucune vulnérabilité connue signalée sur cette résolution locale |
| Suite principale complète | Interrompue après environ **15 min 25 s**, avec de nombreux échecs dans la sortie partielle ; **pas de bilan complet**, donc aucune affirmation de validation de cette suite |
| Sous-ensemble sans fichiers de propriétés Hypothesis et sans `test_role_based_access.py` | **201 tests collectés : 131 réussis, 68 échecs, 2 erreurs de préparation**, 47 avertissements, environ 51 secondes |
| Suite historique `bugfix_email_netexpress/tests` | Échec avant collecte : import de `crm.models.Customer`, module `crm` absent |
| Reproductions ciblées | Escalade de rôle, accès par email non vérifié, redirection externe, quantités, numérotation, files Celery et sondes confirmés localement |
| Construction / lancement Linux | Non effectués : moteur Docker indisponible |

Les échecs ne doivent pas tous être assimilés à des bugs de production. Parmi les 70 échecs/erreurs du sous-ensemble : 25 proviennent d'anciennes fixtures qui affectent directement une relation devenue ManyToMany ; 9 de mocks Brevo incompatibles avec l'usage actuel ; 9 d'appels d'authentification sans le `request` exigé par Axes. Il faut remettre les tests en cohérence, sans simplement supprimer leurs assertions.

En revanche, 16 échecs/erreurs concernent un profil utilisateur absent. Une reproduction indépendante confirme que `User.objects.create_user()` ne crée pas le profil attendu : le signal utilise `hasattr(instance, 'profile')`, qui absorbe l'exception recherchée par le `except`, sans branche de création quand le résultat est faux. Corriger cet invariant et tester les créations hors parcours web. [Signal concerné](C:/Users/vilme/OneDrive/Bureau/netexpress/src/src_netexpress/accounts/signals.py:221).

## 8. Qualité et maintenance

Points favorables : séparation des paramètres dev/test/prod, migrations présentes et cohérentes avec les modèles, permissions objet dans les vues de téléchargement, secrets requis pour démarrer en prod, HTTPS et cookies sécurisés, protection CSRF, nettoyage HTML et mécanismes de limitation des essais de connexion.

Ces mécanismes ne compensent pas les défauts de rattachement d'identité et d'attribution de rôles. Les tests de permissions existants n'offrent pas de garantie tant que leurs résultats et leur couverture de ces parcours ne sont pas corrigés.

Dette notable : `core/views.py` compte 2 625 lignes, plusieurs parcours et générateurs historiques coexistent, deux manifestes Render divergent, aucune CI suivie n'a été trouvée. Le dépôt contient aussi **999 fichiers de cache Hypothesis suivis**, sans utilité pour une image de production. Les retirer de l'index dans une modification distincte et les ignorer ; conserver seulement les jeux de régression explicitement souhaités.

## 9. Ordre de travail recommandé

1. Fermer les parcours d'escalade et d'usurpation d'email ; supprimer les identifiants administratifs fixes ; effectuer les rotations de secrets nécessaires.
2. Corriger les quantités, la numérotation et les tests de non-régression, puis les exécuter sous PostgreSQL.
3. Verrouiller et mettre à jour les dépendances ; corriger Docker, le démarrage, les files Celery et les sondes ; fixer la stratégie des fichiers privés.
4. Déployer une préproduction isolée sur OVH/Coolify avec des données fictives. Vérifier connexion par rôle, invitation, devis décimal, validation, conversion, PDF, envoi de courriel contrôlé, pièces jointes, redémarrage et persistance.
5. Tester une restauration complète et documenter le retour arrière. Migrer les données réelles et basculer le domaine seulement après cette recette.

Le détail des reproductions et les résumés automatisés se trouvent dans [les preuves de l'audit](C:/Users/vilme/OneDrive/Bureau/netexpress/src/src_netexpress/docs/AUDIT_PREUVES_2026-08-27.json). Aucune correction n'est implicitement considérée comme réalisée par ce rapport.
