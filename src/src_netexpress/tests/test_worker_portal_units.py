"""
Unit tests for Worker Portal functionality.

Tests task filtering by worker, calendar view rendering, and task completion workflow.
**Validates: Requirements 3.1, 3.2, 3.3, 3.4**
"""

import pytest
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta
from unittest.mock import patch

from tasks.models import Task
from accounts.models import Profile
from tasks.views import WorkerDashboardView, WorkerScheduleView, TaskCompleteView


class WorkerPortalUnitTests(TestCase):
    """Unit tests for Worker Portal views and functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create Workers group
        self.workers_group, _ = Group.objects.get_or_create(name='Workers')
        
        # Create test workers
        self.worker1 = User.objects.create_user(
            username='worker1',
            email='worker1@example.com',
            password='testpass123'
        )
        Profile.objects.filter(user=self.worker1).update(role='worker')
        self.worker1.groups.add(self.workers_group)
        
        self.worker2 = User.objects.create_user(
            username='worker2',
            email='worker2@example.com',
            password='testpass123'
        )
        Profile.objects.filter(user=self.worker2).update(role='worker')
        self.worker2.groups.add(self.workers_group)
        
        # Create test tasks
        self.task1_worker1 = Task.objects.create(
            title='Task 1 for Worker 1',
            description='Description for task 1',
            location='Location 1',
            team='Team A',
            start_date=date.today(),
            due_date=date.today() + timedelta(days=7),
            status=Task.STATUS_IN_PROGRESS,
            assigned_to=self.worker1
        )
        
        self.task2_worker1 = Task.objects.create(
            title='Task 2 for Worker 1',
            description='Description for task 2',
            location='Location 2',
            team='Team A',
            start_date=date.today() + timedelta(days=1),
            due_date=date.today() + timedelta(days=8),
            status=Task.STATUS_UPCOMING,
            assigned_to=self.worker1
        )
        
        self.task1_worker2 = Task.objects.create(
            title='Task 1 for Worker 2',
            description='Description for worker 2 task',
            location='Location 3',
            team='Team B',
            start_date=date.today(),
            due_date=date.today() + timedelta(days=5),
            status=Task.STATUS_IN_PROGRESS,
            assigned_to=self.worker2
        )
        
        self.unassigned_task = Task.objects.create(
            title='Unassigned Task',
            description='This task has no assigned worker',
            location='Location 4',
            team='Team C',
            start_date=date.today(),
            due_date=date.today() + timedelta(days=3),
            status=Task.STATUS_UPCOMING,
            assigned_to=None
        )
        
        self.client = Client()
    
    def test_worker_dashboard_task_filtering(self):
        """
        Test that worker dashboard correctly filters tasks by assigned worker.
        **Validates: Requirements 3.1**
        """
        # Login as worker1
        self.client.login(username='worker1', password='testpass123')
        
        # Access worker dashboard
        response = self.client.get(reverse('worker:worker_dashboard'))
        
        # Check response is successful
        self.assertEqual(response.status_code, 200)
        
        # Check context contains correct tasks for worker1
        context = response.context
        
        # Check that worker1's tasks are in the appropriate status lists
        in_progress_tasks = list(context['in_progress_tasks'])
        upcoming_tasks = list(context['upcoming_tasks'])
        
        self.assertIn(self.task1_worker1, in_progress_tasks)
        self.assertIn(self.task2_worker1, upcoming_tasks)
        
        # Check that worker2's tasks are NOT in the context
        all_tasks_in_context = (
            list(context.get('upcoming_tasks', [])) +
            list(context.get('in_progress_tasks', [])) +
            list(context.get('almost_overdue_tasks', [])) +
            list(context.get('overdue_tasks', [])) +
            list(context.get('completed_tasks', []))
        )
        
        self.assertNotIn(self.task1_worker2, all_tasks_in_context)
        self.assertNotIn(self.unassigned_task, all_tasks_in_context)
        
        # Check statistics
        self.assertEqual(context['total_assigned'], 2)  # worker1 has 2 tasks
        self.assertEqual(context['pending_tasks'], 2)   # both are pending (not completed)
    
    def test_worker_dashboard_access_control(self):
        """
        Test that only workers can access the worker dashboard.
        **Validates: Requirements 3.1**
        """
        # Test unauthenticated access
        response = self.client.get(reverse('worker:worker_dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Create a client user (non-worker)
        client_user = User.objects.create_user(
            username='client1',
            email='client1@example.com',
            password='testpass123'
        )
        
        # Verify profile was created and has correct role
        client_profile = Profile.objects.get(user=client_user)
        self.assertEqual(client_profile.role, 'client')
        
        # Test client user access (should be blocked by middleware)
        self.client.login(username='client1', password='testpass123')
        response = self.client.get(reverse('worker:worker_dashboard'))
        
        # This should be handled by the RoleBasedAccessMiddleware
        # The middleware should redirect client users away from worker portal
        self.assertIn(response.status_code, [302, 403])  # Redirect or forbidden
    
    def test_worker_schedule_view_rendering(self):
        """
        Test that worker schedule view renders correctly with calendar.
        **Validates: Requirements 3.2, 3.3**
        """
        # Login as worker1
        self.client.login(username='worker1', password='testpass123')
        
        # Access worker schedule
        response = self.client.get(reverse('worker:worker_schedule'))
        
        # Check response is successful
        self.assertEqual(response.status_code, 200)
        
        # Check that the template contains calendar elements
        self.assertContains(response, 'id="calendar"')
        self.assertContains(response, 'FullCalendar')
        
        # Check that user tasks are in context
        context = response.context
        user_tasks = list(context['user_tasks'])
        
        self.assertIn(self.task1_worker1, user_tasks)
        self.assertIn(self.task2_worker1, user_tasks)
        self.assertNotIn(self.task1_worker2, user_tasks)
        self.assertNotIn(self.unassigned_task, user_tasks)
    
    def test_worker_task_events_api(self):
        """
        Test that worker task events API returns correct JSON data.
        **Validates: Requirements 3.2, 3.3**
        """
        # Login as worker1
        self.client.login(username='worker1', password='testpass123')
        
        # Access worker events API
        response = self.client.get(reverse('worker:worker_events'))
        
        # Check response is successful and JSON
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Parse JSON response
        import json
        events = json.loads(response.content)
        
        # Check that events contain worker1's tasks (titles may include location)
        event_titles = [event['title'] for event in events]
        
        # Check for task titles (may include location suffix)
        task1_found = any('Task 1 for Worker 1' in title for title in event_titles)
        task2_found = any('Task 2 for Worker 1' in title for title in event_titles)
        
        self.assertTrue(task1_found, f"Task 1 for Worker 1 not found in {event_titles}")
        self.assertTrue(task2_found, f"Task 2 for Worker 1 not found in {event_titles}")
        
        # Check that events don't contain other worker's tasks
        worker2_task_found = any('Task 1 for Worker 2' in title for title in event_titles)
        unassigned_task_found = any('Unassigned Task' in title for title in event_titles)
        
        self.assertFalse(worker2_task_found, "Should not contain other worker's tasks")
        self.assertFalse(unassigned_task_found, "Should not contain unassigned tasks")
        
        # Check event structure
        if events:
            event = events[0]
            required_fields = ['id', 'title', 'start', 'backgroundColor', 'borderColor']
            for field in required_fields:
                self.assertIn(field, event)
            
            # Check extended properties
            self.assertIn('extendedProps', event)
            extended_props = event['extendedProps']
            self.assertIn('status', extended_props)
    
    def test_task_completion_workflow(self):
        """
        Test the task completion workflow including status updates.
        **Validates: Requirements 3.4**
        """
        # Login as worker1
        self.client.login(username='worker1', password='testpass123')
        
        # Ensure task is not completed initially
        self.assertNotEqual(self.task1_worker1.status, Task.STATUS_COMPLETED)
        self.assertIsNone(self.task1_worker1.completed_by)
        
        # Complete the task
        completion_data = {
            'completion_notes': 'Task completed successfully with no issues.'
        }
        
        response = self.client.post(
            reverse('worker:complete', kwargs={'pk': self.task1_worker1.pk}),
            data=completion_data
        )
        
        # Check response (should redirect or return success)
        self.assertIn(response.status_code, [200, 302])
        
        # Refresh task from database
        self.task1_worker1.refresh_from_db()
        
        # Check that task status was updated
        self.assertEqual(self.task1_worker1.status, Task.STATUS_COMPLETED)
        self.assertEqual(self.task1_worker1.completed_by, self.worker1)
        self.assertEqual(self.task1_worker1.completion_notes, 'Task completed successfully with no issues.')
    
    def test_task_completion_access_control(self):
        """
        Test that workers can only complete their own assigned tasks.
        **Validates: Requirements 3.4**
        """
        # Login as worker1
        self.client.login(username='worker1', password='testpass123')
        
        # Try to complete worker2's task (should fail)
        response = self.client.post(
            reverse('worker:complete', kwargs={'pk': self.task1_worker2.pk}),
            data={'completion_notes': 'Trying to complete other worker task'}
        )
        
        # Should return 404 (task not found for this worker)
        self.assertEqual(response.status_code, 404)
        
        # Check that worker2's task was not modified
        self.task1_worker2.refresh_from_db()
        self.assertNotEqual(self.task1_worker2.status, Task.STATUS_COMPLETED)
        self.assertIsNone(self.task1_worker2.completed_by)
    
    def test_task_completion_already_completed(self):
        """
        Test handling of attempting to complete an already completed task.
        **Validates: Requirements 3.4**
        """
        # Login as worker1
        self.client.login(username='worker1', password='testpass123')
        
        # Mark task as completed first
        self.task1_worker1.status = Task.STATUS_COMPLETED
        self.task1_worker1.completed_by = self.worker1
        self.task1_worker1.completion_notes = 'Already completed'
        self.task1_worker1.save()
        
        # Try to complete it again
        response = self.client.post(
            reverse('worker:complete', kwargs={'pk': self.task1_worker1.pk}),
            data={'completion_notes': 'Trying to complete again'}
        )
        
        # Should redirect with warning message
        self.assertEqual(response.status_code, 302)
        
        # Check that task wasn't modified
        self.task1_worker1.refresh_from_db()
        self.assertEqual(self.task1_worker1.completion_notes, 'Already completed')
    
    def test_worker_dashboard_task_status_separation(self):
        """
        Test that tasks are correctly separated by status in the dashboard.
        **Validates: Requirements 3.1**
        """
        # Create tasks with different statuses for worker1
        overdue_task = Task.objects.create(
            title='Overdue Task',
            start_date=date.today() - timedelta(days=5),
            due_date=date.today() - timedelta(days=1),
            status=Task.STATUS_OVERDUE,
            assigned_to=self.worker1
        )
        
        almost_overdue_task = Task.objects.create(
            title='Almost Overdue Task',
            start_date=date.today(),
            due_date=date.today() + timedelta(days=1),
            status=Task.STATUS_ALMOST_OVERDUE,
            assigned_to=self.worker1
        )
        
        completed_task = Task.objects.create(
            title='Completed Task',
            start_date=date.today() - timedelta(days=3),
            due_date=date.today() - timedelta(days=1),
            status=Task.STATUS_COMPLETED,
            assigned_to=self.worker1,
            completed_by=self.worker1
        )
        
        # Login as worker1
        self.client.login(username='worker1', password='testpass123')
        
        # Access worker dashboard
        response = self.client.get(reverse('worker:worker_dashboard'))
        context = response.context
        
        # Check that tasks are in correct status lists
        self.assertIn(overdue_task, list(context['overdue_tasks']))
        self.assertIn(almost_overdue_task, list(context['almost_overdue_tasks']))
        self.assertIn(completed_task, list(context['completed_tasks']))
        
        # Check that tasks are not in wrong status lists
        self.assertNotIn(overdue_task, list(context['upcoming_tasks']))
        self.assertNotIn(completed_task, list(context['in_progress_tasks']))
    
    def test_worker_dashboard_statistics(self):
        """
        Test that dashboard statistics are calculated correctly.
        **Validates: Requirements 3.1**
        """
        # Create additional tasks for worker1
        completed_task = Task.objects.create(
            title='Completed Task',
            start_date=date.today() - timedelta(days=3),
            due_date=date.today() - timedelta(days=1),
            status=Task.STATUS_COMPLETED,
            assigned_to=self.worker1,
            completed_by=self.worker1
        )
        
        # Login as worker1
        self.client.login(username='worker1', password='testpass123')
        
        # Access worker dashboard
        response = self.client.get(reverse('worker:worker_dashboard'))
        context = response.context
        
        # Check statistics
        # worker1 should have 3 total tasks (2 from setUp + 1 completed)
        self.assertEqual(context['total_assigned'], 3)
        # 2 pending tasks (the original 2 from setUp, completed task doesn't count)
        self.assertEqual(context['pending_tasks'], 2)
    
    def test_htmx_task_completion_response(self):
        """
        Test that HTMX requests for task completion return proper JSON response.
        **Validates: Requirements 3.4**
        """
        # Login as worker1
        self.client.login(username='worker1', password='testpass123')
        
        # Make HTMX request to complete task
        response = self.client.post(
            reverse('worker:complete', kwargs={'pk': self.task1_worker1.pk}),
            data={'completion_notes': 'Completed via HTMX'},
            HTTP_HX_REQUEST='true'  # Simulate HTMX request
        )
        
        # Check response is JSON
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Parse JSON response
        import json
        response_data = json.loads(response.content)
        
        # Check response structure
        self.assertIn('status', response_data)
        self.assertIn('message', response_data)
        self.assertEqual(response_data['status'], 'success')
        
        # Verify task was actually completed
        self.task1_worker1.refresh_from_db()
        self.assertEqual(self.task1_worker1.status, Task.STATUS_COMPLETED)
        self.assertEqual(self.task1_worker1.completion_notes, 'Completed via HTMX')


class WorkerPortalViewTests(TestCase):
    """Unit tests for Worker Portal view classes."""
    
    def setUp(self):
        """Set up test data."""
        self.workers_group, _ = Group.objects.get_or_create(name='Workers')
        
        self.worker = User.objects.create_user(
            username='testworker',
            email='testworker@example.com',
            password='testpass123'
        )
        Profile.objects.filter(user=self.worker).update(role='worker')
        self.worker.groups.add(self.workers_group)
        
        # Create test tasks
        self.task = Task.objects.create(
            title='Test Task',
            start_date=date.today(),
            due_date=date.today() + timedelta(days=7),
            status=Task.STATUS_IN_PROGRESS,
            assigned_to=self.worker
        )
    
    def test_worker_dashboard_view_context(self):
        """Test WorkerDashboardView context data generation."""
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/worker/')
        request.user = self.worker
        
        view = WorkerDashboardView()
        view.request = request
        
        context = view.get_context_data()
        
        # Check that all required context keys are present
        required_keys = [
            'upcoming_tasks', 'in_progress_tasks', 'almost_overdue_tasks',
            'overdue_tasks', 'completed_tasks', 'total_assigned', 'pending_tasks'
        ]
        
        for key in required_keys:
            self.assertIn(key, context)
        
        # Check that task is in correct status list
        self.assertIn(self.task, list(context['in_progress_tasks']))
        
        # Check statistics
        self.assertEqual(context['total_assigned'], 1)
        self.assertEqual(context['pending_tasks'], 1)
    
    def test_worker_schedule_view_context(self):
        """Test WorkerScheduleView context data generation."""
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/worker/schedule/')
        request.user = self.worker
        
        view = WorkerScheduleView()
        view.request = request
        
        context = view.get_context_data()
        
        # Check that user_tasks is in context
        self.assertIn('user_tasks', context)
        
        # Check that task is in user_tasks
        user_tasks = list(context['user_tasks'])
        self.assertIn(self.task, user_tasks)