# NetExpress v2 Setup and Configuration

## Overview

This document describes the setup and configuration completed for the NetExpress v2 transformation, which adds WYSIWYG messaging, TailwindCSS responsive design, and HTMX dynamic UI updates.

## Completed Setup Tasks

### 1. Python Dependencies

The following Python packages have been installed and added to `requirements/base.txt`:

- **django-ckeditor>=6.7.0** - WYSIWYG rich text editor for messaging
- **celery>=5.3.0** - Background task processing for notifications and emails
- **redis>=5.0.0** - Message broker for Celery

### 2. Frontend Dependencies

Since Node.js is not available in the development environment, we're using CDN versions of:

- **TailwindCSS 3.4.0** (via CDN) - Responsive design framework
- **HTMX 1.9.10** (via CDN) - Dynamic UI updates without full page reloads
- **Alpine.js 3.x** (via CDN) - Lightweight JavaScript framework for interactivity

### 3. Django Configuration

#### Settings Updates (`netexpress/settings/base.py`)

**New Apps Added:**
```python
'ckeditor',
'ckeditor_uploader',
```

**CKEditor Configuration:**
- Default configuration for general use
- Messaging configuration optimized for internal communication
- Admin configuration with full editing capabilities
- Upload path configured for media files

**Celery Configuration:**
- Redis broker URL configuration
- Task routing for different queues (messaging, documents, notifications)
- Task time limits configured

#### URL Configuration (`netexpress/urls.py`)

Added CKEditor URLs:
```python
path("ckeditor/", include("ckeditor_uploader.urls")),
```

### 4. Templates

#### New Base Template (`templates/base_v2.html`)

Created a new base template with:
- TailwindCSS integration via CDN
- HTMX integration for dynamic updates
- Alpine.js for enhanced interactivity
- Responsive navigation with mobile menu
- User authentication menu
- Notification system
- Loading indicators for HTMX requests
- Modern footer with contact information

### 5. Static Files

#### CSS (`static/css/style_v2.css`)

Created custom CSS with:
- Portal navigation styles
- Card components
- Button styles (primary, secondary, success, danger, outline)
- Form input styles
- Mobile-responsive utilities
- Task card styles for Worker Portal
- Document card styles for Client Portal
- KPI card styles for Admin Portal
- Notification styles
- HTMX loading states

#### JavaScript (`static/js/portal.js`)

Created portal JavaScript with:
- HTMX event handlers
- Notification system
- Tooltip initialization
- Mobile menu functionality
- Utility functions (formatDate, formatCurrency, debounce)
- Global NetExpress object for shared functionality

### 6. Package Configuration

#### package.json

Created for future Node.js integration (when available):
- TailwindCSS and plugins
- HTMX
- Build scripts for CSS compilation

#### tailwind.config.js

TailwindCSS configuration with:
- Custom color palette (ne-primary, ne-secondary)
- Extended spacing utilities
- Custom font family
- Plugins for forms and typography

## Usage

### Using the New Base Template

To use the new v2 template in your views:

```python
# In your template
{% extends "base_v2.html" %}

{% block content %}
    <!-- Your content here -->
{% endblock %}
```

### Using CKEditor in Forms

```python
from ckeditor.widgets import CKEditorWidget

class MessageForm(forms.Form):
    content = forms.CharField(
        widget=CKEditorWidget(config_name='messaging')
    )
```

### Using HTMX for Dynamic Updates

```html
<button 
    hx-post="/api/complete-task/{{ task.id }}/"
    hx-target="#task-{{ task.id }}"
    hx-swap="outerHTML"
    class="btn btn-success">
    Mark Complete
</button>
```

### Using TailwindCSS Classes

```html
<div class="card">
    <div class="card-header">
        <h2 class="text-xl font-bold">Task Details</h2>
    </div>
    <div class="card-body">
        <p class="text-gray-600">Task description...</p>
    </div>
</div>
```

## Running the Application

### Development Server

```bash
# Using base settings (SQLite)
python manage.py runserver --settings=netexpress.settings.base
```

### Celery Worker (for background tasks)

```bash
# Start Redis first (if not running)
redis-server

# Start Celery worker
celery -A netexpress worker -l info
```

### Collect Static Files

```bash
python manage.py collectstatic --noinput --settings=netexpress.settings.base
```

## Next Steps

The following tasks from the implementation plan are now ready to be executed:

1. ✅ **Task 1: Setup and Configuration** - COMPLETED
2. **Task 2: Role Management and Authentication Foundation** - Ready to implement
3. **Task 3: Messaging System with WYSIWYG** - Ready to implement
4. **Task 4-16**: Remaining implementation tasks

## Notes

### CKEditor Security Warning

The installed version of django-ckeditor (6.7.3) includes CKEditor 4.22.1, which has known security issues. For production use, consider:
- Upgrading to django-ckeditor-5 (if license terms are acceptable)
- Using the CKEditor 4 LTS package (non-free)
- Implementing additional security measures

### Node.js Installation

For optimal development experience, install Node.js to:
- Build TailwindCSS locally with custom configurations
- Use local HTMX instead of CDN
- Enable hot-reloading for CSS changes

Once Node.js is installed:
```bash
npm install
npm run build-css
```

### Redis Requirement

Celery requires Redis to be running for background task processing. Install Redis:
- **Windows**: Use WSL or download from https://redis.io/download
- **Linux/Mac**: `sudo apt-get install redis-server` or `brew install redis`

## Troubleshooting

### Migration Issues

If you encounter migration errors, you may need to fake certain migrations:
```bash
python manage.py migrate <app_name> <migration_number> --fake --settings=netexpress.settings.base
```

### Static Files Not Loading

Ensure static files are collected:
```bash
python manage.py collectstatic --noinput --settings=netexpress.settings.base
```

### CKEditor Media Not Loading

Check that MEDIA_URL and MEDIA_ROOT are properly configured in settings and that the media directory exists.

## Configuration Files Summary

- ✅ `requirements/base.txt` - Updated with new dependencies
- ✅ `netexpress/settings/base.py` - Added CKEditor and Celery configuration
- ✅ `netexpress/urls.py` - Added CKEditor URLs
- ✅ `templates/base_v2.html` - New base template with TailwindCSS and HTMX
- ✅ `static/css/style_v2.css` - Custom CSS for portal components
- ✅ `static/js/portal.js` - JavaScript for HTMX and portal functionality
- ✅ `package.json` - Node.js dependencies (for future use)
- ✅ `tailwind.config.js` - TailwindCSS configuration (for future use)

## Validation

Run the following commands to validate the setup:

```bash
# Check for configuration issues
python manage.py check --settings=netexpress.settings.base

# Verify migrations are up to date
python manage.py showmigrations --settings=netexpress.settings.base

# Test that static files are accessible
python manage.py findstatic css/style_v2.css --settings=netexpress.settings.base
```

All checks should pass with only the CKEditor security warning (which is expected and documented above).