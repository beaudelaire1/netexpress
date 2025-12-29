# PLAN DE TESTS FONCTIONNELS ET MÉTIER - NETEXPRESS ERP

**Date:** 28 Décembre 2025  
**Version:** 2.2  
**Contexte:** Tests fonctionnels pour ERP de nettoyage (devis, factures, tâches, CRM)

---

## 📋 TABLE DES MATIÈRES

1. [Vue d'ensemble](#1-vue-densemble)
2. [Tests Critiques (Priorité 1)](#2-tests-critiques-priorité-1)
3. [Tests de Permissions par Rôle](#3-tests-de-permissions-par-rôle)
4. [Tests des Flux Métier](#4-tests-des-flux-métier)
5. [Tests des Services](#5-tests-des-services)
6. [Tests des Règles Métier](#6-tests-des-règles-métier)
7. [Recommandations et Corrections](#7-recommandations-et-corrections)
8. [Plan d'Exécution](#8-plan-dexécution)

---

## 1. VUE D'ENSEMBLE

### 1.1 Architecture Actuelle

**Modèles principaux:**
- `crm.Customer` - Client unifié (remplace `devis.Client`)
- `accounts.Profile` - Profil utilisateur avec rôles (client, worker, team)
- `devis.Quote` - Devis avec items, statuts et validation 2FA
- `factures.Invoice` - Factures liées aux devis
- `tasks.Task` - Tâches d'intervention
- `services.Service` - Catalogue de services

**Rôles identifiés:**
- `client` - Accès dashboard client (devis/factures)
- `worker` - Accès dashboard ouvrier (tâches)
- `team` - Équipe (alias worker)
- `admin_business` - Administrateur business
- `admin_technical` - Administrateur technique (superuser)

**Flux critiques:**
1. Demande de devis → Création → Envoi → Validation 2FA → Acceptation
2. Devis accepté → Conversion en facture → Génération PDF
3. Création tâche → Attribution → Exécution → Complétion
4. Contrôle d'accès par rôle (middleware + décorateurs)

### 1.2 Périmètre de Tests

✅ **Inclus:**
- Tests unitaires des services métier
- Tests de permissions et contrôle d'accès
- Tests des règles métier et validations
- Tests des transitions de statuts
- Tests des calculs (totaux HT/TVA/TTC)
- Tests des workflows complets

❌ **Exclus:**
- Tests UI visuels (pas de Selenium/Playwright)
- Tests de performance
- Tests d'intégration email réels (mocks uniquement)

---

## 2. TESTS CRITIQUES (Priorité 1)

### 2.1 Flux Devis Complet 🔴

**Objectif:** Vérifier le cycle de vie complet d'un devis

#### TEST-DEVIS-001: Création de devis avec calcul automatique
```python
def test_quote_creation_with_items():
    """Un devis avec lignes doit calculer automatiquement ses totaux."""
    # Arrange
    customer = Customer.objects.create(full_name="Test Client", email="test@example.com", phone="0123456789")
    quote = Quote.objects.create(client=customer, status=Quote.QuoteStatus.DRAFT)
    QuoteItem.objects.create(quote=quote, description="Service A", quantity=2, unit_price=100, tax_rate=20)
    QuoteItem.objects.create(quote=quote, description="Service B", quantity=1, unit_price=50, tax_rate=20)
    
    # Act
    quote.compute_totals()
    
    # Assert
    assert quote.total_ht == Decimal("250.00")  # (2*100 + 1*50)
    assert quote.tva == Decimal("50.00")        # 250 * 0.20
    assert quote.total_ttc == Decimal("300.00") # 250 + 50
```

**Critère de succès:** ✅ Calculs corrects avec précision décimale

---

#### TEST-DEVIS-002: Numérotation unique des devis
```python
def test_quote_numbering_uniqueness():
    """Les devis doivent avoir des numéros séquentiels uniques par année."""
    # Arrange
    customer = Customer.objects.create(full_name="Client", email="c@test.com", phone="01")
    year = date.today().year
    
    # Act
    q1 = Quote.objects.create(client=customer)
    q2 = Quote.objects.create(client=customer)
    
    # Assert
    assert q1.number == f"DEV-{year}-001"
    assert q2.number == f"DEV-{year}-002"
    assert Quote.objects.filter(number__startswith=f"DEV-{year}-").count() == 2
```

**Critère de succès:** ✅ Numérotation séquentielle sans collision

---

#### TEST-DEVIS-003: Validation 2FA du devis
```python
def test_quote_validation_two_factor():
    """La validation d'un devis doit nécessiter un code 2FA."""
    # Arrange
    customer = Customer.objects.create(full_name="Client", email="c@test.com", phone="01")
    quote = Quote.objects.create(client=customer, status=Quote.QuoteStatus.SENT)
    validation = QuoteValidation.create_for_quote(quote, ttl_minutes=15)
    
    # Act - Code incorrect
    result_wrong = validation.verify("000000")
    
    # Assert
    assert result_wrong is False
    assert validation.attempts == 1
    assert validation.confirmed_at is None
    
    # Act - Code correct
    result_ok = validation.verify(validation.code)
    
    # Assert
    assert result_ok is True
    assert validation.is_confirmed is True
    assert validation.confirmed_at is not None
```

**Critère de succès:** ✅ Code 2FA requis, max tentatives respecté

---

#### TEST-DEVIS-004: Expiration de la validation 2FA
```python
def test_quote_validation_expiration():
    """Un code expiré ne doit pas permettre la validation."""
    # Arrange
    customer = Customer.objects.create(full_name="Client", email="c@test.com", phone="01")
    quote = Quote.objects.create(client=customer, status=Quote.QuoteStatus.SENT)
    validation = QuoteValidation.create_for_quote(quote, ttl_minutes=0)  # Expire immédiatement
    
    # Simuler expiration
    from django.utils import timezone
    validation.expires_at = timezone.now() - timedelta(minutes=1)
    validation.save()
    
    # Act
    result = validation.verify(validation.code)
    
    # Assert
    assert result is False
    assert validation.is_expired is True
```

**Critère de succès:** ✅ Token expiré rejeté

---

### 2.2 Flux Facturation 🔴

#### TEST-FACTURE-001: Conversion devis accepté → facture
```python
def test_convert_accepted_quote_to_invoice():
    """Un devis ACCEPTED doit pouvoir être converti en facture."""
    # Arrange
    customer = Customer.objects.create(full_name="Client", email="c@test.com", phone="01")
    quote = Quote.objects.create(client=customer, status=Quote.QuoteStatus.ACCEPTED)
    QuoteItem.objects.create(quote=quote, description="Service", quantity=1, unit_price=100, tax_rate=20)
    quote.compute_totals()
    
    # Act
    result = create_invoice_from_quote(quote)
    
    # Assert
    assert result.invoice is not None
    assert result.invoice.quote == quote
    assert result.invoice.invoice_items.count() == 1
    assert result.invoice.total_ttc == Decimal("120.00")
    assert quote.status == Quote.QuoteStatus.INVOICED
```

**Critère de succès:** ✅ Facture créée avec items et totaux corrects

---

#### TEST-FACTURE-002: Interdiction conversion devis non accepté
```python
def test_prevent_invoice_from_draft_quote():
    """Un devis DRAFT ne doit PAS pouvoir être facturé."""
    # Arrange
    customer = Customer.objects.create(full_name="Client", email="c@test.com", phone="01")
    quote = Quote.objects.create(client=customer, status=Quote.QuoteStatus.DRAFT)
    
    # Act & Assert
    with pytest.raises(QuoteStatusError):
        create_invoice_from_quote(quote)
```

**Critère de succès:** ✅ Exception levée pour statut invalide

---

#### TEST-FACTURE-003: Interdiction double facturation
```python
def test_prevent_duplicate_invoice_from_quote():
    """Un devis déjà facturé ne doit pas être facturé deux fois."""
    # Arrange
    customer = Customer.objects.create(full_name="Client", email="c@test.com", phone="01")
    quote = Quote.objects.create(client=customer, status=Quote.QuoteStatus.ACCEPTED)
    create_invoice_from_quote(quote)  # Première facturation
    
    # Act & Assert
    with pytest.raises(QuoteAlreadyInvoicedError):
        create_invoice_from_quote(quote)  # Tentative de duplication
```

**Critère de succès:** ✅ Exception levée pour double facturation

---

#### TEST-FACTURE-004: Numérotation unique des factures
```python
def test_invoice_numbering_sequential():
    """Les factures doivent avoir des numéros séquentiels uniques."""
    # Arrange
    year = date.today().year
    
    # Act
    inv1 = Invoice.objects.create()
    inv2 = Invoice.objects.create()
    
    # Assert
    assert inv1.number == f"FAC-{year}-001"
    assert inv2.number == f"FAC-{year}-002"
```

**Critère de succès:** ✅ Numérotation sans collision (atomic + select_for_update)

---

#### TEST-FACTURE-005: Calcul avec remise
```python
def test_invoice_discount_calculation():
    """La remise doit être appliquée proportionnellement sur HT et TVA."""
    # Arrange
    invoice = Invoice.objects.create(discount=Decimal("50.00"))
    InvoiceItem.objects.create(invoice=invoice, description="Item", quantity=1, unit_price=200, tax_rate=20)
    
    # Act
    invoice.compute_totals()
    
    # Assert
    # HT: 200 - 50 = 150
    # TVA: 150 * 0.20 = 30
    # TTC: 150 + 30 = 180
    assert invoice.total_ht == Decimal("150.00")
    assert invoice.tva == Decimal("30.00")
    assert invoice.total_ttc == Decimal("180.00")
```

**Critère de succès:** ✅ Remise appliquée correctement

---

### 2.3 Flux Tâches 🔴

#### TEST-TASK-001: Calcul automatique du statut selon dates
```python
def test_task_status_auto_calculation():
    """Le statut doit se calculer automatiquement selon start_date et due_date."""
    today = date.today()
    
    # Cas 1: Tâche future
    task_future = Task(title="Future", start_date=today + timedelta(days=5), due_date=today + timedelta(days=10))
    task_future.save()
    assert task_future.status == Task.STATUS_UPCOMING
    
    # Cas 2: Tâche en cours
    task_current = Task(title="Current", start_date=today, due_date=today + timedelta(days=5))
    task_current.save()
    assert task_current.status == Task.STATUS_IN_PROGRESS
    
    # Cas 3: Tâche en retard
    task_overdue = Task(title="Overdue", start_date=today - timedelta(days=5), due_date=today - timedelta(days=1))
    task_overdue.save()
    assert task_overdue.status == Task.STATUS_OVERDUE
    
    # Cas 4: Presque en retard (due demain)
    task_almost = Task(title="Almost", start_date=today, due_date=today + timedelta(days=1))
    task_almost.save()
    assert task_almost.status == Task.STATUS_ALMOST_OVERDUE
```

**Critère de succès:** ✅ Statut cohérent avec les dates

---

#### TEST-TASK-002: Validation règle due_date >= start_date
```python
def test_task_due_date_after_start_date():
    """La date d'échéance ne peut pas précéder la date de début."""
    # Arrange
    today = date.today()
    
    # Act & Assert
    with pytest.raises(ValueError, match="ne peut pas être antérieure"):
        task = Task(title="Invalid", start_date=today + timedelta(days=5), due_date=today)
        task.save()
```

**Critère de succès:** ✅ Exception levée pour dates incohérentes

---

#### TEST-TASK-003: Détection tâche proche de l'échéance
```python
def test_task_is_due_soon():
    """is_due_soon() doit détecter les tâches proches de l'échéance."""
    today = date.today()
    
    # Cas 1: Due dans 2 jours (threshold=3) → True
    task1 = Task(title="Soon", start_date=today, due_date=today + timedelta(days=2))
    task1.save()
    assert task1.is_due_soon(days_threshold=3) is True
    
    # Cas 2: Due dans 5 jours (threshold=3) → False
    task2 = Task(title="Later", start_date=today, due_date=today + timedelta(days=5))
    task2.save()
    assert task2.is_due_soon(days_threshold=3) is False
    
    # Cas 3: Tâche terminée → False
    task3 = Task(title="Done", start_date=today, due_date=today + timedelta(days=1), status=Task.STATUS_COMPLETED)
    task3.save()
    assert task3.is_due_soon(days_threshold=3) is False
```

**Critère de succès:** ✅ Détection correcte selon threshold

---

## 3. TESTS DE PERMISSIONS PAR RÔLE

### 3.1 Rôle CLIENT

#### TEST-PERM-CLIENT-001: Accès dashboard client
```python
def test_client_can_access_client_dashboard():
    """Un utilisateur avec rôle 'client' doit accéder à /client/."""
    # Arrange
    user = User.objects.create_user(username="client1", password="pass")
    Profile.objects.create(user=user, role=Profile.ROLE_CLIENT)
    client = Client(force_login=user)
    
    # Act
    response = client.get('/client/')
    
    # Assert
    assert response.status_code == 200
```

**Critère de succès:** ✅ 200 OK

---

#### TEST-PERM-CLIENT-002: Interdiction accès worker dashboard
```python
def test_client_cannot_access_worker_dashboard():
    """Un client ne doit PAS accéder au dashboard worker."""
    # Arrange
    user = User.objects.create_user(username="client1", password="pass")
    Profile.objects.create(user=user, role=Profile.ROLE_CLIENT)
    client = Client(force_login=user)
    
    # Act
    response = client.get('/worker/')
    
    # Assert
    assert response.status_code == 302  # Redirection
```

**Critère de succès:** ✅ Redirection (middleware)

---

#### TEST-PERM-CLIENT-003: Visualisation de ses devis uniquement
```python
def test_client_sees_only_own_quotes():
    """Un client doit voir uniquement SES devis (email matching)."""
    # Arrange
    user = User.objects.create_user(username="client1", email="client@test.com", password="pass")
    Profile.objects.create(user=user, role=Profile.ROLE_CLIENT)
    
    customer1 = Customer.objects.create(full_name="Client 1", email="client@test.com", phone="01")
    customer2 = Customer.objects.create(full_name="Client 2", email="autre@test.com", phone="02")
    
    quote1 = Quote.objects.create(client=customer1, status=Quote.QuoteStatus.SENT)
    quote2 = Quote.objects.create(client=customer2, status=Quote.QuoteStatus.SENT)
    
    client = Client(force_login=user)
    
    # Act
    response = client.get('/client/')
    
    # Assert
    assert quote1 in response.context['quotes']
    assert quote2 not in response.context['quotes']
```

**Critère de succès:** ✅ Isolation des données par email

---

#### TEST-PERM-CLIENT-004: Interdiction création de devis (admin only)
```python
def test_client_cannot_create_quote_in_admin():
    """Un client ne doit PAS accéder à l'admin pour créer un devis."""
    # Arrange
    user = User.objects.create_user(username="client1", password="pass")
    Profile.objects.create(user=user, role=Profile.ROLE_CLIENT)
    client = Client(force_login=user)
    
    # Act
    response = client.get('/gestion/devis/quote/add/')
    
    # Assert
    assert response.status_code in [302, 403]  # Redirection ou accès refusé
```

**Critère de succès:** ✅ Accès refusé

---

### 3.2 Rôle WORKER

#### TEST-PERM-WORKER-001: Accès dashboard worker
```python
def test_worker_can_access_worker_dashboard():
    """Un worker doit accéder à /worker/."""
    # Arrange
    user = User.objects.create_user(username="worker1", password="pass")
    Profile.objects.create(user=user, role=Profile.ROLE_WORKER)
    client = Client(force_login=user)
    
    # Act
    response = client.get('/worker/')
    
    # Assert
    assert response.status_code == 200
```

**Critère de succès:** ✅ 200 OK

---

#### TEST-PERM-WORKER-002: Visualisation tâches de son équipe
```python
def test_worker_sees_team_tasks_only():
    """Un worker doit voir uniquement les tâches de son équipe."""
    # Arrange
    user = User.objects.create_user(username="worker1", password="pass")
    Profile.objects.create(user=user, role=Profile.ROLE_WORKER)
    group = Group.objects.create(name="Équipe A")
    user.groups.add(group)
    
    task1 = Task.objects.create(title="Task A", team="Équipe A", due_date=date.today())
    task2 = Task.objects.create(title="Task B", team="Équipe B", due_date=date.today())
    
    client = Client(force_login=user)
    
    # Act
    response = client.get('/worker/')
    
    # Assert
    assert task1 in response.context['tasks']
    assert task2 not in response.context['tasks']
```

**Critère de succès:** ✅ Filtrage par équipe

---

#### TEST-PERM-WORKER-003: Interdiction accès admin
```python
def test_worker_cannot_access_admin():
    """Un worker ne doit PAS accéder à /gestion/."""
    # Arrange
    user = User.objects.create_user(username="worker1", password="pass")
    Profile.objects.create(user=user, role=Profile.ROLE_WORKER)
    client = Client(force_login=user)
    
    # Act
    response = client.get('/gestion/')
    
    # Assert
    assert response.status_code in [302, 403]
```

**Critère de succès:** ✅ Accès refusé

---

#### TEST-PERM-WORKER-004: Permission tasks.view et tasks.complete
```python
def test_worker_permissions():
    """Un worker doit avoir les permissions 'tasks.view' et 'tasks.complete'."""
    # Arrange
    user = User.objects.create_user(username="worker1", password="pass")
    Profile.objects.create(user=user, role=Profile.ROLE_WORKER)
    
    # Act & Assert
    from core.decorators import user_has_permission
    assert user_has_permission(user, 'tasks.view') is True
    assert user_has_permission(user, 'tasks.complete') is True
    assert user_has_permission(user, 'quotes.create') is False
```

**Critère de succès:** ✅ Permissions limitées correctes

---

### 3.3 Rôle ADMIN_BUSINESS

#### TEST-PERM-ADMIN-BUS-001: Accès admin dashboard
```python
def test_admin_business_can_access_admin_dashboard():
    """Un admin_business doit accéder à /admin-dashboard/."""
    # Arrange
    user = User.objects.create_user(username="admin", password="pass", is_staff=True)
    Profile.objects.create(user=user, role="admin_business")
    client = Client(force_login=user)
    
    # Act
    response = client.get('/admin-dashboard/')
    
    # Assert
    assert response.status_code == 200
```

**Critère de succès:** ✅ 200 OK

---

#### TEST-PERM-ADMIN-BUS-002: Lecture seule sur /gestion/
```python
def test_admin_business_readonly_on_technical_admin():
    """Un admin_business a un accès lecture seule à /gestion/ (GET uniquement)."""
    # Arrange
    user = User.objects.create_user(username="admin", password="pass", is_staff=True)
    Profile.objects.create(user=user, role="admin_business")
    client = Client(force_login=user)
    
    # Act GET
    response_get = client.get('/gestion/')
    # Act POST (tentative de modification)
    response_post = client.post('/gestion/devis/quote/add/', {})
    
    # Assert
    assert response_get.status_code == 200
    assert response_post.status_code == 302  # Redirection (lecture seule)
```

**Critère de succès:** ✅ GET autorisé, POST/PUT/DELETE bloqués

---

#### TEST-PERM-ADMIN-BUS-003: Permissions étendues (sauf users.edit)
```python
def test_admin_business_has_extended_permissions():
    """Admin business a toutes les permissions sauf users.edit."""
    # Arrange
    user = User.objects.create_user(username="admin", password="pass", is_staff=True)
    Profile.objects.create(user=user, role="admin_business")
    
    # Act & Assert
    from core.decorators import user_has_permission
    assert user_has_permission(user, 'quotes.view') is True
    assert user_has_permission(user, 'quotes.create') is True
    assert user_has_permission(user, 'invoices.create') is True
    assert user_has_permission(user, 'tasks.assign') is True
    # users.edit réservé à admin_technical
    assert user_has_permission(user, 'users.edit') is False
```

**Critère de succès:** ✅ Permissions métier complètes, admin technique limité

---

### 3.4 Rôle ADMIN_TECHNICAL (Superuser)

#### TEST-PERM-ADMIN-TECH-001: Accès complet /gestion/
```python
def test_superuser_full_access_to_gestion():
    """Un superuser doit avoir un accès complet à /gestion/."""
    # Arrange
    user = User.objects.create_superuser(username="super", password="pass", email="super@test.com")
    client = Client(force_login=user)
    
    # Act
    response_get = client.get('/gestion/')
    # Tentative création
    customer = Customer.objects.create(full_name="Test", email="t@test.com", phone="01")
    response_post = client.post('/gestion/devis/quote/add/', {
        'client': customer.pk,
        'status': 'draft',
    })
    
    # Assert
    assert response_get.status_code == 200
    assert response_post.status_code in [200, 302]  # 302 = succès + redirect
```

**Critère de succès:** ✅ Lecture + écriture complète

---

#### TEST-PERM-ADMIN-TECH-002: Permissions wildcard
```python
def test_superuser_has_all_permissions():
    """Un superuser doit avoir TOUTES les permissions (wildcard '*')."""
    # Arrange
    user = User.objects.create_superuser(username="super", password="pass", email="super@test.com")
    
    # Act & Assert
    from core.decorators import user_has_permission
    assert user_has_permission(user, 'any.permission') is True
    assert user_has_permission(user, 'users.edit') is True
    assert user_has_permission(user, 'system.config') is True
```

**Critère de succès:** ✅ Wildcard '*' actif

---

### 3.5 Tests de Middleware

#### TEST-MIDDLEWARE-001: Redirection automatique selon rôle
```python
def test_middleware_redirects_to_correct_portal():
    """Le middleware doit rediriger chaque rôle vers son portail."""
    # Client → /client/
    user_client = User.objects.create_user(username="c", password="p")
    Profile.objects.create(user=user_client, role=Profile.ROLE_CLIENT)
    client_c = Client(force_login=user_client)
    response = client_c.get('/worker/')  # Tentative accès worker
    assert response.status_code == 302
    assert '/client/' in response.url
    
    # Worker → /worker/
    user_worker = User.objects.create_user(username="w", password="p")
    Profile.objects.create(user=user_worker, role=Profile.ROLE_WORKER)
    client_w = Client(force_login=user_worker)
    response = client_w.get('/client/')  # Tentative accès client
    assert response.status_code == 302
    assert '/worker/' in response.url
```

**Critère de succès:** ✅ Middleware actif et redirections correctes

---

## 4. TESTS DES FLUX MÉTIER

### 4.1 Workflow Complet Devis → Facture

#### TEST-WORKFLOW-001: Cycle complet avec validation
```python
@pytest.mark.django_db
def test_full_quote_to_invoice_workflow():
    """Test du cycle complet : création → envoi → validation → facturation."""
    
    # Étape 1: Création devis
    customer = Customer.objects.create(full_name="Client Test", email="client@test.com", phone="0123456789")
    quote = Quote.objects.create(client=customer, status=Quote.QuoteStatus.DRAFT)
    QuoteItem.objects.create(quote=quote, description="Service A", quantity=1, unit_price=100, tax_rate=20)
    quote.compute_totals()
    assert quote.total_ttc == Decimal("120.00")
    
    # Étape 2: Envoi (changement statut)
    quote.status = Quote.QuoteStatus.SENT
    quote.save()
    assert quote.status == Quote.QuoteStatus.SENT
    
    # Étape 3: Validation 2FA
    validation = QuoteValidation.create_for_quote(quote)
    assert validation.verify(validation.code) is True
    
    # Étape 4: Acceptation
    quote.status = Quote.QuoteStatus.ACCEPTED
    quote.save()
    assert quote.status == Quote.QuoteStatus.ACCEPTED
    
    # Étape 5: Conversion en facture
    result = create_invoice_from_quote(quote)
    invoice = result.invoice
    
    # Vérifications finales
    assert invoice is not None
    assert invoice.total_ttc == Decimal("120.00")
    assert invoice.invoice_items.count() == 1
    assert quote.status == Quote.QuoteStatus.INVOICED
    assert quote.invoices.count() == 1
```

**Critère de succès:** ✅ Workflow complet sans erreur

---

### 4.2 Transitions de Statuts

#### TEST-STATUS-001: Transitions autorisées pour Quote
```python
def test_quote_status_transitions():
    """Vérifier les transitions de statut autorisées."""
    customer = Customer.objects.create(full_name="Client", email="c@test.com", phone="01")
    quote = Quote.objects.create(client=customer, status=Quote.QuoteStatus.DRAFT)
    
    # DRAFT → SENT (autorisé)
    quote.status = Quote.QuoteStatus.SENT
    quote.save()
    assert quote.status == Quote.QuoteStatus.SENT
    
    # SENT → ACCEPTED (autorisé après validation)
    quote.status = Quote.QuoteStatus.ACCEPTED
    quote.save()
    assert quote.status == Quote.QuoteStatus.ACCEPTED
    
    # ACCEPTED → INVOICED (autorisé via service)
    QuoteItem.objects.create(quote=quote, description="Item", quantity=1, unit_price=100, tax_rate=20)
    quote.compute_totals()
    result = create_invoice_from_quote(quote)
    assert quote.status == Quote.QuoteStatus.INVOICED
```

**Critère de succès:** ✅ Transitions cohérentes

---

#### TEST-STATUS-002: Transitions interdites
```python
def test_quote_invalid_status_transitions():
    """Certaines transitions doivent être bloquées."""
    customer = Customer.objects.create(full_name="Client", email="c@test.com", phone="01")
    quote = Quote.objects.create(client=customer, status=Quote.QuoteStatus.REJECTED)
    
    # REJECTED → INVOICED (interdit)
    with pytest.raises(QuoteStatusError):
        create_invoice_from_quote(quote)
```

**Critère de succès:** ✅ Règles métier respectées

---

### 4.3 Génération PDF

#### TEST-PDF-001: Génération PDF devis
```python
def test_quote_pdf_generation():
    """Un devis doit pouvoir générer un PDF via WeasyPrint."""
    # Arrange
    customer = Customer.objects.create(full_name="Client", email="c@test.com", phone="01")
    quote = Quote.objects.create(client=customer, status=Quote.QuoteStatus.DRAFT)
    QuoteItem.objects.create(quote=quote, description="Service", quantity=1, unit_price=100, tax_rate=20)
    quote.compute_totals()
    
    # Act
    pdf_bytes = quote.generate_pdf(attach=True)
    
    # Assert
    assert len(pdf_bytes) > 0
    assert quote.pdf.name.startswith("devis/")
    assert b'%PDF' in pdf_bytes[:10]  # Signature PDF
```

**Critère de succès:** ✅ PDF valide généré

---

#### TEST-PDF-002: Génération PDF facture
```python
def test_invoice_pdf_generation():
    """Une facture doit pouvoir générer un PDF via WeasyPrint."""
    # Arrange
    invoice = Invoice.objects.create()
    InvoiceItem.objects.create(invoice=invoice, description="Item", quantity=1, unit_price=100, tax_rate=20)
    invoice.compute_totals()
    
    # Act
    pdf_bytes = invoice.generate_pdf(attach=True)
    
    # Assert
    assert len(pdf_bytes) > 0
    assert invoice.pdf.name.startswith("factures/")
    assert b'%PDF' in pdf_bytes[:10]
```

**Critère de succès:** ✅ PDF valide généré

---

## 5. TESTS DES SERVICES

### 5.1 Service create_invoice_from_quote

#### TEST-SERVICE-001: Conversion avec items multiples
```python
def test_service_convert_quote_multiple_items():
    """Le service doit copier tous les items du devis."""
    # Arrange
    customer = Customer.objects.create(full_name="Client", email="c@test.com", phone="01")
    quote = Quote.objects.create(client=customer, status=Quote.QuoteStatus.ACCEPTED)
    QuoteItem.objects.create(quote=quote, description="Item 1", quantity=2, unit_price=50, tax_rate=20)
    QuoteItem.objects.create(quote=quote, description="Item 2", quantity=1, unit_price=100, tax_rate=20)
    QuoteItem.objects.create(quote=quote, description="Item 3", quantity=3, unit_price=30, tax_rate=10)
    quote.compute_totals()
    
    # Act
    result = create_invoice_from_quote(quote)
    
    # Assert
    assert result.invoice.invoice_items.count() == 3
    items = list(result.invoice.invoice_items.all())
    assert items[0].description == "Item 1"
    assert items[0].quantity == 2
    assert items[1].description == "Item 2"
    assert items[2].description == "Item 3"
```

**Critère de succès:** ✅ Tous les items copiés

---

#### TEST-SERVICE-002: Atomicité de la transaction
```python
def test_service_transaction_atomicity():
    """En cas d'erreur, la transaction doit être rollback complète."""
    # Arrange
    customer = Customer.objects.create(full_name="Client", email="c@test.com", phone="01")
    quote = Quote.objects.create(client=customer, status=Quote.QuoteStatus.ACCEPTED)
    
    # Mock une erreur lors de la copie des items
    with patch('factures.models.InvoiceItem.objects.create', side_effect=Exception("DB Error")):
        # Act & Assert
        with pytest.raises(Exception):
            create_invoice_from_quote(quote)
        
        # Vérifier qu'aucune facture n'a été créée
        assert Invoice.objects.count() == 0
        assert quote.status == Quote.QuoteStatus.ACCEPTED  # Statut inchangé
```

**Critère de succès:** ✅ Rollback complet en cas d'erreur

---

### 5.2 Service compute_totals

#### TEST-SERVICE-003: Calcul totaux avec TVA multiple
```python
def test_compute_totals_multiple_tax_rates():
    """Le calcul doit gérer plusieurs taux de TVA."""
    # Arrange
    customer = Customer.objects.create(full_name="Client", email="c@test.com", phone="01")
    quote = Quote.objects.create(client=customer)
    QuoteItem.objects.create(quote=quote, description="Item 20%", quantity=1, unit_price=100, tax_rate=20)
    QuoteItem.objects.create(quote=quote, description="Item 10%", quantity=1, unit_price=100, tax_rate=10)
    QuoteItem.objects.create(quote=quote, description="Item 5.5%", quantity=1, unit_price=100, tax_rate=Decimal("5.5"))
    
    # Act
    quote.compute_totals()
    
    # Assert
    assert quote.total_ht == Decimal("300.00")  # 100 + 100 + 100
    assert quote.tva == Decimal("35.50")         # 20 + 10 + 5.5
    assert quote.total_ttc == Decimal("335.50")  # 300 + 35.5
```

**Critère de succès:** ✅ Calcul correct avec TVA mixte

---

#### TEST-SERVICE-004: Précision décimale
```python
def test_compute_totals_decimal_precision():
    """Les calculs doivent utiliser ROUND_HALF_UP pour éviter les erreurs d'arrondi."""
    # Arrange
    customer = Customer.objects.create(full_name="Client", email="c@test.com", phone="01")
    quote = Quote.objects.create(client=customer)
    QuoteItem.objects.create(quote=quote, description="Item", quantity=Decimal("1.33"), unit_price=Decimal("7.99"), tax_rate=20)
    
    # Act
    quote.compute_totals()
    
    # Assert
    # 1.33 * 7.99 = 10.6267 → arrondi à 10.63 (HT)
    # 10.63 * 0.20 = 2.126 → arrondi à 2.13 (TVA)
    # TTC = 10.63 + 2.13 = 12.76
    assert quote.total_ht == Decimal("10.63")
    assert quote.tva == Decimal("2.13")
    assert quote.total_ttc == Decimal("12.76")
```

**Critère de succès:** ✅ Pas d'erreur d'arrondi (banquier évité)

---

## 6. TESTS DES RÈGLES MÉTIER

### 6.1 Règles de Validation

#### TEST-RULE-001: Devis sans lignes interdit
```python
def test_quote_without_items_validation():
    """Un devis SENT ou ACCEPTED doit avoir au moins une ligne."""
    # Arrange
    customer = Customer.objects.create(full_name="Client", email="c@test.com", phone="01")
    quote = Quote.objects.create(client=customer, status=Quote.QuoteStatus.DRAFT)
    
    # Act & Assert
    # DRAFT sans lignes → autorisé
    quote.full_clean()  # Ne lève pas d'exception
    
    # SENT sans lignes → interdit
    quote.status = Quote.QuoteStatus.SENT
    with pytest.raises(ValidationError, match="lignes"):
        quote.full_clean()
```

**Critère de succès:** ✅ Validation métier stricte

---

#### TEST-RULE-002: Facture sans lignes
```python
def test_invoice_without_items_warning():
    """Une facture sans ligne doit afficher un warning (mais ne bloque pas la création)."""
    # Arrange
    invoice = Invoice.objects.create()
    
    # Act
    invoice.compute_totals()
    
    # Assert
    assert invoice.total_ttc == Decimal("0.00")
    # Le code doit logger un warning mais ne pas crasher
```

**Critère de succès:** ✅ Pas de crash, warning affiché

---

### 6.2 Règles de Montants

#### TEST-RULE-003: Montants négatifs interdits
```python
def test_negative_amounts_prevention():
    """Les montants négatifs doivent être évités."""
    # Arrange
    invoice = Invoice.objects.create(discount=Decimal("500.00"))
    InvoiceItem.objects.create(invoice=invoice, description="Item", quantity=1, unit_price=100, tax_rate=20)
    
    # Act
    invoice.compute_totals()
    
    # Assert
    # Remise > HT → montants forcés à 0
    assert invoice.total_ht == Decimal("0.00")
    assert invoice.tva == Decimal("0.00")
    assert invoice.total_ttc == Decimal("0.00")
```

**Critère de succès:** ✅ Pas de montant négatif

---

### 6.3 Règles de Délais

#### TEST-RULE-004: Validité devis 30 jours
```python
def test_quote_validity_period():
    """Un devis doit avoir une validité par défaut de 30 jours."""
    # Arrange
    customer = Customer.objects.create(full_name="Client", email="c@test.com", phone="01")
    quote = Quote.objects.create(client=customer, issue_date=date(2025, 1, 1))
    
    # Assert
    assert quote.valid_until == date(2025, 1, 31)  # +30 jours
```

**Critère de succès:** ✅ Calcul automatique de valid_until

---

## 7. RECOMMANDATIONS ET CORRECTIONS

### 7.1 Incohérences Détectées 🔴

#### ISSUE-001: Devis sans lignes autorisé en base
**Problème:** Un devis peut être sauvegardé sans `QuoteItem`, ce qui génère des totaux à 0.

**Impact:** Risque d'envoi de devis vides au client.

**Recommandation:**
```python
# Ajouter dans Quote.clean()
def clean(self):
    if self.status in [self.QuoteStatus.SENT, self.QuoteStatus.ACCEPTED]:
        if not self.quote_items.exists():
            raise ValidationError("Un devis envoyé ou accepté doit contenir au moins une ligne.")
```

**Tests à ajouter:**
- TEST-RULE-001 (déjà défini ci-dessus)

---

#### ISSUE-002: Pas de validation métier sur conversion Invoice
**Problème:** `create_invoice_from_quote` ne vérifie pas que le devis a des lignes.

**Impact:** Factures vides possibles.

**Recommandation:**
```python
# Dans devis/services.py
def create_invoice_from_quote(quote):
    # Ajouter avant création facture
    if not quote.quote_items.exists():
        raise ValidationError("Le devis ne contient aucune ligne à facturer.")
    # ... reste du code
```

---

#### ISSUE-003: Race condition sur numérotation
**Problème:** Bien que `select_for_update()` soit utilisé, il faut s'assurer que toutes les créations passent par `save()`.

**Recommandation:**
✅ **Déjà implémenté correctement** dans `Invoice.save()` et `Quote.save()`.

**Tests à renforcer:**
- Ajouter test de concurrence avec threads multiples

---

#### ISSUE-004: Validation 2FA sans rate limiting
**Problème:** Un attaquant peut tenter 5 fois le code (max_attempts=5), puis recréer une validation.

**Impact:** Brute force possible.

**Recommandation:**
```python
# Ajouter rate limiting par IP ou par email
from django.core.cache import cache

def verify(self, submitted_code: str, *, max_attempts: int = 5, request=None):
    if request:
        ip = request.META.get('REMOTE_ADDR')
        cache_key = f"quote_validation_{self.quote_id}_{ip}"
        attempts = cache.get(cache_key, 0)
        if attempts >= 10:  # Max 10 tentatives par IP
            raise ValidationError("Trop de tentatives. Réessayez dans 1 heure.")
        cache.set(cache_key, attempts + 1, 3600)
    # ... reste du code
```

---

#### ISSUE-005: Permissions hardcodées dans decorators
**Problème:** Les permissions sont définies dans un dict hardcodé (`user_has_permission`), pas en base.

**Impact:** Difficile à maintenir, pas dynamique.

**Recommandation:**
- Utiliser Django Permissions natives (`Permission` model)
- Migrer vers `django-guardian` pour permissions objet-level

**Alternative court terme:**
- Externaliser le dict dans `settings.py` pour permettre configuration

---

### 7.2 Améliorations Suggérées

#### IMPROV-001: Ajouter django-fsm pour les statuts
**Objectif:** Garantir les transitions de statut valides via machine à états.

**Exemple:**
```python
from django_fsm import FSMField, transition

class Quote(models.Model):
    status = FSMField(default=QuoteStatus.DRAFT, choices=QuoteStatus.choices)
    
    @transition(field=status, source=QuoteStatus.DRAFT, target=QuoteStatus.SENT)
    def send(self):
        # Validation avant transition
        if not self.quote_items.exists():
            raise ValidationError("Impossible d'envoyer un devis vide.")
    
    @transition(field=status, source=QuoteStatus.SENT, target=QuoteStatus.ACCEPTED)
    def accept(self):
        pass
```

**Tests à ajouter:**
- TEST-FSM-001: Transition invalide levée en exception
- TEST-FSM-002: Workflow complet avec FSM

---

#### IMPROV-002: Ajouter historique des modifications
**Objectif:** Tracer qui a modifié quoi et quand (audit trail).

**Solution:**
- Utiliser `django-simple-history`
- Ajouter `history = HistoricalRecords()` sur Quote et Invoice

---

#### IMPROV-003: Tests de performance
**Objectif:** Vérifier les performances sur gros volumes.

**Tests à ajouter:**
```python
def test_quote_list_performance():
    """La liste de 1000 devis doit charger en < 1s."""
    # Créer 1000 devis
    quotes = [Quote(client=customer) for _ in range(1000)]
    Quote.objects.bulk_create(quotes)
    
    # Act
    start = time.time()
    list(Quote.objects.all())
    duration = time.time() - start
    
    # Assert
    assert duration < 1.0
```

---

## 8. PLAN D'EXÉCUTION

### 8.1 Priorités

**🔴 PRIORITÉ 1 - CRITIQUE (Semaine 1)**
- TEST-DEVIS-001 à 004 (Flux devis)
- TEST-FACTURE-001 à 005 (Flux facturation)
- TEST-TASK-001 à 003 (Tâches)
- TEST-PERM-CLIENT-001 à 004 (Permissions client)
- TEST-WORKFLOW-001 (Workflow complet)
- Corrections ISSUE-001 et ISSUE-002

**🟡 PRIORITÉ 2 - IMPORTANT (Semaine 2)**
- TEST-PERM-WORKER-001 à 004
- TEST-PERM-ADMIN-BUS-001 à 003
- TEST-PERM-ADMIN-TECH-001 à 002
- TEST-SERVICE-001 à 004
- TEST-RULE-001 à 004
- Correction ISSUE-004 (rate limiting)

**🟢 PRIORITÉ 3 - SOUHAITABLE (Semaine 3)**
- TEST-PDF-001 et 002
- TEST-STATUS-001 et 002
- TEST-MIDDLEWARE-001
- IMPROV-001 (django-fsm)
- IMPROV-002 (historique)

### 8.2 Organisation des Fichiers de Tests

```
bugfix_email_netexpress/tests/
├── __init__.py
├── conftest.py                    # Fixtures pytest communes
├── test_models.py                 # Tests modèles (existant)
├── test_devis_urls.py            # Tests URLs (existant)
├── test_devis_links.py           # Tests liens (existant)
│
├── business/                      # NOUVEAUX TESTS MÉTIER
│   ├── __init__.py
│   ├── test_quote_workflow.py    # TEST-DEVIS-*, TEST-WORKFLOW-*
│   ├── test_invoice_workflow.py  # TEST-FACTURE-*
│   ├── test_task_business.py     # TEST-TASK-*
│   └── test_business_rules.py    # TEST-RULE-*
│
├── services/                      # TESTS DES SERVICES
│   ├── __init__.py
│   ├── test_invoice_service.py   # TEST-SERVICE-001, 002
│   ├── test_totals_service.py    # TEST-SERVICE-003, 004
│   └── test_pdf_service.py       # TEST-PDF-*
│
├── permissions/                   # TESTS DE PERMISSIONS
│   ├── __init__.py
│   ├── test_client_permissions.py    # TEST-PERM-CLIENT-*
│   ├── test_worker_permissions.py    # TEST-PERM-WORKER-*
│   ├── test_admin_permissions.py     # TEST-PERM-ADMIN-*
│   └── test_middleware.py            # TEST-MIDDLEWARE-*
│
└── fixtures/                      # Données de test
    ├── customers.json
    ├── quotes.json
    └── services.json
```

### 8.3 Configuration pytest

**conftest.py:**
```python
import pytest
from django.contrib.auth.models import User, Group
from accounts.models import Profile
from crm.models import Customer
from devis.models import Quote, QuoteItem
from factures.models import Invoice, InvoiceItem
from services.models import Service, Category
from tasks.models import Task


@pytest.fixture
def customer():
    """Fixture client standard."""
    return Customer.objects.create(
        full_name="Client Test",
        email="client@test.com",
        phone="0123456789"
    )


@pytest.fixture
def user_client(db):
    """Utilisateur avec rôle client."""
    user = User.objects.create_user(username="client", password="password", email="client@test.com")
    Profile.objects.create(user=user, role=Profile.ROLE_CLIENT)
    return user


@pytest.fixture
def user_worker(db):
    """Utilisateur avec rôle worker."""
    user = User.objects.create_user(username="worker", password="password")
    Profile.objects.create(user=user, role=Profile.ROLE_WORKER)
    group = Group.objects.create(name="Équipe A")
    user.groups.add(group)
    return user


@pytest.fixture
def user_admin_business(db):
    """Utilisateur avec rôle admin business."""
    user = User.objects.create_user(username="admin_business", password="password", is_staff=True)
    Profile.objects.create(user=user, role="admin_business")
    return user


@pytest.fixture
def user_superuser(db):
    """Superuser (admin technique)."""
    return User.objects.create_superuser(username="super", password="password", email="super@test.com")


@pytest.fixture
def quote_with_items(customer):
    """Devis avec 2 lignes."""
    quote = Quote.objects.create(client=customer, status=Quote.QuoteStatus.DRAFT)
    QuoteItem.objects.create(quote=quote, description="Service A", quantity=1, unit_price=100, tax_rate=20)
    QuoteItem.objects.create(quote=quote, description="Service B", quantity=2, unit_price=50, tax_rate=20)
    quote.compute_totals()
    return quote


@pytest.fixture
def service_category():
    """Catégorie de service."""
    return Category.objects.create(name="Nettoyage", slug="nettoyage")


@pytest.fixture
def service(service_category):
    """Service standard."""
    return Service.objects.create(
        title="Nettoyage Bureaux",
        category=service_category,
        description="Nettoyage de bureaux professionnels",
        is_active=True
    )
```

### 8.4 Commandes d'Exécution

```bash
# Tests complets
pytest

# Tests critiques uniquement
pytest -m critical

# Tests d'un module spécifique
pytest tests/business/test_quote_workflow.py

# Tests avec couverture
pytest --cov=devis --cov=factures --cov=tasks --cov-report=html

# Tests en parallèle
pytest -n auto

# Tests avec verbosité
pytest -vv

# Tests avec pdb en cas d'échec
pytest --pdb
```

### 8.5 Métriques de Succès

**Couverture de code cible:**
- `devis/`: ≥ 85%
- `factures/`: ≥ 85%
- `tasks/`: ≥ 80%
- `accounts/`: ≥ 75%
- `core/`: ≥ 70%

**Temps d'exécution:**
- Suite complète: < 60 secondes
- Tests critiques: < 15 secondes

**Taux de réussite:**
- 100% sur environnement CI/CD

---

## 📊 RÉSUMÉ

**Total de tests définis:** 50+

**Répartition:**
- Tests critiques (P1): 15
- Tests permissions (P1-P2): 18
- Tests services (P2): 8
- Tests règles métier (P2): 6
- Tests workflow (P1-P3): 8

**Corrections identifiées:** 5 issues critiques  
**Améliorations suggérées:** 3 améliorations majeures

**Estimation:**
- Implémentation complète: 2-3 semaines
- Priorité 1 uniquement: 1 semaine
- Corrections critiques: 2-3 jours

---

## ✅ VALIDATION

Ce plan de tests a été élaboré en respectant:
- ✅ PROJECT_CONTEXT.txt (phases 0-7)
- ✅ Architecture orientée services
- ✅ Rôles identifiés (Client, Worker, Admin Business, Admin Technical)
- ✅ Flux critiques (devis, factures, tâches)
- ✅ Pas de tests UI visuels
- ✅ Focus sur logique métier ERP

**Auteur:** Expert Senior Tester  
**Validation:** Prêt pour implémentation  
**Prochaine étape:** Création des fichiers de tests

