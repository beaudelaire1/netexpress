$ErrorActionPreference = "Stop"

# Force les settings DEV pour la session en cours (Windows PowerShell / pwsh)
$env:DJANGO_SETTINGS_MODULE = "netexpress.settings.dev"

Write-Host "[OK] DJANGO_SETTINGS_MODULE=$env:DJANGO_SETTINGS_MODULE"

python manage.py runserver


