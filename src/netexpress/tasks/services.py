"""Utility services for the tasks application.

This module exposes :class:`EmailNotificationService` which simplifies
sending plain text emails with optional attachments using Django's
configured email backend. This supports both SMTP and API-based backends
(like Brevo) through Django's EMAIL_BACKEND setting.

Configuration is read from :mod:`django.conf.settings`. For SMTP, define:

``EMAIL_HOST``
    The SMTP server hostname (e.g. ``smtp.gmail.com``).
``EMAIL_PORT``
    The port number used to connect to the SMTP server (465 for SSL or
    587 for STARTTLS).
``EMAIL_HOST_USER``
    The username used to authenticate with the SMTP server.
``EMAIL_HOST_PASSWORD``
    The password or app‑specific token for the above account.
``EMAIL_USE_SSL``
    A boolean indicating whether to use an implicit SSL connection.

For Brevo API, define:

``EMAIL_BACKEND_TYPE``
    Set to 'brevo' to use Brevo API backend.
``BREVO_API_KEY``
    Your Brevo API key from https://app.brevo.com/settings/keys/api

``DEFAULT_FROM_EMAIL``
    The default sender address for all emails.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import EmailMessage as DjangoEmailMessage


class EmailNotificationService:
    """Email service that uses Django's configured backend.

    This service sends plain text messages and supports arbitrary
    attachments. Attachments are supplied as an iterable of
    ``(filename, content_bytes)`` tuples. The service automatically
    uses the configured EMAIL_BACKEND (SMTP, Brevo, or others).
    """

    logger = logging.getLogger(__name__)

    @classmethod
    def send(
        cls,
        to_email: str,
        subject: str,
        body: str,
        attachments: list[tuple[str, bytes]] | None = None,
    ) -> None:
        """Send an email via Django's configured backend.

        This method uses Django's EmailMessage class which automatically
        uses the configured EMAIL_BACKEND (SMTP, Brevo API, or others).

        Parameters
        ----------
        to_email : str
            Recipient email address.  Multiple recipients are not
            supported; call this method once per recipient.
        subject : str
            Subject line of the email.
        body : str
            Plain text body of the email.
        attachments : list of tuple(str, bytes), optional
            Optional list of attachments.  Each tuple must contain the
            filename and the binary content of the file.
        """
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com")

        try:
            # Create Django EmailMessage
            email = DjangoEmailMessage(
                subject=subject,
                body=body,
                from_email=from_email,
                to=[to_email],
            )

            # Attach files if provided
            for fname, content in (attachments or []):
                email.attach(fname, content)

            # Send via configured backend (SMTP, Brevo, etc.)
            email.send(fail_silently=False)
            cls.logger.info(f"E‑mail envoyé avec succès à {to_email}")
        except Exception as exc:
            cls.logger.error(f"Échec de l'envoi de l'e‑mail à {to_email}: {exc}")
            raise
