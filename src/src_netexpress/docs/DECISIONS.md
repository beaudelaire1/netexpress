# Décisions Architecturales - NetExpress

**Version:** 1.0  
**Date:** 2025-01-27

Ce document enregistre les décisions architecturales importantes prises pour NetExpress, avec leur contexte et leur justification.

---

## Format des décisions

Chaque décision suit le format suivant :

- **ID** : Identifiant unique
- **Date** : Date de la décision
- **Statut** : Proposé | Accepté | Rejeté | Déprécié
- **Contexte** : Situation qui a nécessité la décision
- **Décision** : Ce qui a été décidé
- **Conséquences** : Impact de la décision

---

## Décisions

### ADR-001 : Architecture modulaire Django

**Date** : 2025-01-27  
**Statut** : Accepté

**Contexte** :
Le projet nécessite une organisation claire des fonctionnalités métier (devis, factures, tâches, etc.) tout en restant simple et maintenable.

**Décision** :
Utiliser une architecture modulaire Django avec une application par domaine métier. Chaque application est autonome et peut être développée/maintenue indépendamment.

**Conséquences** :
- ✅ Séparation claire des responsabilités
- ✅ Code organisé et facile à naviguer
- ✅ Possibilité de réutiliser les apps dans d'autres projets
- ⚠️ Nécessite une discipline pour éviter les dépendances circulaires

---

### ADR-002 : Système multi-portails

**Date** : 2025-01-27  
**Statut** : Accepté

**Contexte** :
Les besoins des différents profils utilisateurs (client, ouvrier, admin) sont très différents et nécessitent des interfaces dédiées.

**Décision** :
Implémenter 4 portails séparés avec URLs dédiées :
- `/client/` pour les clients
- `/worker/` pour les ouvriers
- `/admin-dashboard/` pour les admins business
- `/gestion/` pour les admins techniques (Django Admin)

**Conséquences** :
- ✅ Expérience utilisateur optimale par profil
- ✅ Sécurité renforcée (isolation des accès)
- ✅ Maintenance facilitée (code séparé par portail)
- ⚠️ Plus de code à maintenir (4 interfaces)
- ⚠️ Nécessite un middleware de routage

---

### ADR-003 : Middleware de contrôle d'accès

**Date** : 2025-01-27  
**Statut** : Accepté

**Contexte** :
Le contrôle d'accès aux portails doit être centralisé et cohérent pour éviter les failles de sécurité.

**Décision** :
Implémenter un middleware `RoleBasedAccessMiddleware` qui intercepte toutes les requêtes et redirige les utilisateurs vers leur portail approprié selon leur rôle.

**Conséquences** :
- ✅ Contrôle d'accès centralisé et cohérent
- ✅ Sécurité renforcée (pas de contournement possible)
- ✅ Logs centralisés pour le debugging
- ⚠️ Performance légèrement impactée (middleware sur chaque requête)
- ⚠️ Nécessite une gestion soignée des URLs publiques

---

### ADR-004 : Architecture hexagonale partielle

**Date** : 2025-01-27  
**Statut** : En évaluation

**Contexte** :
Une tentative d'architecture hexagonale a été initiée dans le module `hexcore/` pour la facturation, mais elle n'est pas complètement intégrée.

**Décision** :
**DÉCISION EN ATTENTE** : Évaluer l'utilité de `hexcore/` avant de décider :
1. Compléter l'intégration si bénéfique
2. Supprimer si non utilisé
3. Maintenir tel quel si utile mais isolé

**Conséquences** :
- ⚠️ Architecture hybride (modulaire Django + hexagonale partielle)
- ⚠️ Complexité supplémentaire si généralisée
- ✅ Découplage du domaine métier si bien implémentée

**Action requise** : Audit de `hexcore/` (voir Phase 4 de la feuille de route)

---

### ADR-005 : Génération PDF avec deux bibliothèques

**Date** : 2025-01-27  
**Statut** : Accepté

**Contexte** :
Les besoins de génération PDF sont différents pour les devis (HTML simple) et les factures (mise en page complexe avec QR codes).

**Décision** :
- **Devis** : WeasyPrint (HTML → PDF, simple et flexible)
- **Factures** : ReportLab (génération programmatique, contrôle total)

**Conséquences** :
- ✅ Outil adapté à chaque besoin
- ✅ Flexibilité maximale
- ⚠️ Deux dépendances à maintenir
- ⚠️ Deux approches différentes à documenter

---

### ADR-006 : Celery pour les tâches asynchrones

