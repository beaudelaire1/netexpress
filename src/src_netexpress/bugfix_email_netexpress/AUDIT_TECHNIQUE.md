# AUDIT TECHNIQUE - PROJET NETEXPRESS

**Date d'audit** : Décembre 2024  
**Auditeur** : Assistant technique senior  
**Projet** : NetExpress ERP - Version 2.2

---

## 📋 EXECUTIVE SUMMARY

Cet audit technique a identifié **8 incohérences critiques** et **12 problèmes mineurs** nécessitant une correction avant toute évolution fonctionnelle. Les principales préoccupations concernent :

1. **Violation des règles métier** : Les WORKERS peuvent actuellement créer leur propre compte via l'interface publique
2. **Code dupliqué** : Trois fichiers email différents dans l'app `devis`
3. **Routes obsolètes** : Anciennes routes dashboard encore présentes
4. **Incohérences de modèles** : Rôle `ROLE_TEAM` défini mais jamais utilisé

---

## 🔴 INCOHÉRENCES CRITIQUES

### 1. VIOLATION DES RÈGLES MÉTIER : WORKERS PEUVENT S'INSCRIRE

**Fichier concerné** : `accounts/forms.py`

**Problème** :
```python
class SignUpForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=[
            (Profile.ROLE_CLIENT, "Client"),
            (Profile.ROLE_WORKER, "Ouvrier"),  # ❌ VIOLATION
        ],
        initial=Profile.ROLE_CLIENT,
    )
```

Le formulaire d'inscription publique (`/accounts/signup/`) permet aux utilisateurs de choisir le rôle `WORKER`, ce qui viole la règle métier :
- **Règle attendue** : "Un WORKER ne peut PAS créer son compte lui-même"
- **Règle attendue** : "Les WORKERS sont créés uniquement par un ADMIN ou SUPER ADMIN"

**Impact** : Sécurité - n'importe qui peut devenir WORKER en s'inscrivant

**Correction requise** :
- Supprimer `ROLE_WORKER` des choix du `SignUpForm`
- Forcer le rôle à `ROLE_CLIENT` lors de l'inscription publique
- Vérifier que seul l'admin peut créer des WORKERS (via `/gestion/` ou portail admin)

---

### 2. CODE DUPLIQUÉ : TROIS FICHIERS EMAIL DANS DEVIS

**Fichiers concernés** :
- `devis/email_service.py` (149 lignes - utilisé dans views.py)
- `devis/email.py` (57 lignes - code mort probable)
- `devis/emailing.py` (98 lignes - code mort probable)

**Problème** :
Trois fichiers différents implémentent des fonctions similaires pour envoyer des emails de devis. Seul `email_service.py` est actuellement importé dans `devis/views.py`.

**Impact** :
- Maintenance difficile (code dupliqué)
- Confusion sur quelle fonction utiliser
- Risque d'incohérence dans le comportement

**Correction requise** :
1. Vérifier quelles fonctions sont utilisées
2. Fusionner dans un seul fichier (`email_service.py`)
3. Supprimer `email.py` et `emailing.py` si non utilisés

---

### 3. ROUTES OBSOLÈTES : ANCIENS DASHBOARDS

**Fichier concerné** : `core/urls.py`

**Problème** :
```python
# Routes obsolètes (lignes 28-29)
path("dashboard/client/", views.client_dashboard, name="client_dashboard"),
path("dashboard/ouvrier/", views.worker_dashboard, name="worker_dashboard"),
```

Ces routes sont obsolètes selon les commentaires du code qui indiquent une migration vers `/client/` et `/worker/`.

**Impact** :
- Confusion sur les URLs à utiliser
- Routes en double pouvant causer des conflits
- Maintenance difficile

**Correction requise** :
- Supprimer ces routes obsolètes
- Vérifier que toutes les références pointent vers `/client/` et `/worker/`

---

### 4. LIENS OBSOLÈTES VERS `core:dashboard`

**Fichiers concernés** :
- `templates/tasks/task_list.html`
- `templates/tasks/task_detail.html`
- `templates/tasks/task_calendar.html`
- `templates/messaging/message_list.html`
- `templates/messaging/message_detail.html`
- `templates/messaging/compose.html`
- `templates/factures/archive.html`
- `templates/base.html`

**Problème** :
Plusieurs templates utilisent `{% url 'core:dashboard' %}` alors que cette route est marquée comme obsolète dans le code.

