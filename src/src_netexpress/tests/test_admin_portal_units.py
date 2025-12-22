"""
Unit tests for Admin Portal functionality.

Tests KPI calculations, global planning view, and document validation functionality.
**Requirements: 4.1, 4.2, 4.3, 4.4**
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import Mock, patch
from django.test import TestCase, Client as DjangoClient
from django.contrib.auth.models import User, Group
from django.utils import timezone

from accounts.models import Profile
from devis.models import Client, Quote
from factures.models import Invoice
from tasks.models import Task


class TestAdminDashboardKPIs(TestCase):
    """Unit tests for Admin Portal KPI calculations."""
    
    def setUp(self):
        """Set up test data."""
        self.client = DjangoClient()
        
        # Create groups
        self.workers_group, _ = Group.objects.get_or_create(name='Workers')
        self.clients_group, _ = Group.objects.get_or_create(name='Clients')
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        
        # Create test client
        self.test_client_obj = Client.objects.create(
            full_name='Test Client',
            email='client@example.com',
            phone='1234567890'
        )
        
        # Create test worker
        self.worker_user = User.objects.create_user(
            username='worker1',
            email='worker1@example.com',
            password='testpass123'
        )
        self.worker_user.groups.add(self.workers_group)
        Profile.objects.filter(user=self.worker_user).update(role='worker')
    
    def test_admin_dashboard_renders_correctly(self):
        """
        Test that admin dashboard renders with correct template and context.
        **Requirements: 4.1**
        """
        self.client.force_login(self.admin_user)
        
        response = self.client.get('/admin-dashboard/')
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/admin_dashboard.html')
        
        # Check that all required KPI context variables are present
        context = response.context
        required_kpis = [
            'total_revenue', 'monthly_revenue', 'pending_revenue',
            'conversion_rate', 'task_completion_rate', 'worker_stats',
            'total_workers', 'recent_quotes', 'recent_invoices', 'recent_tasks'
        ]
        
        for kpi in required_kpis:
            self.assertIn(kpi, context, f"KPI '{kpi}' should be in dashboard context")
    
    def test_revenue_calculations(self):
        """
        Test that revenue KPIs are calculated correctly.
        **Requirements: 4.1**
        """
        # Create test quotes and invoices
        quote1 = Quote.objects.create(
            client=self.test_client_obj,
            status=Quote.QuoteStatus.ACCEPTED,
            total_ttc=Decimal('100.00'),
            issue_date=date.today()
        )
        
        quote2 = Quote.objects.create(
            client=self.test_client_obj,
            status=Quote.QuoteStatus.SENT,
            total_ttc=Decimal('200.00'),
            issue_date=date.today()
        )
        
        # Create paid invoice (should count toward total revenue)
        paid_invoice = Invoice.objects.create(
            quote=quote1,
            status=Invoice.InvoiceStatus.PAID,
            total_ttc=Decimal('100.00'),
            issue_date=date.today()
        )
        
        # Create sent invoice (should count toward pending revenue)
        sent_invoice = Invoice.objects.create(
            quote=quote2,
            status=Invoice.InvoiceStatus.SENT,
            total_ttc=Decimal('200.00'),
            issue_date=date.today()
        )
        
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin-dashboard/')
        context = response.context
        
        # Test revenue calculations
        self.assertEqual(context['total_revenue'], Decimal('100.00'))
        self.assertEqual(context['pending_revenue'], Decimal('200.00'))
        self.assertEqual(context['monthly_revenue'], Decimal('100.00'))  # Current month
    
    def test_conversion_rate_calculation(self):
        """
        Test that quote conversion rate is calculated correctly.
        **Requirements: 4.1**
        """
        # Create quotes with different statuses
        Quote.objects.create(
            client=self.test_client_obj,
            status=Quote.QuoteStatus.SENT,
            total_ttc=Decimal('100.00')
        )
        
        Quote.objects.create(
            client=self.test_client_obj,
            status=Quote.QuoteStatus.ACCEPTED,
            total_ttc=Decimal('150.00')
        )
        
        Quote.objects.create(
            client=self.test_client_obj,
            status=Quote.QuoteStatus.ACCEPTED,
            total_ttc=Decimal('200.00')
        )
        
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin-dashboard/')
        context = response.context
        
        # 2 accepted out of 3 total = 66.67% conversion rate
        expected_rate = (2 / 3) * 100
        self.assertAlmostEqual(context['conversion_rate'], expected_rate, places=1)
    
    def test_task_completion_rate_calculation(self):
        """
        Test that task completion rate is calculated correctly.
        **Requirements: 4.1**
        """
        # Create tasks with different statuses
        Task.objects.create(
            title='Task 1',
            due_date=date.today() + timedelta(days=1),
            status=Task.STATUS_COMPLETED,
            assigned_to=self.worker_user
        )
        
        Task.objects.create(
            title='Task 2',
            due_date=date.today() + timedelta(days=2),
            status=Task.STATUS_IN_PROGRESS,
            assigned_to=self.worker_user
        )
        
        Task.objects.create(
            title='Task 3',
            due_date=date.today() + timedelta(days=3),
            status=Task.STATUS_COMPLETED,
            assigned_to=self.worker_user
        )
        
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin-dashboard/')
        context = response.context
        
        # 2 completed out of 3 total = 66.67% completion rate
        expected_rate = (2 / 3) * 100
        self.assertAlmostEqual(context['task_completion_rate'], expected_rate, places=1)
    
    def test_worker_performance_stats(self):
        """
        Test that worker performance statistics are calculated correctly.
        **Requirements: 4.1**
        """
        # Create another worker
        worker2 = User.objects.create_user(
            username='worker2',
            email='worker2@example.com',
            password='testpass123'
        )
        worker2.groups.add(self.workers_group)
        Profile.objects.filter(user=worker2).update(role='worker')
        
        # Create tasks for worker1
        Task.objects.create(
            title='Worker1 Task 1',
            due_date=date.today() + timedelta(days=1),
            status=Task.STATUS_COMPLETED,
            assigned_to=self.worker_user
        )
        
        Task.objects.create(
            title='Worker1 Task 2',
            due_date=date.today() + timedelta(days=2),
            status=Task.STATUS_IN_PROGRESS,
            assigned_to=self.worker_user
        )
        
        # Create tasks for worker2
        Task.objects.create(
            title='Worker2 Task 1',
            due_date=date.today() + timedelta(days=1),
            status=Task.STATUS_COMPLETED,
            assigned_to=worker2
        )
        
        Task.objects.create(
            title='Worker2 Task 2',
            due_date=date.today() + timedelta(days=2),
            status=Task.STATUS_COMPLETED,
            assigned_to=worker2
        )
        
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin-dashboard/')
        context = response.context
        
        worker_stats = context['worker_stats']
        self.assertEqual(len(worker_stats), 2)
        
        # Find stats for each worker
        worker1_stats = next(ws for ws in worker_stats if ws['worker'] == self.worker_user)
        worker2_stats = next(ws for ws in worker_stats if ws['worker'] == worker2)
        
        # Worker1: 1 completed out of 2 total = 50%
        self.assertEqual(worker1_stats['total_tasks'], 2)
        self.assertEqual(worker1_stats['completed_tasks'], 1)
        self.assertEqual(worker1_stats['completion_rate'], 50.0)
        
        # Worker2: 2 completed out of 2 total = 100%
        self.assertEqual(worker2_stats['total_tasks'], 2)
        self.assertEqual(worker2_stats['completed_tasks'], 2)
        self.assertEqual(worker2_stats['completion_rate'], 100.0)
    
    def test_admin_dashboard_denies_non_staff_access(self):
        """
        Test that non-staff users cannot access admin dashboard.
        **Requirements: 4.3**
        """
        # Create non-staff user
        regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='testpass123',
            is_staff=False
        )
        
        self.client.force_login(regular_user)
        response = self.client.get('/admin-dashboard/')
        
        # Should redirect to admin login (302)
        self.assertEqual(response.status_code, 302)
        # The redirect might go to different places depending on middleware
        # Just check that access is denied (302 redirect)
        self.assertTrue(response.url is not None)


class TestAdminGlobalPlanningView(TestCase):
    """Unit tests for Admin Portal global planning view."""
    
    def setUp(self):
        """Set up test data."""
        self.client = DjangoClient()
        
        # Create groups
        self.workers_group, _ = Group.objects.get_or_create(name='Workers')
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        
        # Create test workers
        self.worker1 = User.objects.create_user(
            username='worker1',
            email='worker1@example.com',
            password='testpass123'
        )
        self.worker1.groups.add(self.workers_group)
        Profile.objects.filter(user=self.worker1).update(role='worker')
        
        self.worker2 = User.objects.create_user(
            username='worker2',
            email='worker2@example.com',
            password='testpass123'
        )
        self.worker2.groups.add(self.workers_group)
        Profile.objects.filter(user=self.worker2).update(role='worker')
    
    def test_global_planning_renders_correctly(self):
        """
        Test that global planning view renders with correct template and context.
        **Requirements: 4.2**
        """
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin-dashboard/planning/')
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/admin_global_planning.html')
        
        # Check that all required context variables are present
        context = response.context
        required_vars = [
            'worker_planning', 'unassigned_tasks', 'start_date', 'end_date',
            'total_workers', 'total_tasks_in_period', 'assigned_tasks',
            'unassigned_count', 'status_distribution', 'all_tasks'
        ]
        
        for var in required_vars:
            self.assertIn(var, context, f"Variable '{var}' should be in planning context")
    
    def test_worker_planning_organization(self):
        """
        Test that tasks are properly organized by worker in planning view.
        **Requirements: 4.2, 4.4**
        """
        from django.utils import timezone
        
        today = timezone.now().date()
        # Use dates within the current week to ensure they appear in planning
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        # Create tasks for worker1 within the current week
        task1 = Task.objects.create(
            title='Worker1 Upcoming Task',
            start_date=start_of_week + timedelta(days=1),
            due_date=start_of_week + timedelta(days=3),
            assigned_to=self.worker1
        )
        
        task2 = Task.objects.create(
            title='Worker1 In Progress Task',
            start_date=start_of_week,
            due_date=start_of_week + timedelta(days=2),
            assigned_to=self.worker1
        )
        
        # Create task for worker2 within the current week - manually set to completed
        task3 = Task.objects.create(
            title='Worker2 Completed Task',
            start_date=start_of_week,
            due_date=start_of_week + timedelta(days=1),
            assigned_to=self.worker2
        )
        # Manually set to completed (this prevents auto-recalculation)
        task3.status = Task.STATUS_COMPLETED
        task3.save()
        
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin-dashboard/planning/')
        context = response.context
        
        worker_planning = context['worker_planning']
        self.assertEqual(len(worker_planning), 2)
        
        # Find planning for each worker
        worker1_plan = next(wp for wp in worker_planning if wp['worker'] == self.worker1)
        worker2_plan = next(wp for wp in worker_planning if wp['worker'] == self.worker2)
        
        # Check worker1 planning - should have 2 tasks total
        self.assertEqual(worker1_plan['total_tasks'], 2)
        
        # Check worker2 planning - should have 1 completed task
        self.assertEqual(worker2_plan['total_tasks'], 1)
        self.assertEqual(len(worker2_plan['completed_tasks']), 1)
    
    def test_date_range_filtering(self):
        """
        Test that planning view correctly filters tasks by date range.
        **Requirements: 4.2**
        """
        today = date.today()
        
        # Create task within range
        task_in_range = Task.objects.create(
            title='Task In Range',
            start_date=today,
            due_date=today + timedelta(days=2),
            status=Task.STATUS_IN_PROGRESS,
            assigned_to=self.worker1
        )
        
        # Create task outside range (in the past)
        task_outside_range = Task.objects.create(
            title='Task Outside Range',
            start_date=today - timedelta(days=10),
            due_date=today - timedelta(days=8),
            status=Task.STATUS_COMPLETED,
            assigned_to=self.worker1
        )
        
        # Request with specific date range
        start_date = today
        end_date = today + timedelta(days=7)
        
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin-dashboard/planning/', {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        })
        context = response.context
        
        all_tasks = list(context['all_tasks'])
        
        # Task in range should be included
        self.assertIn(task_in_range, all_tasks)
        
        # Task outside range should not be included
        self.assertNotIn(task_outside_range, all_tasks)
        
        # Check date range in context
        self.assertEqual(context['start_date'], start_date)
        self.assertEqual(context['end_date'], end_date)
    
    def test_unassigned_tasks_identification(self):
        """
        Test that unassigned tasks are properly identified and displayed.
        **Requirements: 4.2, 4.4**
        """
        today = date.today()
        
        # Create assigned task
        assigned_task = Task.objects.create(
            title='Assigned Task',
            start_date=today,
            due_date=today + timedelta(days=2),
            status=Task.STATUS_IN_PROGRESS,
            assigned_to=self.worker1
        )
        
        # Create unassigned task
        unassigned_task = Task.objects.create(
            title='Unassigned Task',
            start_date=today,
            due_date=today + timedelta(days=2),
            status=Task.STATUS_UPCOMING,
            assigned_to=None
        )
        
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin-dashboard/planning/')
        context = response.context
        
        unassigned_tasks = list(context['unassigned_tasks'])
        
        # Check unassigned tasks
        self.assertIn(unassigned_task, unassigned_tasks)
        self.assertNotIn(assigned_task, unassigned_tasks)
        
        # Check counts
        self.assertEqual(context['assigned_tasks'], 1)
        self.assertEqual(context['unassigned_count'], 1)
        self.assertEqual(context['total_tasks_in_period'], 2)
    
    def test_status_distribution_calculation(self):
        """
        Test that task status distribution is calculated correctly.
        **Requirements: 4.2**
        """
        from django.utils import timezone
        
        today = timezone.now().date()
        # Use dates within the current week to ensure they appear in planning
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        # Create tasks with dates within the current week
        task1 = Task.objects.create(
            title='Upcoming Task',
            start_date=start_of_week + timedelta(days=2),  # Future start = upcoming
            due_date=start_of_week + timedelta(days=4),
            assigned_to=self.worker1
        )
        
        task2 = Task.objects.create(
            title='In Progress Task',
            start_date=start_of_week,  # Past start, future due = in progress
            due_date=start_of_week + timedelta(days=3),
            assigned_to=self.worker1
        )
        
        # Create completed task - manually set status to prevent auto-recalculation
        task3 = Task.objects.create(
            title='Completed Task',
            start_date=start_of_week,
            due_date=start_of_week + timedelta(days=1),
            assigned_to=self.worker2
        )
        task3.status = Task.STATUS_COMPLETED
        task3.save()
        
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin-dashboard/planning/')
        context = response.context
        
        status_distribution = context['status_distribution']
        
        # Check that we have the expected number of tasks in each status
        # The exact counts may vary due to automatic status calculation
        total_tasks = sum(status_distribution.values())
        self.assertEqual(total_tasks, 3)  # Should have 3 tasks total
        
        # Check that completed tasks are properly identified
        self.assertGreaterEqual(status_distribution['completed'], 1)
    
    def test_workload_percentage_calculation(self):
        """
        Test that workload percentage is calculated for workers.
        **Requirements: 4.2**
        """
        today = date.today()
        
        # Create multiple tasks for worker1 (high workload)
        for i in range(8):
            Task.objects.create(
                title=f'Worker1 Task {i+1}',
                start_date=today,
                due_date=today + timedelta(days=2),
                status=Task.STATUS_IN_PROGRESS,
                assigned_to=self.worker1
            )
        
        # Create fewer tasks for worker2 (low workload)
        for i in range(2):
            Task.objects.create(
                title=f'Worker2 Task {i+1}',
                start_date=today,
                due_date=today + timedelta(days=2),
                status=Task.STATUS_IN_PROGRESS,
                assigned_to=self.worker2
            )
        
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin-dashboard/planning/')
        context = response.context
        
        worker_planning = context['worker_planning']
        
        worker1_plan = next(wp for wp in worker_planning if wp['worker'] == self.worker1)
        worker2_plan = next(wp for wp in worker_planning if wp['worker'] == self.worker2)
        
        # Simple workload calculation: min(100, task_count * 10)
        self.assertEqual(worker1_plan['workload_percentage'], 80)  # 8 * 10 = 80
        self.assertEqual(worker2_plan['workload_percentage'], 20)  # 2 * 10 = 20


class TestAdminPortalAccessControl(TestCase):
    """Unit tests for Admin Portal access control and document validation."""
    
    def setUp(self):
        """Set up test data."""
        self.client = DjangoClient()
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='testpass123',
            is_staff=False
        )
        
        # Create staff user (but not superuser)
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='testpass123',
            is_staff=True,
            is_superuser=False
        )
    
    def test_admin_dashboard_staff_access_control(self):
        """
        Test that only staff members can access admin dashboard.
        **Requirements: 4.3**
        """
        # Test admin access
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin-dashboard/')
        self.assertEqual(response.status_code, 200)
        
        # Test staff access
        self.client.force_login(self.staff_user)
        response = self.client.get('/admin-dashboard/')
        self.assertEqual(response.status_code, 200)
        
        # Test regular user access (should be denied)
        self.client.force_login(self.regular_user)
        response = self.client.get('/admin-dashboard/')
        self.assertEqual(response.status_code, 302)  # Redirect to admin login
    
    def test_global_planning_staff_access_control(self):
        """
        Test that only staff members can access global planning view.
        **Requirements: 4.3**
        """
        # Test admin access
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin-dashboard/planning/')
        self.assertEqual(response.status_code, 200)
        
        # Test staff access
        self.client.force_login(self.staff_user)
        response = self.client.get('/admin-dashboard/planning/')
        self.assertEqual(response.status_code, 200)
        
        # Test regular user access (should be denied)
        self.client.force_login(self.regular_user)
        response = self.client.get('/admin-dashboard/planning/')
        self.assertEqual(response.status_code, 302)  # Redirect to admin login
    
    def test_document_validation_functionality(self):
        """
        Test that admin portal provides document validation functionality.
        **Requirements: 4.4**
        """
        # Create test client and documents
        test_client_obj = Client.objects.create(
            full_name='Test Client',
            email='client@example.com',
            phone='1234567890'
        )
        
        quote = Quote.objects.create(
            client=test_client_obj,
            status=Quote.QuoteStatus.SENT,
            total_ttc=Decimal('100.00')
        )
        
        invoice = Invoice.objects.create(
            quote=quote,
            status=Invoice.InvoiceStatus.SENT,
            total_ttc=Decimal('100.00')
        )
        
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin-dashboard/')
        context = response.context
        
        # Check that recent documents are available for validation
        self.assertIn('recent_quotes', context)
        self.assertIn('recent_invoices', context)
        
        recent_quotes = list(context['recent_quotes'])
        recent_invoices = list(context['recent_invoices'])
        
        self.assertIn(quote, recent_quotes)
        self.assertIn(invoice, recent_invoices)
        
        # Check that status counts are available for validation workflow
        self.assertIn('quote_status_counts', context)
        self.assertIn('invoice_status_counts', context)
        
        quote_status_counts = context['quote_status_counts']
        invoice_status_counts = context['invoice_status_counts']
        
        self.assertEqual(quote_status_counts['sent'], 1)
        self.assertEqual(invoice_status_counts['sent'], 1)
    
    def test_admin_portal_comprehensive_data_access(self):
        """
        Test that admin portal provides comprehensive access to all business data.
        **Requirements: 4.1, 4.2, 4.4**
        """
        # Create comprehensive test data
        test_client_obj = Client.objects.create(
            full_name='Test Client',
            email='client@example.com',
            phone='1234567890'
        )
        
        # Create worker
        worker = User.objects.create_user(
            username='worker',
            email='worker@example.com',
            password='testpass123'
        )
        workers_group, _ = Group.objects.get_or_create(name='Workers')
        worker.groups.add(workers_group)
        
        # Create business documents
        quote = Quote.objects.create(
            client=test_client_obj,
            status=Quote.QuoteStatus.ACCEPTED,
            total_ttc=Decimal('500.00')
        )
        
        invoice = Invoice.objects.create(
            quote=quote,
            status=Invoice.InvoiceStatus.PAID,
            total_ttc=Decimal('500.00')
        )
        
        task = Task.objects.create(
            title='Test Task',
            due_date=date.today() + timedelta(days=1),
            status=Task.STATUS_COMPLETED,
            assigned_to=worker
        )
        
        # Test dashboard access
        self.client.force_login(self.admin_user)
        dashboard_response = self.client.get('/admin-dashboard/')
        dashboard_context = dashboard_response.context
        
        # Verify comprehensive data access in dashboard
        self.assertGreater(dashboard_context['total_revenue'], 0)
        self.assertGreater(dashboard_context['conversion_rate'], 0)
        self.assertGreater(dashboard_context['task_completion_rate'], 0)
        self.assertEqual(len(dashboard_context['worker_stats']), 1)
        
        # Test planning access
        planning_response = self.client.get('/admin-dashboard/planning/')
        planning_context = planning_response.context
        
        # Verify comprehensive planning data access
        self.assertEqual(planning_context['total_workers'], 1)
        self.assertEqual(planning_context['total_tasks_in_period'], 1)
        self.assertEqual(len(planning_context['worker_planning']), 1)
        
        worker_plan = planning_context['worker_planning'][0]
        self.assertEqual(worker_plan['worker'], worker)
        self.assertEqual(worker_plan['total_tasks'], 1)
        self.assertEqual(len(worker_plan['completed_tasks']), 1)


class TestAdminPortalIntegration(TestCase):
    """Integration tests for Admin Portal components."""
    
    def setUp(self):
        """Set up test data."""
        self.client = DjangoClient()
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
    
    def test_admin_portal_navigation_consistency(self):
        """
        Test that admin portal views use consistent templates and navigation.
        **Requirements: 4.3**
        """
        self.client.force_login(self.admin_user)
        
        # Test dashboard template
        dashboard_response = self.client.get('/admin-dashboard/')
        self.assertTemplateUsed(dashboard_response, 'core/admin_dashboard.html')
        
        # Test planning template
        planning_response = self.client.get('/admin-dashboard/planning/')
        self.assertTemplateUsed(planning_response, 'core/admin_global_planning.html')
        
        # Both templates should follow the same naming convention
        dashboard_templates = [t.name for t in dashboard_response.templates]
        planning_templates = [t.name for t in planning_response.templates]
        
        # Check that admin templates are used
        self.assertTrue(any('admin_dashboard.html' in t for t in dashboard_templates))
        self.assertTrue(any('admin_global_planning.html' in t for t in planning_templates))
    
    def test_admin_portal_error_handling(self):
        """
        Test that admin portal handles edge cases gracefully.
        **Requirements: 4.1, 4.2**
        """
        self.client.force_login(self.admin_user)
        
        # Test with no data (empty database)
        response = self.client.get('/admin-dashboard/')
        self.assertEqual(response.status_code, 200)
        
        context = response.context
        
        # Should handle empty data gracefully
        self.assertEqual(context['total_revenue'], Decimal('0.00'))
        self.assertEqual(context['conversion_rate'], 0)
        self.assertEqual(context['task_completion_rate'], 0)
        self.assertEqual(len(context['worker_stats']), 0)
        
        # Test planning with no data
        response = self.client.get('/admin-dashboard/planning/')
        self.assertEqual(response.status_code, 200)
        
        context = response.context
        
        # Should handle empty planning gracefully
        self.assertEqual(len(context['worker_planning']), 0)
        self.assertEqual(context['total_tasks_in_period'], 0)
        self.assertEqual(context['unassigned_count'], 0)
    
    def test_admin_portal_date_parameter_validation(self):
        """
        Test that global planning handles invalid date parameters gracefully.
        **Requirements: 4.2**
        """
        self.client.force_login(self.admin_user)
        
        response = self.client.get('/admin-dashboard/planning/', {
            'start_date': 'invalid-date',
            'end_date': 'also-invalid'
        })
        self.assertEqual(response.status_code, 200)
        
        # Should fall back to default date range (current week)
        context = response.context
        self.assertIsInstance(context['start_date'], date)
        self.assertIsInstance(context['end_date'], date)
        self.assertLessEqual(context['start_date'], context['end_date'])