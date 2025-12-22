"""
Property-based tests for Admin Portal global planning completeness.

**Feature: netexpress-v2-transformation, Property 4: Global planning completeness**
**Validates: Requirements 4.2, 4.4**
"""

import pytest
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import from_model, TestCase
from django.contrib.auth.models import User, Group
from django.test import RequestFactory
from django.utils import timezone
from datetime import datetime, timedelta, date

from tasks.models import Task
from accounts.models import Profile
from core.views import admin_global_planning


# Strategies for generating test data
@st.composite
def worker_user(draw):
    """Generate a worker user."""
    # Use UUID to ensure unique usernames
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    username = f"worker_{unique_id}"
    email = f"{username}@example.com"
    
    user = User.objects.create_user(
        username=username,
        email=email,
        password='testpass123'
    )
    
    # Create profile with worker role
    Profile.objects.filter(user=user).update(role='worker')
    
    # Add to Workers group
    group, _ = Group.objects.get_or_create(name='Workers')
    user.groups.add(group)
    
    return user


@st.composite
def admin_user(draw):
    """Generate an admin user."""
    # Use UUID to ensure unique usernames
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    username = f"admin_{unique_id}"
    email = f"{username}@example.com"
    
    user = User.objects.create_user(
        username=username,
        email=email,
        password='testpass123',
        is_staff=True,
        is_superuser=True
    )
    
    return user


@st.composite
def task_for_worker(draw, worker=None, start_date=None, due_date=None):
    """Generate a Task optionally assigned to a specific worker."""
    title = draw(st.text(min_size=5, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))))
    description = draw(st.text(min_size=0, max_size=200, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))))
    location = draw(st.text(min_size=0, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))))
    team = draw(st.text(min_size=0, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))))
    
    # Use provided dates or generate random ones
    if start_date is None:
        start_date = draw(st.dates(min_value=date.today() - timedelta(days=30), 
                                 max_value=date.today() + timedelta(days=30)))
    if due_date is None:
        due_date = draw(st.dates(min_value=start_date, 
                               max_value=start_date + timedelta(days=14)))
    
    status = draw(st.sampled_from([
        Task.STATUS_UPCOMING,
        Task.STATUS_IN_PROGRESS,
        Task.STATUS_COMPLETED,
        Task.STATUS_OVERDUE,
        Task.STATUS_ALMOST_OVERDUE
    ]))
    
    task = Task.objects.create(
        title=title,
        description=description,
        location=location,
        team=team,
        start_date=start_date,
        due_date=due_date,
        status=status,
        assigned_to=worker
    )
    
    return task


@st.composite
def date_range(draw):
    """Generate a valid date range for planning view."""
    start = draw(st.dates(min_value=date.today() - timedelta(days=60), 
                         max_value=date.today() + timedelta(days=60)))
    end = draw(st.dates(min_value=start, 
                       max_value=start + timedelta(days=30)))
    return start, end


