"""
Property-based tests for Worker Portal task assignment visibility.

**Feature: netexpress-v2-transformation, Property 3: Task assignment visibility**
**Validates: Requirements 3.1**
"""

import pytest
import uuid
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import from_model, TestCase
from django.contrib.auth.models import User, Group
from django.test import RequestFactory
from datetime import date, timedelta

from tasks.models import Task
from accounts.models import Profile


# Strategies for generating test data
@st.composite
def worker_user(draw):
    """Generate a worker user with proper role and group assignment."""
    base_username = draw(st.text(min_size=5, max_size=15, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    # Add UUID suffix to ensure uniqueness
    username = f"{base_username}_{str(uuid.uuid4())[:8]}"
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
def task_assigned_to_user(draw, assigned_user):
    """Generate a Task assigned to a specific user."""
    title = draw(st.text(min_size=5, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))))
    description = draw(st.text(min_size=0, max_size=200, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))))
    location = draw(st.text(min_size=0, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))))
    team = draw(st.text(min_size=0, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))))
    
    # Generate dates
    start_date = draw(st.dates(min_value=date.today() - timedelta(days=30), max_value=date.today() + timedelta(days=30)))
    due_date = draw(st.dates(min_value=start_date, max_value=start_date + timedelta(days=60)))
    
    status = draw(st.sampled_from([Task.STATUS_UPCOMING, Task.STATUS_IN_PROGRESS, Task.STATUS_COMPLETED, Task.STATUS_OVERDUE, Task.STATUS_ALMOST_OVERDUE]))
    
    task = Task.objects.create(
        title=title,
        description=description,
        location=location,
        team=team,
        start_date=start_date,
        due_date=due_date,
        status=status,
        assigned_to=assigned_user
    )
    return task


@st.composite
def unassigned_task(draw):
    """Generate a Task with no assigned user."""
    title = draw(st.text(min_size=5, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))))
    description = draw(st.text(min_size=0, max_size=200, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))))
    location = draw(st.text(min_size=0, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))))
    team = draw(st.text(min_size=0, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))))
    
    # Generate dates
    start_date = draw(st.dates(min_value=date.today() - timedelta(days=30), max_value=date.today() + timedelta(days=30)))
    due_date = draw(st.dates(min_value=start_date, max_value=start_date + timedelta(days=60)))
    
    status = draw(st.sampled_from([Task.STATUS_UPCOMING, Task.STATUS_IN_PROGRESS, Task.STATUS_COMPLETED, Task.STATUS_OVERDUE, Task.STATUS_ALMOST_OVERDUE]))
    
    task = Task.objects.create(
        title=title,
        description=description,
        location=location,
        team=team,
        start_date=start_date,
        due_date=due_date,
        status=status,
        assigned_to=None  # No assigned user
    )
    return task


