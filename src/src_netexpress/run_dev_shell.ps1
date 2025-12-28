$ErrorActionPreference = "Stop"

# Ouvre un shell Django en settings DEV
$env:DJANGO_SETTINGS_MODULE = "netexpress.settings.dev"

Write-Host "[OK] DJANGO_SETTINGS_MODULE=$env:DJANGO_SETTINGS_MODULE"

python manage.py shell


