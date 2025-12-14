# Guide d’utilisation — Plateforme NetExpress

Ce guide détaille l’ensemble des fonctionnalités du site NetExpress, développé conformément au cahier des charges pour une entreprise spécialisée dans les espaces verts, le nettoyage, la peinture et le bricolage. Il s’adresse aux clients qui souhaitent réserver un service ou demander un devis ainsi qu’au personnel chargé de gérer les devis et les factures.

## 1. Navigation générale

### Accueil

L’écran d’accueil met immédiatement en valeur l’expertise de NetExpress dans les **espaces verts**, le **nettoyage**, la **peinture** et le **bricolage**. Vous y trouverez :

* Un **héro** présentant la promesse de la marque : interventions rapides, qualité certifiée, tarifs transparents.
* Une section **« Nos métiers »** qui affiche quatre cartes (Espaces verts, Nettoyage, Peinture, Bricolage). Chaque carte vous redirige vers la liste filtrée des services correspondants.
* Une sélection de **services populaires** issus de notre catalogue. Chaque carte indique un prix indicatif (« à partir de … € ») et la durée moyenne du service.
* Les **étapes du parcours client** décrivant comment choisir un service, confirmer l’intervention et recevoir sa facture.
* Un bloc **témoignages** et un **appel à l’action final** invitant à demander un devis.
* Aucun scroll horizontal n’est nécessaire : la grille est fluide et responsive.

### Mise à jour 2025 et images libres de droits

En 2025, le site a été entièrement repensé pour moderniser son apparence et
améliorer l’expérience utilisateur.  Les illustrations présentes sur
l’accueil, les listes et les fiches de services sont désormais fournies
par Unsplash sans utiliser d’API.  Les liens de type
`https://source.unsplash.com/400x300/?motcle` permettent de récupérer
des photos libres de droits correspondant à un mot clé【668280112401708†L16-L63】.  Vous
remarquerez ainsi des photos de jardins, d’outils ou de bureaux selon les
catégories sélectionnées.  Cette approche garantit une esthétique
professionnelle tout en respectant les droits d’auteur.

### Catalogue de services

* **Liste des services :** accessible via le menu *Services*, cette page affiche tous les services actifs. Vous pouvez filtrer la liste par catégorie en ajoutant un paramètre `?category=slug` dans l’URL (par exemple : `/services/?category=espaces-verts`). Le filtre est également utilisé par les cartes « Nos métiers » de l’accueil.
* **Détail d’un service :** cliquez sur un service pour ouvrir sa fiche détaillée : description, catégorie, prix de base (« à partir de … € »), durée estimée, zone desservie et une **checklist** des tâches incluses (déblayage, taille de haies, peinture de façades, etc.). Un bouton **« Demander un devis »** pré‑remplit ensuite le formulaire de devis avec ce service.

### À propos

La page **À propos** explique l’historique, les valeurs et la mission de NetExpress : qualité, transparence et respect de l’environnement. Elle est accessible via le menu et s’adresse aux visiteurs qui souhaitent en savoir plus sur l’entreprise.

### Contact

Le lien *Contact* ouvre un formulaire permettant de poser vos questions ou de demander un partenariat. Sélectionnez le sujet (prospection, SAV, partenariat, gros volumes ou autre) puis saisissez vos coordonnées et votre message. Un accusé de réception vous est envoyé automatiquement.

### Demande de devis

* Accédez au formulaire via `/devis/nouveau/` ou en cliquant sur **« Demander un devis »** à différents endroits du site.
* Renseignez vos informations (nom, téléphone, e‑mail), sélectionnez le **service souhaité** dans une liste déroulante et précisez votre message (adresse, surface, attentes).
* Soumettez le formulaire : une référence de **devis** est générée automatiquement et un accusé de réception s’affiche. Un membre de l’équipe vous contactera sous 24–48 heures ouvrées pour valider la prestation.
* Les devis sont consultables côté personnel dans l’interface d’administration.

## 2. Gestion des devis et factures

### Accès à l’administration

L’administration utilise le thème **Jazzmin** pour offrir une interface moderne et haut de gamme. Conformément au cahier des charges, l’URL d’accès à l’admin est personnalisée : la dernière étape de la configuration du site consiste à **brancher le site d’administration sur une URL spécifique**, comme le montre la documentation de Django【824420556980610†L3019-L3033】. Dans notre cas, nous utilisons `/gestion/` à la place du `/admin/` par défaut. Seuls les utilisateurs ayant l’attribut `is_staff=True` peuvent s’y connecter.

### Gestion des devis