**Date** : 2025-01-27  
**Statut** : Accepté

**Contexte** :
Les envois d'emails et générations de PDF peuvent être longs et ne doivent pas bloquer les requêtes HTTP.

**Décision** :
Utiliser Celery avec Redis comme broker pour toutes les tâches asynchrones (emails, PDF, notifications).

**Conséquences** :
- ✅ Expérience utilisateur améliorée (pas d'attente)
- ✅ Fiabilité (retry automatique)
- ✅ Scalabilité (workers multiples)
- ⚠️ Infrastructure supplémentaire (Redis + Celery workers)
- ⚠️ Complexité de déploiement augmentée

---

### ADR-007 : Notifications UI + Email

**Date** : 2025-01-27  
**Statut** : Accepté

**Contexte** :
Les utilisateurs doivent être informés des événements importants (devis validé, tâche assignée, etc.) de manière visible et persistante.

**Décision** :
Implémenter un système hybride :
- **Notifications UI** : Affichage dans l'interface (modèle `UINotification`)
- **Notifications Email** : Envoi par email via Celery

**Conséquences** :
- ✅ Double canal de communication (UI + email)
- ✅ Notifications persistantes (historique)
- ✅ Flexibilité (préférences utilisateur possibles)
- ⚠️ Synchronisation à maintenir entre UI et email

---

### ADR-008 : Settings modulaires

**Date** : 2025-01-27  
**Statut** : Accepté

**Contexte** :
Les configurations diffèrent entre développement, test et production. Il faut éviter la duplication et faciliter la maintenance.

**Décision** :
Organiser les settings en modules :
- `base.py` : Configuration commune
- `dev.py` : Développement (hérite de base)
- `prod.py` : Production (hérite de base)
- `test.py` : Tests (hérite de base)
- `local.py` : Overrides locaux (optionnel, gitignored)

**Conséquences** :
- ✅ Configuration claire et organisée
- ✅ Pas de duplication
- ✅ Facilite le déploiement
- ⚠️ Nécessite une discipline pour éviter les overrides incorrects

---

### ADR-009 : WhiteNoise pour les fichiers statiques

**Date** : 2025-01-27  
**Statut** : Accepté

**Contexte** :
En production, les fichiers statiques doivent être servis efficacement sans nécessiter un serveur web dédié (Nginx).

**Décision** :
Utiliser WhiteNoise pour servir les fichiers statiques directement depuis Django, avec compression et cache.

**Conséquences** :
- ✅ Déploiement simplifié (pas de Nginx requis)
- ✅ Performance acceptable pour un ERP léger
- ✅ Compression automatique
- ⚠️ Moins performant qu'un serveur web dédié (acceptable pour le volume attendu)

---

### ADR-010 : Jazzmin pour l'interface admin

**Date** : 2025-01-27  
**Statut** : Accepté

**Contexte** :
L'interface Django Admin par défaut est fonctionnelle mais peu attrayante. Les administrateurs business ont besoin d'une interface moderne.

**Décision** :
Utiliser Django Jazzmin pour améliorer l'interface admin (`/gestion/`) avec un thème moderne et personnalisable.

**Conséquences** :
- ✅ Interface moderne et professionnelle
- ✅ Personnalisation facile (logo, couleurs)
- ✅ Meilleure expérience utilisateur pour les admins
- ⚠️ Dépendance supplémentaire à maintenir
- ⚠️ Compatibilité avec les futures versions de Django à vérifier

---

## Décisions en attente

### ADR-PENDING-001 : API REST

**Date** : À définir  
**Statut** : Proposé

**Contexte** :
Des intégrations externes pourraient nécessiter une API REST.

**Question** : Faut-il implémenter une API REST maintenant ou attendre un besoin concret ?

**Options** :
1. Implémenter maintenant (proactivité)
2. Attendre un besoin concret (pragmatisme)

**Décision** : En attente de besoins métier concrets

---

### ADR-PENDING-002 : Tests automatisés

**Date** : À définir  
**Statut** : Proposé

**Contexte** :
La couverture de tests actuelle est partielle.

**Question** : Quel niveau de couverture viser et quels types de tests prioriser ?

**Options** :
1. Tests unitaires uniquement
2. Tests d'intégration uniquement
3. Mix (recommandé)

**Décision** : À définir selon les ressources disponibles

---

## Révisions

Ce document sera mis à jour à chaque décision architecturale majeure.

**Dernière mise à jour** : 2025-01-27  
**Prochaine révision** : Lors de la prochaine décision majeure