class TestGlobalPlanningCompletenessProperties(TestCase):
    """Property-based tests for global planning completeness."""
    
    def setUp(self):
        """Set up test environment."""
        # Ensure groups exist
        Group.objects.get_or_create(name='Workers')
        Group.objects.get_or_create(name='Clients')
        
        # Create request factory
        self.factory = RequestFactory()
    
    @settings(max_examples=2, deadline=None)
    @given(
        workers=st.lists(worker_user(), min_size=1, max_size=2),
        data=st.data(),
    )
    def test_property_all_workers_visible_in_global_planning(self, workers, data):
        """
        Property 4: Global planning completeness (workers)
        
        For any admin user viewing global planning, all existing workers
        should be visible in the planning interface.
        
        **Validates: Requirements 4.2, 4.4**
        """
        # Create admin user
        admin = data.draw(admin_user())
        
        # Generate date range for the planning view
        start_date, end_date = data.draw(date_range())
        
        # Create some tasks for workers within the date range
        for worker in workers:
            # Create 1 task per worker
            task_start = data.draw(st.dates(min_value=start_date, max_value=end_date))
            task_due = data.draw(st.dates(min_value=task_start, 
                                        max_value=min(end_date, task_start + timedelta(days=7))))
            data.draw(task_for_worker(worker, task_start, task_due))
        
        # Create request with date range parameters
        request = self.factory.get('/admin-dashboard/planning/', {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        })
        request.user = admin
        
        # Call the global planning view
        response = admin_global_planning(request)
        
        # Extract worker planning data from response context
        context = response.context_data if hasattr(response, 'context_data') else response.context
        worker_planning = context.get('worker_planning', [])
        
        # Property: All workers should be visible in the planning
        planning_workers = [wp['worker'] for wp in worker_planning]
        
        for worker in workers:
            assert worker in planning_workers, f"Worker {worker.username} should be visible in global planning"
        
        # Property: The number of workers in planning should match total workers
        total_workers_in_db = User.objects.filter(groups__name='Workers').count()
        assert len(planning_workers) == total_workers_in_db, "All workers should be included in planning view"
    
    @settings(max_examples=2, deadline=None)
    @given(
        workers=st.lists(worker_user(), min_size=1, max_size=2),
        data=st.data(),
    )
    def test_property_all_tasks_visible_in_global_planning(self, workers, data):
        """
        Property 4: Global planning completeness (tasks)
        
        For any admin user viewing global planning, all existing tasks
        within the specified date range should be visible in the planning interface.
        
        **Validates: Requirements 4.2, 4.4**
        """
        # Create admin user
        admin = data.draw(admin_user())
        
        # Generate date range for the planning view
        start_date, end_date = data.draw(date_range())
        
        # Create tasks within the date range
        tasks_in_range = []
        for worker in workers:
            # Create 1 task per worker within range
            task_start = data.draw(st.dates(min_value=start_date, max_value=end_date))
            task_due = data.draw(st.dates(min_value=task_start, 
                                        max_value=min(end_date, task_start + timedelta(days=7))))
            task = data.draw(task_for_worker(worker, task_start, task_due))
            tasks_in_range.append(task)
        
        # Create some tasks outside the date range (should not appear)
        tasks_outside_range = []
        if workers:  # Only if we have workers
            worker = workers[0]  # Use first worker
            # Task before range
            before_start = start_date - timedelta(days=10)
            before_due = start_date - timedelta(days=5)
            task_before = data.draw(task_for_worker(worker, before_start, before_due))
            tasks_outside_range.append(task_before)
        
        # Create 1 unassigned task within range
        unassigned_tasks = []
        task_start = data.draw(st.dates(min_value=start_date, max_value=end_date))
        task_due = data.draw(st.dates(min_value=task_start, 
                                    max_value=min(end_date, task_start + timedelta(days=7))))
        unassigned_task = data.draw(task_for_worker(None, task_start, task_due))
        unassigned_tasks.append(unassigned_task)
        
        # Create request with date range parameters
        request = self.factory.get('/admin-dashboard/planning/', {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        })
        request.user = admin
        
        # Call the global planning view
        response = admin_global_planning(request)
        
        # Extract task data from response context
        context = response.context_data if hasattr(response, 'context_data') else response.context
        all_tasks_in_view = context.get('all_tasks', Task.objects.none())
        unassigned_tasks_in_view = context.get('unassigned_tasks', Task.objects.none())
        worker_planning = context.get('worker_planning', [])
        
        # Property: All tasks within date range should be visible
        all_tasks_list = list(all_tasks_in_view)
        
        for task in tasks_in_range:
            assert task in all_tasks_list, f"Task {task.title} within date range should be visible in planning"
        
        for task in unassigned_tasks:
            assert task in all_tasks_list, f"Unassigned task {task.title} within date range should be visible in planning"
        
        # Property: Tasks outside date range should NOT be visible
        for task in tasks_outside_range:
            assert task not in all_tasks_list, f"Task {task.title} outside date range should not be visible in planning"
        
        # Property: Unassigned tasks should be properly identified
        unassigned_list = list(unassigned_tasks_in_view)
        for task in unassigned_tasks:
            assert task in unassigned_list, f"Unassigned task {task.title} should appear in unassigned tasks list"
        
        # Property: Worker-specific tasks should be properly grouped
        for worker_plan in worker_planning:
            worker = worker_plan['worker']
            worker_tasks = []
            
            # Collect all tasks for this worker from different status lists
            for status_key in ['upcoming_tasks', 'in_progress_tasks', 'completed_tasks', 'overdue_tasks', 'almost_overdue_tasks']:
                if status_key in worker_plan:
                    worker_tasks.extend(list(worker_plan[status_key]))
            
            # Check that all tasks assigned to this worker appear in their planning
            expected_worker_tasks = [t for t in tasks_in_range if t.assigned_to == worker]
            for expected_task in expected_worker_tasks:
                assert expected_task in worker_tasks, f"Task {expected_task.title} assigned to {worker.username} should appear in their planning"
    
    @settings(max_examples=2, deadline=None)
    @given(
        workers=st.lists(worker_user(), min_size=1, max_size=2),
        data=st.data(),
    )
    def test_property_task_assignment_completeness(self, workers, data):
        """
        Property 4: Global planning completeness (task assignments)
        
        For any admin user viewing global planning, the sum of all worker-assigned tasks
        plus unassigned tasks should equal the total number of tasks in the date range.
        
        **Validates: Requirements 4.2, 4.4**
        """
        # Create admin user
        admin = data.draw(admin_user())
        
        # Generate date range for the planning view
        start_date, end_date = data.draw(date_range())
        
        # Create a mix of assigned and unassigned tasks
        all_created_tasks = []
        
        # Create assigned tasks
        for worker in workers:
            task_start = data.draw(st.dates(min_value=start_date, max_value=end_date))
            task_due = data.draw(st.dates(min_value=task_start, 
                                        max_value=min(end_date, task_start + timedelta(days=7))))
            task = data.draw(task_for_worker(worker, task_start, task_due))
            all_created_tasks.append(task)
        
        # Create 1 unassigned task
        task_start = data.draw(st.dates(min_value=start_date, max_value=end_date))
        task_due = data.draw(st.dates(min_value=task_start, 
                                    max_value=min(end_date, task_start + timedelta(days=7))))
        task = data.draw(task_for_worker(None, task_start, task_due))
        all_created_tasks.append(task)
        
        # Create request with date range parameters
        request = self.factory.get('/admin-dashboard/planning/', {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        })
        request.user = admin
        
        # Call the global planning view
        response = admin_global_planning(request)
        
        # Extract data from response context
        context = response.context_data if hasattr(response, 'context_data') else response.context
        worker_planning = context.get('worker_planning', [])
        unassigned_tasks_in_view = context.get('unassigned_tasks', Task.objects.none())
        total_tasks_in_period = context.get('total_tasks_in_period', 0)
        assigned_tasks_count = context.get('assigned_tasks', 0)
        unassigned_count = context.get('unassigned_count', 0)
        
        # Property: Total tasks should equal assigned + unassigned
        assert assigned_tasks_count + unassigned_count == total_tasks_in_period, \
            "Sum of assigned and unassigned tasks should equal total tasks in period"
        
        # Property: Total tasks in view should match our created tasks
        assert total_tasks_in_period == len(all_created_tasks), \
            "Total tasks in planning view should match number of created tasks in date range"
        
        # Property: Count all tasks across all workers
        total_worker_tasks = 0
        for worker_plan in worker_planning:
            total_worker_tasks += worker_plan.get('total_tasks', 0)
        
        assert total_worker_tasks == assigned_tasks_count, \
            "Sum of tasks across all workers should equal assigned tasks count"
        
        # Property: Unassigned tasks count should match actual unassigned tasks
        actual_unassigned_count = len([t for t in all_created_tasks if t.assigned_to is None])
        assert unassigned_count == actual_unassigned_count, \
            "Unassigned tasks count should match actual number of unassigned tasks"
    
    @settings(max_examples=2, deadline=None)
    @given(
        workers=st.lists(worker_user(), min_size=1, max_size=2),
        data=st.data(),
    )
    def test_property_planning_view_accessibility_for_staff(self, workers, data):
        """
        Property 4: Global planning completeness (access control)
        
        For any staff/admin user, the global planning view should be accessible
        and return complete data. For non-staff users, access should be denied.
        
        **Validates: Requirements 4.2, 4.4**
        """
        # Create different types of users
        admin = data.draw(admin_user())
        
        # Create a regular client user
        client_user = User.objects.create_user(
            username='clientuser',
            email='client@example.com',
            password='testpass123'
        )
        Profile.objects.filter(user=client_user).update(role='client')
        
        # Create a worker user
        worker_user_obj = workers[0] if workers else data.draw(worker_user())
        
        # Generate date range
        start_date, end_date = data.draw(date_range())
        
        # Create some tasks
        for worker in workers:
            task_start = data.draw(st.dates(min_value=start_date, max_value=end_date))
            task_due = data.draw(st.dates(min_value=task_start, 
                                        max_value=min(end_date, task_start + timedelta(days=7))))
            data.draw(task_for_worker(worker, task_start, task_due))
        
        # Test admin access
        request = self.factory.get('/admin-dashboard/planning/', {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        })
        request.user = admin
        
        response = admin_global_planning(request)
        
        # Property: Admin should get successful response with complete data
        assert response.status_code == 200, "Admin should have access to global planning"
        
        context = response.context_data if hasattr(response, 'context_data') else response.context
        assert 'worker_planning' in context, "Admin should see worker planning data"
        assert 'total_tasks_in_period' in context, "Admin should see task statistics"
        assert 'all_tasks' in context, "Admin should see all tasks data"
        
        # Property: All workers should be represented in the planning data
        worker_planning = context.get('worker_planning', [])
        planning_worker_ids = {wp['worker'].id for wp in worker_planning}
        expected_worker_ids = {w.id for w in workers}
        
        assert expected_worker_ids.issubset(planning_worker_ids), \
            "All created workers should appear in admin's global planning view"