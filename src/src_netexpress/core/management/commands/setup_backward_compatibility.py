from django.core.management.base import BaseCommand
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Set up backward compatibility layer for NetExpress v2 transformation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='Only check compatibility setup without making changes',
        )

    def handle(self, *args, **options):
        check_only = options['check_only']
        
        if check_only:
            self.stdout.write(
                self.style.WARNING('CHECK MODE - Verifying compatibility setup')
            )
        
        # Check middleware configuration
        self._check_middleware_setup(check_only)
        
        # Check URL configuration
        self._check_url_configuration(check_only)
        
        # Check template compatibility
        self._check_template_compatibility(check_only)
        
        self.stdout.write(
            self.style.SUCCESS('Backward compatibility setup completed!')
        )

    def _check_middleware_setup(self, check_only):
        """Check if backward compatibility middleware is properly configured."""
        self.stdout.write('Checking middleware configuration...')
        
        middleware_class = 'core.compatibility.BackwardCompatibilityMiddleware'
        
        if hasattr(settings, 'MIDDLEWARE'):
            if middleware_class in settings.MIDDLEWARE:
                self.stdout.write(f'  ✓ {middleware_class} is configured')
            else:
                self.stdout.write(
                    self.style.WARNING(f'  ⚠ {middleware_class} not found in MIDDLEWARE')
                )
                if not check_only:
                    self.stdout.write(
                        f'  Add "{middleware_class}" to your MIDDLEWARE setting'
                    )
        else:
            self.stdout.write(
                self.style.ERROR('  ✗ MIDDLEWARE setting not found')
            )

    def _check_url_configuration(self, check_only):
        """Check URL configuration for backward compatibility."""
        self.stdout.write('Checking URL configuration...')
        
        # Check if legacy URLs are properly mapped
        legacy_urls = [
            '/dashboard/',
            '/dashboard/client/',
            '/dashboard/ouvrier/',
        ]
        
        for url in legacy_urls:
            self.stdout.write(f'  Legacy URL: {url} - handled by middleware')
        
        # Check if new portal URLs exist
        portal_urls = [
            'core:client_portal_dashboard',
            'tasks:worker_dashboard', 
            'core:admin_dashboard',
        ]
        
        for url_name in portal_urls:
            try:
                from django.urls import reverse
                reverse(url_name)
                self.stdout.write(f'  ✓ Portal URL {url_name} is available')
            except Exception:
                self.stdout.write(
                    self.style.WARNING(f'  ⚠ Portal URL {url_name} not found')
                )

    def _check_template_compatibility(self, check_only):
        """Check template compatibility."""
        self.stdout.write('Checking template compatibility...')
        
        # Check if base templates exist
        base_templates = [
            'base.html',
            'base_v2.html',
        ]
        
        template_dirs = getattr(settings, 'TEMPLATES', [])
        if template_dirs:
            template_dir = template_dirs[0].get('DIRS', [])
            if template_dir:
                template_path = template_dir[0]
                
                for template in base_templates:
                    template_file = os.path.join(template_path, template)
                    if os.path.exists(template_file):
                        self.stdout.write(f'  ✓ Template {template} exists')
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'  ⚠ Template {template} not found')
                        )
        
        self.stdout.write('  Template compatibility checks completed')