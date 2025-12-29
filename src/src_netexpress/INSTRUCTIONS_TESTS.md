# INSTRUCTIONS D'EXÉCUTION DES TESTS - NETEXPRESS ERP

## 📦 Installation des Dépendances

Avant d'exécuter les tests, installer les dépendances de test :

```bash
cd bugfix_email_netexpress
pip install pytest pytest-django pytest-cov
```

**Optionnel (recommandé) :**
```bash
pip install pytest-xdist  # Pour parallélisation
pip install pytest-sugar  # Pour meilleur affichage
```

---

## 🚀 Exécution des Tests

### Tests Complets

Exécuter tous les tests :
```bash
pytest
```

### Tests par Priorité

**Tests critiques uniquement (Priorité 1) :**
```bash
pytest -m critical
```

**Tests de permissions :**
```bash
pytest -m permissions
```

**Tests métier :**
```bash
pytest -m business
```

### Tests par Module

**Tests des devis :**
```bash
pytest tests/business/test_quote_workflow.py
```

**Tests des factures :**
```bash
pytest tests/business/test_invoice_workflow.py
```

**Tests des tâches :**
```bash
pytest tests/business/test_task_business.py
```

**Tests permissions client :**
```bash
pytest tests/permissions/test_client_permissions.py
```

**Tests permissions worker :**
```bash
pytest tests/permissions/test_worker_permissions.py
```

**Tests permissions admin :**
```bash
pytest tests/permissions/test_admin_permissions.py
```

### Tests par Fonction

**Un test spécifique :**
```bash
pytest tests/business/test_quote_workflow.py::TestQuoteCreationAndCalculations::test_quote_creation_with_items_calculates_totals
```

---

## 📊 Couverture de Code

### Générer le rapport de couverture

```bash
pytest --cov=devis --cov=factures --cov=tasks --cov=accounts --cov=core --cov-report=html
```

**Consulter le rapport :**
```bash
# Ouvrir htmlcov/index.html dans un navigateur
start htmlcov/index.html  # Windows
open htmlcov/index.html   # macOS
xdg-open htmlcov/index.html  # Linux
```

### Couverture minimale par module

```bash
pytest --cov=devis --cov-report=term --cov-fail-under=85
```

---

## ⚡ Optimisation des Tests

### Exécution en parallèle

```bash
pytest -n auto  # Utilise tous les CPU disponibles
pytest -n 4     # Utilise 4 workers
```

### Tests rapides uniquement

```bash
pytest -m "not slow"
```

### Mode verbeux

```bash
pytest -vv  # Très verbeux
```

### Arrêt au premier échec

```bash
pytest -x
```

### Afficher les print()

```bash
pytest -s
```

### Debugger en cas d'échec

```bash
pytest --pdb
```

---

## 🔍 Filtrage Avancé

### Tests contenant un mot-clé

```bash
pytest -k "quote"        # Tous les tests avec "quote" dans le nom
pytest -k "not admin"    # Exclure les tests avec "admin"
```

### Tests modifiés récemment

```bash
pytest --lf  # Last Failed (re-exécuter les échecs)
pytest --ff  # Failed First (échecs en premier)
```

---

## 📋 Vérification des Tests

### Lister tous les tests

```bash
pytest --collect-only
```

### Compter les tests

```bash
pytest --collect-only -q
```

### Vérifier la configuration

```bash
pytest --version
pytest --fixtures  # Lister les fixtures disponibles
```

---

## 🐛 Debugging

### Exécuter avec trace complète

```bash
pytest --tb=long
```

### Afficher les variables locales

```bash
pytest -l
```

### Mode interactif

```bash
pytest --pdb --pdbcls=IPython.terminal.debugger:Pdb
```

---

## 📈 Rapports

### Rapport JUnit (pour CI/CD)

```bash
pytest --junit-xml=report.xml
```

### Rapport HTML

```bash
pytest --html=report.html --self-contained-html
```

---

## ✅ Checklist Avant Commit

```bash
# 1. Tests critiques
pytest -m critical

# 2. Couverture minimale
pytest --cov=devis --cov=factures --cov=tasks --cov-fail-under=80

# 3. Pas de warnings
pytest --strict-warnings

# 4. Linter
ruff check .
black --check .

# 5. Migrations
python manage.py makemigrations --check --dry-run
```

---

## 🎯 Objectifs de Couverture

| Module | Couverture Cible | Priorité |
|--------|------------------|----------|
| `devis/` | ≥ 85% | 🔴 Critique |
| `factures/` | ≥ 85% | 🔴 Critique |
| `tasks/` | ≥ 80% | 🟡 Important |
| `accounts/` | ≥ 75% | 🟡 Important |
| `core/` | ≥ 70% | 🟢 Souhaitable |

---

## 🔧 Dépannage

### Erreur "No module named 'pytest'"

```bash
pip install pytest pytest-django
```

### Erreur "django.core.exceptions.ImproperlyConfigured"

Vérifier que `DJANGO_SETTINGS_MODULE` est défini dans `pytest.ini` :
```ini
DJANGO_SETTINGS_MODULE = netexpress.settings.dev
```

### Erreur de base de données

Django crée automatiquement une DB de test. Vérifier les permissions :
```bash
python manage.py test --keepdb  # Garde la DB entre les exécutions
```

### Tests lents

Utiliser pytest-xdist pour paralléliser :
```bash
pytest -n auto
```

---

## 📚 Documentation

- **Pytest :** https://docs.pytest.org/
- **Pytest-Django :** https://pytest-django.readthedocs.io/
- **Pytest-Cov :** https://pytest-cov.readthedocs.io/

---

## 🎓 Bonnes Pratiques

1. **Toujours exécuter les tests avant de commit**
2. **Maintenir une couverture ≥ 80%**
3. **Tests critiques en < 15 secondes**
4. **Suite complète en < 60 secondes**
5. **Utiliser les fixtures pour réduire la duplication**
6. **Isoler les tests (pas de dépendances entre eux)**
7. **Noms de tests explicites (test_should_xxx_when_yyy)**
8. **Un test = une assertion principale**

---

## 📞 Support

En cas de problème avec les tests :
1. Vérifier les logs : `pytest -vv --tb=long`
2. Consulter le plan de tests : `PLAN_TESTS_NETEXPRESS.md`
3. Vérifier les fixtures : `bugfix_email_netexpress/tests/conftest.py`

---

**Dernière mise à jour :** 28 Décembre 2025  
**Version :** 2.2

