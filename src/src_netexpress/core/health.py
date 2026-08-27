from uuid import uuid4
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse


def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        key = "health:" + uuid4().hex
        cache.set(key, "ok", 10)
        if cache.get(key) != "ok":
            raise RuntimeError("Cache unavailable")
        cache.delete(key)
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})
