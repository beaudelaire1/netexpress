from pathlib import Path
from django.http import FileResponse, Http404
from services.models import Category, Service
from core.models import Realisation


def public_image(request, name):
    # Never expose MEDIA_ROOT as a directory: it may still contain legacy private files.
    for queryset, field in [(Category.objects.all(), "icon"), (Service.objects.filter(is_active=True), "image"),
                            (Realisation.objects.filter(is_published=True), "image")]:
        obj = queryset.filter(**{field: name}).first()
        if obj:
            try:
                response = FileResponse(getattr(obj, field).open("rb"), filename=Path(name).name)
            except (OSError, ValueError):
                raise Http404
            response["X-Content-Type-Options"] = "nosniff"
            response["Content-Security-Policy"] = "default-src 'none'; sandbox"
            return response
    raise Http404