class TestTaskAssignmentVisibilityProperties(TestCase):
    """Property-based tests for task assignment visibility in Worker Portal."""
    
    def setUp(self):
        """Set up test environment."""
        # Ensure Workers group exists
        Group.objects.get_or_create(name='Workers')
    
    @settings(max_examples=20, deadline=None)
    @given(
        worker1_data=worker_user(),
        worker2_data=worker_user(),
        data=st.data(),
    )
    def test_property_worker_sees_only_assigned_tasks(self, worker1_data, worker2_data, data):
        """
        Property 3: Task assignment visibility
        
        For any worker user, the worker portal should display all and only
        the tasks that are assigned to that specific worker.
        
        **Validates: Requirements 3.1**
        """
        # Create two different workers
        worker1 = worker1_data
        worker2 = worker2_data
        
        # Ensure workers have different usernames
        if worker1.username == worker2.username:
            worker2.username = f"different_{worker2.username}"
            worker2.save()
        
        # Create tasks assigned to worker1 using data.draw()
        worker1_task1 = data.draw(task_assigned_to_user(worker1))
        worker1_task2 = data.draw(task_assigned_to_user(worker1))
        
        # Create tasks assigned to worker2 using data.draw()
        worker2_task1 = data.draw(task_assigned_to_user(worker2))
        worker2_task2 = data.draw(task_assigned_to_user(worker2))
        
        # Create unassigned tasks using data.draw()
        unassigned_task1 = data.draw(unassigned_task())
        unassigned_task2 = data.draw(unassigned_task())
        
        # Test: Worker1 should only see tasks assigned to them
        worker1_tasks = Task.objects.filter(assigned_to=worker1)
        
        # Worker1 should see their own tasks
        assert worker1_task1 in worker1_tasks, "Worker should see their own assigned task"
        assert worker1_task2 in worker1_tasks, "Worker should see all their assigned tasks"
        
        # Worker1 should NOT see other worker's tasks
        assert worker2_task1 not in worker1_tasks, "Worker should not see other worker's tasks"
        assert worker2_task2 not in worker1_tasks, "Worker should not see any tasks assigned to others"
        
        # Worker1 should NOT see unassigned tasks
        assert unassigned_task1 not in worker1_tasks, "Worker should not see unassigned tasks"
        assert unassigned_task2 not in worker1_tasks, "Worker should not see any unassigned tasks"
        
        # Test: Worker2 should only see tasks assigned to them
        worker2_tasks = Task.objects.filter(assigned_to=worker2)
        
        # Worker2 should see their own tasks
        assert worker2_task1 in worker2_tasks, "Worker should see their own assigned task"
        assert worker2_task2 in worker2_tasks, "Worker should see all their assigned tasks"
        
        # Worker2 should NOT see other worker's tasks
        assert worker1_task1 not in worker2_tasks, "Worker should not see other worker's tasks"
        assert worker1_task2 not in worker2_tasks, "Worker should not see any tasks assigned to others"
        
        # Worker2 should NOT see unassigned tasks
        assert unassigned_task1 not in worker2_tasks, "Worker should not see unassigned tasks"
        assert unassigned_task2 not in worker2_tasks, "Worker should not see any unassigned tasks"
        
        # Test: Verify task counts are correct
        assert worker1_tasks.count() >= 2, "Worker should see at least their assigned tasks"
        assert worker2_tasks.count() >= 2, "Worker should see at least their assigned tasks"
        
        # Test: Verify no overlap between workers' task lists
        worker1_task_ids = set(worker1_tasks.values_list('id', flat=True))
        worker2_task_ids = set(worker2_tasks.values_list('id', flat=True))
        assert worker1_task_ids.isdisjoint(worker2_task_ids), "Workers should not see each other's tasks"
    
    @settings(max_examples=15, deadline=None)
    @given(
        worker_data=worker_user(),
        data=st.data(),
    )
    def test_property_worker_sees_all_assigned_tasks_regardless_of_status(self, worker_data, data):
        """
        Property 3: Task assignment visibility (all statuses)
        
        For any worker user, the worker portal should display ALL tasks assigned
        to that worker, regardless of their status (upcoming, in progress, completed, etc.).
        
        **Validates: Requirements 3.1**
        """
        worker = worker_data
        
        # Create tasks with different statuses by controlling dates
        # Note: Task model automatically calculates status based on dates
        
        # Upcoming task: start_date in future
        upcoming_task = data.draw(task_assigned_to_user(worker))
        upcoming_task.start_date = date.today() + timedelta(days=5)
        upcoming_task.due_date = date.today() + timedelta(days=10)
        upcoming_task.save()
        
        # In progress task: start_date today or past, due_date future (more than 1 day)
        in_progress_task = data.draw(task_assigned_to_user(worker))
        in_progress_task.start_date = date.today() - timedelta(days=1)
        in_progress_task.due_date = date.today() + timedelta(days=5)
        in_progress_task.save()
        
        # Almost overdue task: due_date tomorrow or today
        almost_overdue_task = data.draw(task_assigned_to_user(worker))
        almost_overdue_task.start_date = date.today() - timedelta(days=2)
        almost_overdue_task.due_date = date.today() + timedelta(days=1)
        almost_overdue_task.save()
        
        # Overdue task: due_date in past
        overdue_task = data.draw(task_assigned_to_user(worker))
        overdue_task.start_date = date.today() - timedelta(days=5)
        overdue_task.due_date = date.today() - timedelta(days=1)
        overdue_task.save()
        
        # Completed task: manually set to completed (this won't be overridden)
        completed_task = data.draw(task_assigned_to_user(worker))
        completed_task.status = Task.STATUS_COMPLETED
        completed_task.save()
        
        # Test: Worker should see all their tasks regardless of status
        worker_tasks = Task.objects.filter(assigned_to=worker)
        
        assert upcoming_task in worker_tasks, "Worker should see upcoming tasks assigned to them"
        assert in_progress_task in worker_tasks, "Worker should see in-progress tasks assigned to them"
        assert completed_task in worker_tasks, "Worker should see completed tasks assigned to them"
        assert overdue_task in worker_tasks, "Worker should see overdue tasks assigned to them"
        assert almost_overdue_task in worker_tasks, "Worker should see almost overdue tasks assigned to them"
        
        # Test: Verify different statuses are represented
        worker_task_statuses = set(worker_tasks.values_list('status', flat=True))
        
        # We should have at least 3 different statuses (upcoming, in_progress/almost_overdue, overdue, completed)
        assert len(worker_task_statuses) >= 3, f"Worker should see tasks of multiple statuses, got: {worker_task_statuses}"
        
        # Verify specific statuses exist
        assert Task.STATUS_UPCOMING in worker_task_statuses, "Should have upcoming task"
        assert Task.STATUS_OVERDUE in worker_task_statuses, "Should have overdue task"
        assert Task.STATUS_COMPLETED in worker_task_statuses, "Should have completed task"
    
    @settings(max_examples=10, deadline=None)
    @given(
        worker_data=worker_user(),
        data=st.data(),
    )
    def test_property_unassigned_tasks_not_visible_to_any_worker(self, worker_data, data):
        """
        Property 3: Task assignment visibility (unassigned tasks)
        
        For any worker user, unassigned tasks (tasks with assigned_to=None)
        should never be visible in their task list.
        
        **Validates: Requirements 3.1**
        """
        worker = worker_data
        
        # Create some tasks assigned to the worker using data.draw()
        assigned_task = data.draw(task_assigned_to_user(worker))
        
        # Create unassigned tasks using data.draw()
        unassigned_task1 = data.draw(unassigned_task())
        unassigned_task2 = data.draw(unassigned_task())
        unassigned_task3 = data.draw(unassigned_task())
        
        # Test: Worker should only see assigned tasks
        worker_tasks = Task.objects.filter(assigned_to=worker)
        
        # Worker should see their assigned task
        assert assigned_task in worker_tasks, "Worker should see tasks assigned to them"
        
        # Worker should NOT see any unassigned tasks
        assert unassigned_task1 not in worker_tasks, "Worker should not see unassigned tasks"
        assert unassigned_task2 not in worker_tasks, "Worker should not see any unassigned tasks"
        assert unassigned_task3 not in worker_tasks, "Worker should not see any unassigned tasks"
        
        # Test: Verify that all tasks in worker's list are assigned to them
        for task in worker_tasks:
            assert task.assigned_to == worker, f"All tasks in worker's list should be assigned to them, but found task {task.id} assigned to {task.assigned_to}"
        
        # Test: Verify unassigned tasks exist but are not in worker's list
        all_unassigned_tasks = Task.objects.filter(assigned_to=None)
        assert all_unassigned_tasks.count() >= 3, "Unassigned tasks should exist in the system"
        
        worker_task_ids = set(worker_tasks.values_list('id', flat=True))
        unassigned_task_ids = set(all_unassigned_tasks.values_list('id', flat=True))
        assert worker_task_ids.isdisjoint(unassigned_task_ids), "Worker's task list should not contain any unassigned tasks"
    
    @settings(max_examples=10, deadline=None)
    @given(
        worker_data=worker_user(),
        data=st.data(),
    )
    def test_property_task_assignment_is_exclusive(self, worker_data, data):
        """
        Property 3: Task assignment visibility (exclusivity)
        
        For any task assigned to a specific worker, that task should only
        be visible to that worker and not to any other worker.
        
        **Validates: Requirements 3.1**
        """
        worker1 = worker_data
        
        # Create a second worker
        worker2 = User.objects.create_user(
            username=f"worker2_{worker1.username}",
            email=f"worker2_{worker1.email}",
            password='testpass123'
        )
        Profile.objects.filter(user=worker2).update(role='worker')
        group, _ = Group.objects.get_or_create(name='Workers')
        worker2.groups.add(group)
        
        # Create a task assigned to worker1 using data.draw()
        worker1_task = data.draw(task_assigned_to_user(worker1))
        
        # Create a task assigned to worker2 using data.draw()
        worker2_task = data.draw(task_assigned_to_user(worker2))
        
        # Test: Each worker should only see their own tasks
        worker1_tasks = Task.objects.filter(assigned_to=worker1)
        worker2_tasks = Task.objects.filter(assigned_to=worker2)
        
        # Worker1 should see their task but not worker2's task
        assert worker1_task in worker1_tasks, "Worker should see their own assigned task"
        assert worker2_task not in worker1_tasks, "Worker should not see tasks assigned to other workers"
        
        # Worker2 should see their task but not worker1's task
        assert worker2_task in worker2_tasks, "Worker should see their own assigned task"
        assert worker1_task not in worker2_tasks, "Worker should not see tasks assigned to other workers"
        
        # Test: Verify task assignment exclusivity
        assert worker1_task.assigned_to == worker1, "Task should be assigned to the correct worker"
        assert worker2_task.assigned_to == worker2, "Task should be assigned to the correct worker"
        assert worker1_task.assigned_to != worker2, "Task should not be assigned to multiple workers"
        assert worker2_task.assigned_to != worker1, "Task should not be assigned to multiple workers"