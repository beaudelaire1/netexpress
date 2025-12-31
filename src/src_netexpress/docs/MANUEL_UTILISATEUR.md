# Manuel Utilisateur NetExpress

**Version 1.0 — Janvier 2025**

---

# Table des Matières

1. [Introduction](#introduction)
2. [Guide Administrateur Business](#guide-administrateur-business)
3. [Guide Ouvrier](#guide-ouvrier)
4. [Guide Client](#guide-client)
5. [Assistance et Contact](#assistance-et-contact)

---

# Introduction

## Qu'est-ce que NetExpress ?

NetExpress est une plateforme de gestion complète pour les entreprises de services (nettoyage, entretien, espaces verts). Elle permet de :

- Gérer les clients et leurs demandes
- Créer et envoyer des devis professionnels
- Générer des factures automatiquement
- Planifier et suivre les interventions
- Communiquer efficacement entre équipes

## Accès à la plateforme

**Adresse du site :** https://nettoyageexpresse.fr

Chaque utilisateur dispose d'un compte personnel avec :
- Un nom d'utilisateur
- Un mot de passe sécurisé

---

# Guide Administrateur Business

## 1. Connexion

1. Rendez-vous sur le site NetExpress
2. Cliquez sur **"Connexion"** en haut à droite
3. Entrez votre nom d'utilisateur et mot de passe
4. Cliquez sur **"Se connecter"**

Vous arrivez automatiquement sur le **Tableau de Bord Admin**.

---

## 2. Le Tableau de Bord

Le tableau de bord affiche en un coup d'œil :

| Section | Information |
|---------|-------------|
| **Chiffre d'affaires** | Total du mois et évolution |
| **Devis en attente** | Nombre de devis à traiter |
| **Factures impayées** | Montant total dû |
| **Tâches du jour** | Interventions planifiées |

### Actions rapides

En haut à droite, vous trouverez des boutons pour :
- ➕ **Nouveau Devis** : Créer un devis rapidement
- ➕ **Nouveau Client** : Ajouter un client
- ➕ **Nouvelle Tâche** : Planifier une intervention

---

## 3. Gestion des Clients

### Voir la liste des clients

1. Dans le menu, cliquez sur **"Clients"** (si disponible) ou accédez via le Dashboard
2. La liste affiche tous vos clients avec leurs informations

### Créer un nouveau client

1. Cliquez sur **"+ Nouveau Client"**
2. Remplissez le formulaire :
   - **Nom complet** (obligatoire)
   - **Email** (obligatoire)
   - **Téléphone**
   - **Entreprise** (si professionnel)
   - **Adresse complète**
3. Cliquez sur **"Créer le client"**

### Consulter un client

Cliquez sur le nom d'un client pour voir :
- Ses informations de contact
- L'historique de ses devis
- Ses factures
- Son chiffre d'affaires total

---

## 4. Gestion des Devis

### Créer un devis

1. Cliquez sur **"Devis"** dans le menu puis **"+ Nouveau Devis"**
2. **Étape 1 - Client** : Sélectionnez le client concerné
3. **Étape 2 - Lignes du devis** :
   - Cliquez sur **"+ Ajouter une ligne"**
   - Choisissez un service ou saisissez une description libre
   - Indiquez la quantité et le prix unitaire
   - Répétez pour chaque prestation
4. **Étape 3 - Dates** : 
   - Date d'émission (automatique)
   - Date de validité (30 jours par défaut)
5. Cliquez sur **"Enregistrer le devis"**

### Envoyer un devis par email

1. Ouvrez le devis concerné
2. Cliquez sur **"Envoyer par email"**
3. Vérifiez l'adresse email du client
4. Personnalisez le message si souhaité
5. Cliquez sur **"Envoyer"**

Le client reçoit un email avec :
- Un lien pour consulter le devis en ligne
- Le PDF du devis en pièce jointe

### Statuts des devis

| Statut | Signification |
|--------|---------------|
| **Brouillon** | En cours de rédaction, non envoyé |
| **Envoyé** | Transmis au client, en attente de réponse |
| **Accepté** | Validé par le client |
| **Refusé** | Décliné par le client |
| **Facturé** | Converti en facture |

### Convertir un devis en facture

1. Ouvrez un devis au statut **"Accepté"**
2. Cliquez sur **"Convertir en facture"**
3. Confirmez l'action
4. La facture est créée automatiquement avec toutes les informations du devis

---

## 5. Gestion des Factures

### Consulter les factures

1. Cliquez sur **"Factures"** dans le menu
2. La liste affiche toutes les factures avec :
   - Numéro de facture
   - Client
   - Montant TTC
   - Statut de paiement

### Statuts des factures

| Statut | Signification |
|--------|---------------|
| **Brouillon** | Non finalisée |
| **Envoyée** | Transmise au client |
| **Payée** | Règlement reçu |
| **En retard** | Échéance dépassée |

### Marquer une facture comme payée

1. Ouvrez la facture concernée
2. Cliquez sur **"Marquer comme payée"**
3. Le statut passe à "Payée"

### Télécharger une facture PDF

1. Ouvrez la facture
2. Cliquez sur **"Télécharger PDF"**
3. Le fichier se télécharge automatiquement

---

## 6. Gestion des Ouvriers

### Voir l'équipe

1. Cliquez sur **"Ouvriers"** dans le menu
2. La liste affiche tous les ouvriers avec :
   - Nom et prénom
   - Email
   - Nombre de tâches assignées
   - Taux de complétion

### Créer un nouvel ouvrier

1. Cliquez sur **"+ Nouvel Ouvrier"**
2. Remplissez les informations :
   - **Prénom** (obligatoire)
   - **Nom** (obligatoire)
   - **Email** (obligatoire) — servira d'identifiant
   - **Téléphone**
3. Cliquez sur **"Créer l'ouvrier"**

L'ouvrier reçoit automatiquement un email avec ses identifiants de connexion.

### Consulter un ouvrier

Cliquez sur un ouvrier pour voir :
- Ses coordonnées
- Ses statistiques de performance
- Ses tâches en cours
- Son historique de tâches

---

## 7. Gestion des Tâches

### Créer une tâche

1. Cliquez sur **"Tâches"** puis **"+ Nouvelle Tâche"**
2. Remplissez le formulaire :
   - **Titre** : Description courte de l'intervention
   - **Description** : Détails de la prestation
   - **Lieu** : Adresse de l'intervention
   - **Ouvriers** : Sélectionnez un ou plusieurs ouvriers
     - Maintenez **Ctrl** (ou **Cmd** sur Mac) pour sélectionner plusieurs
   - **Date de début**
   - **Date d'échéance**
3. Cliquez sur **"Créer la tâche"**

### Planning Global

1. Cliquez sur **"Planning Global"** dans le menu
2. Visualisez toutes les interventions sur un calendrier
3. Utilisez les flèches pour naviguer entre les mois

---

## 8. Analyses et Rapports

### Tableau de bord analytique

1. Cliquez sur **"Analyses"** dans le menu
2. Consultez les indicateurs clés :
   - Chiffre d'affaires avec évolution
   - Taux de conversion des devis
   - Top services demandés
   - Performance des ouvriers

### Générer un rapport

1. Cliquez sur **"Rapports"** (accessible depuis Analyses)
2. Sélectionnez le type de rapport :
   - **Rapport CA** : Toutes les factures d'une période
   - **Rapport Clients** : Activité par client
   - **Rapport Ouvriers** : Performance de l'équipe
3. Choisissez les dates de début et fin
4. Cliquez sur **"Générer"**

### Exporter en Excel

1. Une fois le rapport généré
2. Cliquez sur **"Export CSV"**
3. Ouvrez le fichier avec Excel

---

## 9. Préférences

### Mode sombre

Pour activer le mode sombre (moins fatigant pour les yeux) :
1. Cliquez sur l'icône **lune** 🌙 dans la barre de navigation
2. L'interface passe en mode sombre
3. Cliquez sur l'icône **soleil** ☀️ pour revenir au mode clair

Votre préférence est mémorisée automatiquement.

### Déconnexion

1. Cliquez sur votre nom en haut à droite
2. Cliquez sur **"Déconnexion"**

---

# Guide Ouvrier

## 1. Connexion

1. Rendez-vous sur le site NetExpress
2. Cliquez sur **"Connexion"**
3. Entrez votre nom d'utilisateur (email) et mot de passe
4. Cliquez sur **"Se connecter"**

Vous arrivez sur votre **Espace Ouvrier**.

---

## 2. Mon Tableau de Bord

Votre tableau de bord affiche :

| Section | Information |
|---------|-------------|
| **Tâches du jour** | Interventions prévues aujourd'hui |
| **Tâches en cours** | Interventions commencées |
| **Tâches à venir** | Prochaines interventions |
| **Statistiques** | Votre performance du mois |

---

## 3. Mes Tâches

### Voir mes tâches

1. La liste de vos tâches s'affiche automatiquement
2. Chaque tâche montre :
   - Le titre de l'intervention
   - L'adresse du lieu
   - La date prévue
   - Le statut actuel

### Comprendre les statuts

| Couleur | Statut | Signification |
|---------|--------|---------------|
| 🟡 Jaune | À venir | Intervention planifiée |
| 🔵 Bleu | En cours | Intervention commencée |
| 🟢 Vert | Terminée | Intervention achevée |
| 🔴 Rouge | En retard | Échéance dépassée |

### Consulter une tâche

Cliquez sur une tâche pour voir :
- La description complète
- L'adresse exacte
- Les consignes particulières
- Les autres ouvriers assignés (si équipe)

---

## 4. Marquer une Tâche Terminée

1. Ouvrez la tâche concernée
2. Cliquez sur **"Marquer comme terminée"**
3. Ajoutez des notes si nécessaire (travail effectué, remarques)
4. Confirmez

La tâche passe au statut "Terminée" et l'administrateur est notifié.

---

## 5. Mon Planning

1. Cliquez sur **"Planning"** dans le menu
2. Visualisez vos interventions sur un calendrier
3. Les couleurs indiquent le statut des tâches
4. Cliquez sur une tâche pour voir les détails

---

## 6. Messages

### Consulter mes messages

1. Cliquez sur **"Messages"** dans le menu
2. La liste affiche vos conversations
3. Cliquez sur une conversation pour lire les messages

### Répondre à un message

1. Ouvrez la conversation
2. Tapez votre réponse dans le champ en bas
3. Cliquez sur **"Envoyer"**

---

## 7. Notifications

L'icône cloche 🔔 en haut de l'écran affiche vos notifications :
- Nouvelles tâches assignées
- Messages reçus
- Rappels d'échéance

Cliquez sur une notification pour accéder directement à l'élément concerné.

---

## 8. Déconnexion

1. Cliquez sur votre nom en haut à droite
2. Cliquez sur **"Déconnexion"**

---

# Guide Client

## 1. Connexion

1. Rendez-vous sur le site NetExpress
2. Cliquez sur **"Connexion"** ou **"Espace Client"**
3. Entrez votre email et mot de passe
4. Cliquez sur **"Se connecter"**

Si vous n'avez pas encore de compte, demandez à Nettoyage Express de vous en créer un.

---

## 2. Mon Espace Client

Votre espace client affiche :

| Section | Information |
|---------|-------------|
| **Mes devis** | Tous vos devis reçus |
| **Mes factures** | Toutes vos factures |
| **Messages** | Vos échanges avec l'entreprise |

---

## 3. Mes Devis

### Consulter mes devis

1. Cliquez sur **"Mes Devis"**
2. La liste affiche tous vos devis avec :
   - Numéro du devis
   - Date
   - Montant
   - Statut

### Voir le détail d'un devis

1. Cliquez sur un devis
2. Consultez le détail des prestations proposées
3. Vérifiez les montants

### Télécharger un devis en PDF

1. Ouvrez le devis
2. Cliquez sur **"Télécharger PDF"**
3. Le fichier se télécharge sur votre ordinateur

---

## 4. Accepter ou Refuser un Devis

Lorsque vous recevez un nouveau devis par email :

### Par email (recommandé)

1. Ouvrez l'email reçu de Nettoyage Express
2. Cliquez sur le lien **"Consulter le devis"**
3. Entrez le code de validation reçu dans l'email
4. Consultez le devis en détail
5. Cliquez sur **"Accepter"** ou **"Refuser"**

### Depuis votre espace client

1. Connectez-vous à votre espace
2. Cliquez sur **"Mes Devis"**
3. Ouvrez le devis concerné
4. Cliquez sur **"Accepter"** ou **"Refuser"**

---

## 5. Mes Factures

### Consulter mes factures

1. Cliquez sur **"Mes Factures"**
2. La liste affiche toutes vos factures

### Voir le détail d'une facture

1. Cliquez sur une facture
2. Consultez :
   - Les prestations facturées
   - Les montants HT et TTC
   - La date d'échéance de paiement

### Télécharger une facture en PDF

1. Ouvrez la facture
2. Cliquez sur **"Télécharger PDF"**
3. Conservez ce document pour votre comptabilité

---

## 6. Contacter l'entreprise

### Par messagerie interne

1. Cliquez sur **"Messages"** dans votre espace
2. Cliquez sur **"Nouveau message"**
3. Rédigez votre message
4. Cliquez sur **"Envoyer"**

### Par téléphone

- **Fixe** : 05 94 30 23 68
- **Mobile** : 06 94 46 20 12

### Par email

- **Email** : contact@nettoyageexpresse.fr

---

## 7. Demander un Nouveau Devis

### Option 1 : Depuis le site public

1. Allez sur la page d'accueil
2. Cliquez sur **"Devis Express"**
3. Remplissez le formulaire de demande
4. Vous serez recontacté rapidement

### Option 2 : Par message

1. Connectez-vous à votre espace client
2. Envoyez un message décrivant votre besoin
3. L'équipe vous enverra un devis personnalisé

---

## 8. Déconnexion

1. Cliquez sur votre nom en haut à droite
2. Cliquez sur **"Déconnexion"**

---

# Assistance et Contact

## Besoin d'aide ?

| Moyen | Contact |
|-------|---------|
| **Téléphone** | 05 94 30 23 68 |
| **Mobile** | 06 94 46 20 12 |
| **Email** | contact@nettoyageexpresse.fr |
| **Adresse** | 753, Chemin de la Désirée, 97351 Matoury |

## Horaires d'assistance

- **Lundi à Vendredi** : 8h00 - 18h00
- **Samedi** : 8h00 - 12h00

## Problèmes fréquents

### J'ai oublié mon mot de passe

1. Sur la page de connexion, cliquez sur **"Mot de passe oublié"**
2. Entrez votre adresse email
3. Consultez votre boîte mail
4. Cliquez sur le lien reçu
5. Créez un nouveau mot de passe

### Je ne reçois pas les emails

1. Vérifiez votre dossier **Spam** ou **Courrier indésirable**
2. Ajoutez contact@nettoyageexpresse.fr à vos contacts
3. Si le problème persiste, contactez-nous par téléphone

### L'application ne s'affiche pas correctement

1. Essayez d'actualiser la page (touche F5)
2. Videz le cache de votre navigateur
3. Essayez avec un autre navigateur (Chrome, Firefox, Edge)

---

**© 2025 Nettoyage Express — Tous droits réservés**

*Document créé pour la version 1.0 de NetExpress*