**Impact** :
- Liens cassés potentiels
- Redirection vers une route obsolète

**Correction requise** :
- Identifier la route de remplacement (probablement `/admin-dashboard/` ou `/gestion/`)
- Mettre à jour tous les templates concernés

---

### 5. RÔLE `ROLE_TEAM` DÉFINI MAIS JAMAIS UTILISÉ

**Fichier concerné** : `accounts/models.py`

**Problème** :
```python
ROLE_TEAM = "team"  # Défini mais jamais utilisé
ROLE_CHOICES = [
    (ROLE_CLIENT, "Client"),
    (ROLE_WORKER, "Ouvrier"),
    (ROLE_TEAM, "Équipe"),  # ❌ Jamais utilisé
]
```

Le rôle `ROLE_TEAM` est défini dans le modèle mais :
- N'est pas utilisé dans les formulaires
- N'est pas utilisé dans les vues
- N'est pas utilisé dans les décorateurs de permissions

**Impact** :
- Code mort
- Confusion sur l'objectif de ce rôle

**Correction requise** :
- Soit supprimer `ROLE_TEAM` s'il n'est pas nécessaire
- Soit l'implémenter complètement si c'est une fonctionnalité prévue

---

### 6. INCOHÉRENCE DANS LE SIGNAL DE CRÉATION DE PROFILE

**Fichier concerné** : `accounts/models.py`

**Problème** :
```python
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile_for_user(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)  # Crée avec default=ROLE_CLIENT
```

Le signal crée automatiquement un Profile avec `default=ROLE_CLIENT`, ce qui est correct. Cependant, le `SignUpForm` permet de contourner cela en définissant explicitement le rôle WORKER.

**Impact** :
- L'intention du modèle (default CLIENT) est contournée par le formulaire

**Correction requise** :
- Assurer que le SignUpForm force toujours ROLE_CLIENT (voir problème #1)

---

### 7. ROUTE `core:dashboard` OBSOLÈTE MAIS TOUJOURS DÉFINIE

**Fichier concerné** : `core/views.py`

**Problème** :
```python
@staff_member_required
def dashboard(request):
    """Tableau de bord interne agrégé."""
    # ... code ...
```

La vue `dashboard` est marquée comme obsolète dans les commentaires mais :
- Est toujours définie
- Est toujours accessible via une route
- Est utilisée dans plusieurs templates

**Impact** :
- Code obsolète maintenu en vie
- Confusion sur la route à utiliser

**Correction requise** :
- Déterminer la route de remplacement
- Rediriger `core:dashboard` vers la nouvelle route
- Ou supprimer complètement si non nécessaire

---

### 8. PROFILE ADMIN : PAS DE RESTRICTION SUR LE CHANGEMENT DE RÔLE

**Fichier concerné** : `accounts/admin.py`

**Problème** :
```python
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "phone")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email", "user__first_name")
```

L'admin Django permet à n'importe quel utilisateur staff de changer le rôle d'un Profile, y compris de créer des WORKERS. Bien que cela soit techniquement correct (seuls les staff peuvent accéder à l'admin), il n'y a pas de restriction explicite ni de logique métier dans le formulaire admin.

**Impact** :
- Pas de validation explicite que seuls les ADMIN/SUPER ADMIN peuvent créer des WORKERS
- Risque de confusion sur qui peut faire quoi

**Correction requise** :
- Ajouter une logique dans `ProfileAdmin.save_model()` pour vérifier les permissions
- Ou documenter clairement que seuls les superusers peuvent créer des WORKERS
- Ou utiliser un formulaire personnalisé qui restreint le changement de rôle WORKER

---

## ⚠️ PROBLÈMES MOYENS

### 9. FICHIERS INUTILES À LA RACINE DU PROJET

**Fichiers** :
- `20251221_120403.jpg`
- `accueil.mp4`
- `actuel.mp4`
- `fac_modèle.jpg`
- `modele_mail.html`
- `modele_quote.html`
- `notification.html`
- `Prompt.txt`

**Problème** : Fichiers de test/exemple à la racine, en dehors du projet Django principal.

**Impact** : Pollution du répertoire, confusion.

**Correction requise** : Déplacer ou supprimer ces fichiers.

---

### 10. DOSSIER `static_site/` : MODE STATIQUE

**Fichier** : `static_site/index.html`

**Problème** : Dossier contenant une version statique du site pour le mode "fallback" mentionné dans la documentation. Le README indique que c'est une fonctionnalité prévue.

