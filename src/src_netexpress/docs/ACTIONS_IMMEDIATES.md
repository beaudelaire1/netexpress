# Actions Immédiates - NetExpress

**Date de création** : 2025-01-27  
**Priorité** : Actions critiques identifiées lors de l'audit architectural

---

## 🔴 Actions Critiques (À faire cette semaine)

### 1. ✅ Nettoyage des fichiers de test à la racine - TERMINÉ

**Problème** : Des fichiers de test sont présents à la racine du projet au lieu d'être dans `tests/`.

**Fichiers concernés** :
- `test_smtp_brevo.py`
- `test_smtp.py`
- `test_email_console.py`

**Action effectuée** :
- ✅ Déplacés vers `scripts/` (scripts de diagnostic SMTP)
- ✅ Conservés car utiles pour le debugging de la configuration email

**Impact** : Organisation améliorée, fichiers à leur place logique

---

### 2. ✅ Middleware - Vérifié

**État** : Un seul fichier middleware existe (`accounts/middleware.py`), utilisé dans `settings/base.py`.

**Action** : Aucune action nécessaire - le middleware est propre et fonctionnel.

---

### 3. ✅ Décorateurs - Corrigé

**État** : Un seul fichier décorateurs existe (`core/decorators.py`).

**Action effectuée** :
- ✅ Ajout du décorateur `admin_portal_required` manquant (utilisé dans `core/views.py`)
- ✅ Le fichier est complet et fonctionnel

**Note** : Le système de permissions granulaires (ligne 110-133) utilise un mapping temporaire rôle → permissions. Une amélioration future pourrait utiliser Django Permissions.

---

## 🟡 Actions Importantes (À faire ce mois)

### 4. Documentation du TODO permissions granulaires

**Problème** : Un TODO existe dans `core/decorators_v2.py` ligne 313 concernant les permissions granulaires.

**Contexte** : Le système utilise actuellement les rôles comme proxy pour les permissions.

**Action** :
- [ ] Créer une issue/tâche dans la feuille de route pour ce TODO
- [ ] Documenter la décision : faut-il vraiment des permissions granulaires ?
- [ ] Si oui, définir le scope et la priorité

**Impact** : Clarification des besoins, planification

---

### 5. ✅ Backend email - Nettoyé

**État** : `brevo_backend_old.py` n'était pas utilisé (seulement `brevo_backend.py` dans les settings).

**Action effectuée** :
- ✅ Supprimé `core/backends/brevo_backend_old.py`
- ✅ Seul `brevo_backend.py` reste (utilisé dans dev.py et prod.py)

**Impact** : Nettoyage effectué, code simplifié

---

### 6. Vérification de l'application CRM

**Problème** : Le dossier `crm/` existe mais semble vide (seulement migrations).

**Action** :
- [ ] Vérifier si cette app est utilisée
- [ ] Si non utilisée : supprimer OU documenter pourquoi elle existe
- [ ] Si utilisée : documenter son rôle dans `docs/ARCHITECTURE.md`

**Impact** : Clarification de l'architecture

---

## 🟢 Actions de Maintenance (À faire trimestriellement)

### 7. Review des scripts d'analyse

**Fichiers** :
- `scripts/analyze_dashboard_features.py`
- `scripts/migrate_dashboard_rationalization.py`

**Action** :
- [ ] Vérifier si ces scripts sont encore nécessaires
- [ ] Documenter leur utilité ou les supprimer
- [ ] Si conservés, les documenter dans `docs/`

**Impact** : Maintenance, documentation

---

### 8. Audit des dépendances

**Action** :
- [ ] Vérifier les versions des dépendances dans `requirements/base.txt`
- [ ] Identifier les dépendances obsolètes ou non utilisées
- [ ] Mettre à jour si nécessaire

**Impact** : Sécurité, maintenance

---

## 📋 Checklist de Validation

Avant de supprimer un fichier :

- [ ] Vérifier qu'il n'est pas importé ailleurs (`grep -r "nom_du_fichier"`)
- [ ] Vérifier qu'il n'est pas référencé dans les settings
- [ ] Vérifier qu'il n'est pas utilisé dans les migrations
- [ ] Tester que l'application fonctionne toujours après suppression
- [ ] Commit avec message clair expliquant la suppression

---

## 🎯 Priorisation

**Cette semaine** :
1. Nettoyage fichiers de test (Action 1)
2. Vérification middleware (Action 2)
3. Vérification décorateurs (Action 3)

**Ce mois** :
4. Documentation TODO (Action 4)
5. Audit backend email (Action 5)
6. Vérification CRM (Action 6)

**Trimestriel** :
7. Review scripts (Action 7)
8. Audit dépendances (Action 8)

---

## 📝 Notes

- Toutes les actions doivent être testées avant commit
- Documenter les décisions dans `docs/DECISIONS.md` si nécessaire
- Mettre à jour `docs/ARCHITECTURE.md` si des changements structurels sont effectués

---

**Dernière mise à jour** : 2025-01-27  
**Prochaine révision** : Après complétion des actions critiques

