# Tests NetExpress ERP

Suite de tests fonctionnels et métier pour l'ERP NetExpress.

## 📁 Structure

```
tests/
├── conftest.py                 # Fixtures communes (20+ fixtures)
├── test_models.py             # Tests modèles (existant)
├── test_devis_urls.py         # Tests URLs devis (existant)
├── test_devis_links.py        # Tests liens devis (existant)
│
├── business/                   # Tests métier (65 tests)
│   ├── test_quote_workflow.py      # Flux devis (20 tests)
│   ├── test_invoice_workflow.py    # Flux factures (18 tests)
│   ├── test_task_business.py       # Gestion tâches (15 tests)
│   └── test_business_rules.py      # Règles métier (12 tests)
│
└── permissions/                # Tests permissions (37 tests)
    ├── test_client_permissions.py  # Permissions client (12 tests)
    ├── test_worker_permissions.py  # Permissions worker (11 tests)
    └── test_admin_permissions.py   # Permissions admin (14 tests)
```

## 🚀 Démarrage Rapide

### Installation

```bash
pip install pytest pytest-django pytest-cov
```

### Exécution

```bash
# Tous les tests
pytest

# Tests critiques uniquement
pytest -m critical

# Tests d'un module spécifique
pytest tests/business/test_quote_workflow.py

# Avec couverture
pytest --cov=devis --cov=factures --cov=tasks --cov-report=html
```

## 🎯 Fixtures Disponibles

Toutes les fixtures sont définies dans `conftest.py` :

### Utilisateurs
- `user_client`, `user_worker`, `user_admin_business`, `user_superuser`
- `client_authenticated`, `client_worker`, `client_admin`, `client_superuser`

### Données Métier
- `customer`, `customer_alt`
- `quote_draft`, `quote_with_items`, `quote_sent`, `quote_accepted`
- `invoice_draft`, `invoice_with_items`, `invoice_from_quote`
- `task_upcoming`, `task_in_progress`, `task_overdue`
- `service_nettoyage`, `service_jardinage`
- `category_nettoyage`, `category_espaces_verts`

## 📊 Couverture

Objectifs de couverture :
- `devis/` : ≥ 85%
- `factures/` : ≥ 85%
- `tasks/` : ≥ 80%
- `accounts/` : ≥ 75%
- `core/` : ≥ 70%

## 🏷️ Marqueurs

Tests organisés par marqueurs pytest :

```python
@pytest.mark.critical      # Tests critiques (flux essentiels)
@pytest.mark.permissions   # Tests de permissions
@pytest.mark.business      # Tests règles métier
@pytest.mark.integration   # Tests d'intégration
@pytest.mark.slow          # Tests lents (> 1s)
```

## 📚 Documentation Complète

Voir les documents à la racine du projet :
- `PLAN_TESTS_NETEXPRESS.md` - Plan détaillé des tests
- `INSTRUCTIONS_TESTS.md` - Guide d'exécution
- `SYNTHESE_TESTS_NETEXPRESS.md` - Synthèse et livrables

## 🐛 Dépannage

### Erreur "No module named 'pytest'"
```bash
pip install pytest pytest-django
```

### Erreur de configuration Django
Vérifier `pytest.ini` à la racine :
```ini
DJANGO_SETTINGS_MODULE = netexpress.settings.dev
```

### Tests lents
```bash
pytest -n auto  # Parallélisation
```

## ✅ Bonnes Pratiques

1. Utiliser les fixtures au lieu de créer des données à la main
2. Isoler les tests (pas de dépendances entre eux)
3. Noms explicites : `test_should_xxx_when_yyy`
4. Une assertion principale par test
5. Exécuter les tests avant chaque commit

## 📞 Support

En cas de problème :
1. Vérifier les logs : `pytest -vv --tb=long`
2. Consulter la documentation
3. Examiner `conftest.py` pour les fixtures disponibles