* Depuis le menu **Ventes → Devis**, le personnel voit l’ensemble des demandes de devis. Pour chaque devis : numéro, client, service demandé, montant estimé, statut (en attente, accepté, refusé) et date.
* Les devis peuvent être **mis à jour** (modifier le montant, le statut) ou **transformés en facture**. Une action groupée permet de sélectionner plusieurs devis et de générer des factures en une seule fois.

### Générer une facture

Pour créer et exporter une facture PDF, suivez les étapes ci‑dessous :

1. **Installez le module ReportLab** si ce n’est pas déjà fait : la bibliothèque ReportLab, disponible sur PyPI, permet de générer des PDF et s’installe avec pip【598069122958153†L22-L29】. Vous pouvez vérifier l’installation en important le module dans un shell Python【598069122958153†L30-L33】.
2. **Créez une facture depuis un devis** : dans l’admin (menu Factures → Ajouter une facture), sélectionnez le devis à facturer. Un numéro unique de facture est généré automatiquement (`F-YYYYMMDD####`). Complétez le montant TTC et enregistrez.
3. **Générez le PDF** : revenez à la liste des factures, cochez celle que vous venez de créer et utilisez l’action groupée **« Générer les PDF pour les factures sélectionnées »**. Le système utilise ReportLab pour composer un fichier PDF. Concrètement, un code similaire à celui de l’exemple officiel【598069122958153†L42-L63】 est exécuté en interne : un objet `canvas.Canvas` est créé à partir de la réponse HTTP et des chaînes sont dessinées dans le PDF (logo, coordonnées du client, référence du devis, description du service, montant total). Le fichier est ensuite fermé avec `showPage()` et `save()`【598069122958153†L42-L63】.
4. **Téléchargement et envoi** : après génération, un lien de téléchargement apparaît dans la colonne « PDF ». Cliquez dessus pour récupérer le fichier et l’envoyer au client par e‑mail. Vous pouvez également configurer l’envoi automatique par e‑mail via l’interface d’administration.

### Personnalisation du PDF

Le gabarit de facture peut être adapté : vous pouvez modifier les coordonnées de l’entreprise, ajouter un logo, personnaliser les couleurs et la typographie. Toutes ces modifications se font dans le code Python qui construit le PDF via ReportLab. Consultez la documentation Django sur la sortie PDF【598069122958153†L68-L93】 pour plus de détails.

## 3. Bonnes pratiques et recommandations

* **Administration Jazzmin :** l’interface d’administration est organisée en sections claires (Ventes, Catalogue, Communication). Profitez‑en pour gérer vos clients, devis, factures, services et catégories depuis un seul endroit.
* **Pages statiques** : ajoutez des pages pour les mentions légales, les CGV et la politique de confidentialité dans l’app `core`. Ces pages renforcent la conformité RGPD.
* **Sécurité** : configurez correctement vos variables d’environnement (`SECRET_KEY`, `ALLOWED_HOSTS`, `EMAIL_HOST`, etc.). Utilisez HTTPS en production et activez les en‑têtes de sécurité via `SecurityMiddleware`.
* **Performance** : veillez à optimiser vos images, minifier vos CSS/JS et mettre en cache les pages. Le design a été pensé pour éviter les barres de scroll horizontales et rester fluide sur mobile.
* **Qualité du code** : mettez en place des tests unitaires pour vos modèles, vues et formulaires et utilisez un linter (Ruff ou Black). Une CI (GitHub Actions) peut automatiser ces vérifications.

### Mode statique en cas d’absence de dépendances

Dans certains environnements, il peut être impossible d’installer Django ou
les dépendances Python (problème de proxy, installation verrouillée).  Pour
anticiper cette situation, le script `manage.py` de NetExpress contient un
mode de secours : s’il ne parvient pas à importer Django, il démarre un
serveur HTTP simple qui sert les fichiers du répertoire `static_site/`.
Placez des pages HTML dans ce répertoire (une page d’accueil est
fournie par défaut) pour permettre aux utilisateurs de consulter
rapidement vos services même sans backend.  Bien entendu, les formulaires
ne fonctionneront pas en mode statique, mais les informations et
illustrations resteront accessibles.

---

NetExpress vous remercie pour votre confiance. Pour toute question supplémentaire, utilisez le formulaire de contact ou adressez‑vous à un administrateur via l’interface `/gestion/`.

---

**NetExpress** vous remercie d’avoir choisi cette solution. Pour toute question supplémentaire, contactez l’équipe de support via le formulaire de contact ou l’interface d’administration.