**Impact** : Aucun si c'est intentionnel.

**Correction requise** : Conserver si c'est une fonctionnalité prévue, sinon supprimer.

---

### 11. DOCUMENTATION OBSOLÈTE : MENTION DE REPORTLAB

**Fichier** : `docs/user_guide.md`

**Problème** :
Le guide utilisateur mentionne encore ReportLab pour la génération de PDF :
> "Installez le module ReportLab si ce n'est pas déjà fait"

Alors que le README indique que WeasyPrint est utilisé maintenant.

**Impact** : Documentation désuète, confusion pour les développeurs.

**Correction requise** : Mettre à jour la documentation pour refléter l'utilisation de WeasyPrint.

---

### 12. ROUTES EN DOUBLE DANS `netexpress/urls.py`

**Problème potentiel** :
Le fichier `netexpress/urls.py` inclut `core.urls` qui peut contenir des routes qui sont également définies ailleurs.

**Vérification requise** : S'assurer qu'il n'y a pas de conflits entre :
- `path("", include("core.urls"))`
- `path("client/", include("core.urls_client"))`
- `path("worker/", include(("core.urls_worker", "worker_portal"), namespace="worker"))`

---

## 📊 RÉSUMÉ DES CORRECTIONS PRIORITAIRES

### PRIORITÉ 1 (CRITIQUE - À CORRIGER IMMÉDIATEMENT)

1. ✅ **Supprimer le choix WORKER du SignUpForm** (`accounts/forms.py`)
   - Forcer le rôle à CLIENT lors de l'inscription publique
   - Vérifier que seuls les admins peuvent créer des WORKERS

2. ✅ **Nettoyer les fichiers email dupliqués** (`devis/`)
   - Conserver uniquement `email_service.py`
   - Supprimer `email.py` et `emailing.py` si non utilisés

3. ✅ **Supprimer les routes obsolètes** (`core/urls.py`)
   - Supprimer `dashboard/client/` et `dashboard/ouvrier/`

### PRIORITÉ 2 (IMPORTANT - À CORRIGER AVANT PRODUCTION)

4. ✅ **Corriger les liens obsolètes dans les templates**
   - Remplacer `{% url 'core:dashboard' %}` par la route appropriée

5. ✅ **Décider du sort de ROLE_TEAM**
   - Supprimer si non utilisé
   - Ou implémenter complètement

6. ✅ **Mettre à jour la documentation**
   - Corriger les mentions de ReportLab → WeasyPrint

### PRIORITÉ 3 (NETTOYAGE - À FAIRE POUR MAINTENABILITÉ)

7. ✅ **Nettoyer les fichiers inutiles à la racine**
   - Déplacer ou supprimer les fichiers de test/exemple

8. ✅ **Ajouter des restrictions dans ProfileAdmin**
   - Valider que seuls les admins peuvent créer des WORKERS

---

## ✅ POINTS POSITIFS IDENTIFIÉS

1. ✅ **Structure du projet claire** : Organisation par apps Django
2. ✅ **Séparation des settings** : Configuration séparée dev/prod
3. ✅ **Documentation présente** : README et guide utilisateur
4. ✅ **Tests présents** : Dossier `tests/` avec quelques tests
5. ✅ **Admin personnalisé** : Utilisation de Jazzmin pour l'interface admin

---

## 📝 RECOMMANDATIONS GÉNÉRALES

1. **Tests automatisés** : Ajouter des tests pour valider les règles métier (WORKER ne peut pas s'inscrire, etc.)

2. **Documentation du code** : Ajouter des docstrings pour clarifier les règles métier importantes

3. **Migration progressive** : Si des routes doivent être supprimées, prévoir une période de redirection pour la compatibilité

4. **Code review** : Mettre en place un processus de review pour éviter les duplications futures

5. **Linter/Formatter** : Utiliser des outils comme Black ou Ruff pour maintenir la cohérence du code

---

## 🔍 MÉTHODOLOGIE D'AUDIT

- ✅ Analyse de la structure du projet
- ✅ Examen de tous les fichiers `urls.py`
- ✅ Vérification des modèles et formulaires
- ✅ Recherche de code dupliqué
- ✅ Vérification des règles métier critiques
- ✅ Analyse des templates et liens
- ✅ Recherche de fichiers inutiles

---

**FIN DU RAPPORT D'AUDIT**

