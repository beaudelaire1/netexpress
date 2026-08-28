"""Tests never write into user media or contact production services."""
import os
import socket
import pytest


@pytest.fixture(autouse=True)
def isolated_services(settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.PRIVATE_MEDIA_ROOT = tmp_path / "private"
    settings.STATIC_ROOT = tmp_path / "static"
    settings.STATIC_ROOT.mkdir()
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.BREVO_API_KEY = ""
    settings.TURNSTILE_SITE_KEY = ""
    settings.TURNSTILE_SECRET_KEY = ""
    original = socket.socket.connect

    def offline(sock, address):
        if os.getenv("TEST_DATABASE_URL") and isinstance(address, tuple) and address[0] in {"127.0.0.1", "localhost", "::1"}:
            return original(sock, address)
        raise OSError("External network disabled in tests")

    monkeypatch.setattr(socket.socket, "connect", offline)
    from django.core.cache import cache
    cache.clear()
