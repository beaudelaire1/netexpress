"""
Management command to generate session analytics reports.

Provides detailed analytics about portal usage patterns, user engagement,
and system performance metrics.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import PortalSession
from django.contrib.auth.models import User
from django.db.models import Count, Avg, Sum, Q
import json


class Command(BaseCommand):
    help = 'Generate session analytics reports for portal usage'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to analyze (default: 30)'
        )
        parser.add_argument(
            '--portal',
            type=str,
            choices=['client', 'worker', 'admin'],
            help='Specific portal to analyze (default: all portals)'
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['text', 'json'],
            default='text',
            help='Output format (default: text)'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path (default: stdout)'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        portal_type = options['portal']
        output_format = options['format']
        output_file = options['output']
        
        # Generate analytics data
        analytics_data = self.generate_analytics(days, portal_type)
        
        # Format output
        if output_format == 'json':
            output = self.format_json(analytics_data)
        else:
            output = self.format_text(analytics_data)
        
        # Write output
        if output_file:
            with open(output_file, 'w') as f:
                f.write(output)
            self.stdout.write(
                self.style.SUCCESS(f'Analytics report written to {output_file}')
            )
        else:
            self.stdout.write(output)
    
    def generate_analytics(self, days, portal_type=None):
        """Generate comprehensive analytics data."""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Base queryset
        sessions = PortalSession.objects.filter(login_time__gte=cutoff_date)
        if portal_type:
            sessions = sessions.filter(portal_type=portal_type)
        
        # Overall statistics
        total_sessions = sessions.count()
        unique_users = sessions.values('user').distinct().count()
        total_users = User.objects.filter(is_active=True).count()
        
        # Session duration statistics
        completed_sessions = sessions.filter(logout_time__isnull=False)
        avg_duration = completed_sessions.aggregate(
            avg=Avg('session_duration')
        )['avg']
        
        # Page view statistics
        total_page_views = sessions.aggregate(
            total=Sum('pages_visited')
        )['total'] or 0
        
        avg_pages_per_session = sessions.aggregate(
            avg=Avg('pages_visited')
        )['avg'] or 0
        
        # Portal breakdown
        portal_breakdown = sessions.values('portal_type').annotate(
            session_count=Count('id'),
            unique_users=Count('user', distinct=True),
            total_pages=Sum('pages_visited')
        ).order_by('-session_count')
        
        # Daily activity
        daily_activity = []
        for i in range(days):
            date = (timezone.now() - timedelta(days=i)).date()
            day_sessions = sessions.filter(login_time__date=date)
            daily_activity.append({
                'date': date.isoformat(),
                'sessions': day_sessions.count(),
                'unique_users': day_sessions.values('user').distinct().count(),
                'page_views': day_sessions.aggregate(
                    total=Sum('pages_visited')
                )['total'] or 0
            })
        
        # Top users by activity
        top_users = sessions.values('user__username', 'user__first_name', 'user__last_name').annotate(
            session_count=Count('id'),
            total_pages=Sum('pages_visited'),
            total_time=Sum('session_duration')
        ).order_by('-session_count')[:10]
        
        # Peak hours analysis
        peak_hours = sessions.extra(
            select={'hour': 'EXTRACT(hour FROM login_time)'}
        ).values('hour').annotate(
            session_count=Count('id')
        ).order_by('-session_count')
        
        return {
            'period': {
                'days': days,
                'start_date': cutoff_date.date().isoformat(),
                'end_date': timezone.now().date().isoformat(),
                'portal_type': portal_type or 'all'
            },
            'overview': {
                'total_sessions': total_sessions,
                'unique_users': unique_users,
                'total_users': total_users,
                'user_engagement_rate': round((unique_users / total_users * 100), 2) if total_users > 0 else 0,
                'total_page_views': total_page_views,
                'avg_pages_per_session': round(avg_pages_per_session, 2),
                'avg_session_duration': str(avg_duration) if avg_duration else 'N/A'
            },
            'portal_breakdown': list(portal_breakdown),
            'daily_activity': daily_activity,
            'top_users': list(top_users),
            'peak_hours': list(peak_hours)
        }
    
    def format_text(self, data):
        """Format analytics data as human-readable text."""
        output = []
        
        # Header
        output.append("=" * 60)
        output.append("PORTAL SESSION ANALYTICS REPORT")
        output.append("=" * 60)
        output.append("")
        
        # Period information
        period = data['period']
        output.append(f"Analysis Period: {period['start_date']} to {period['end_date']}")
        output.append(f"Days Analyzed: {period['days']}")
        output.append(f"Portal Filter: {period['portal_type']}")
        output.append("")
        
        # Overview statistics
        overview = data['overview']
        output.append("OVERVIEW STATISTICS")
        output.append("-" * 20)
        output.append(f"Total Sessions: {overview['total_sessions']:,}")
        output.append(f"Unique Users: {overview['unique_users']:,}")
        output.append(f"Total Users: {overview['total_users']:,}")
        output.append(f"User Engagement Rate: {overview['user_engagement_rate']}%")
        output.append(f"Total Page Views: {overview['total_page_views']:,}")
        output.append(f"Avg Pages per Session: {overview['avg_pages_per_session']}")
        output.append(f"Avg Session Duration: {overview['avg_session_duration']}")
        output.append("")
        
        # Portal breakdown
        if data['portal_breakdown']:
            output.append("PORTAL BREAKDOWN")
            output.append("-" * 16)
            for portal in data['portal_breakdown']:
                output.append(f"{portal['portal_type'].title()} Portal:")
                output.append(f"  Sessions: {portal['session_count']:,}")
                output.append(f"  Unique Users: {portal['unique_users']:,}")
                output.append(f"  Page Views: {portal['total_pages'] or 0:,}")
                output.append("")
        
        # Top users
        if data['top_users']:
            output.append("TOP USERS BY ACTIVITY")
            output.append("-" * 22)
            for i, user in enumerate(data['top_users'][:5], 1):
                name = f"{user['user__first_name']} {user['user__last_name']}".strip()
                if not name:
                    name = user['user__username']
                output.append(f"{i}. {name}")
                output.append(f"   Sessions: {user['session_count']:,}")
                output.append(f"   Page Views: {user['total_pages'] or 0:,}")
                output.append("")
        
        # Peak hours
        if data['peak_hours']:
            output.append("PEAK USAGE HOURS")
            output.append("-" * 17)
            for hour_data in data['peak_hours'][:5]:
                hour = int(hour_data['hour'])
                output.append(f"{hour:02d}:00 - {hour+1:02d}:00: {hour_data['session_count']:,} sessions")
            output.append("")
        
        return "\n".join(output)
    
    def format_json(self, data):
        """Format analytics data as JSON."""
        return json.dumps(data, indent=2, default=str)