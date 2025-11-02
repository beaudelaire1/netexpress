"""Utility services for the tasks application.

Currently this module exposes :class:`EmailNotificationService` which
simplifies sending plain text emails with optional attachments using
either SSL or STARTTLS depending on your configuration.  All
configuration values are read from :mod:`django.conf.settings`.  To
enable notifications you should define at least the following
settings:

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
``TASK_NOTIFICATION_EMAIL``
    Optional override for the default recipient address used by task
    notifications.  If not provided ``EMAIL_HOST_USER`` is used as
    fallback.

You may also define additional settings if you need to customise the
behaviour further (for example ``DEFAULT_FROM_EMAIL``), however
``EmailNotificationService`` will gracefully fall back to sensible
defaults.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

from django.conf import settings


class EmailNotificationService:
    """Simple SMTP wrapper for sending notification emails.

    This service sends plain text messages and supports arbitrary
    attachments.  Attachments are supplied as an iterable of
    ``(filename, content_bytes)`` tuples.  The service automatically
    chooses between SSL and STARTTLS based on the ``EMAIL_USE_SSL``
    setting.  Authentication is optional: if ``EMAIL_HOST_USER`` or
    ``EMAIL_HOST_PASSWORD`` are empty then no login attempt is made.
    """

    logger = logging.getLogger(__name__)

    @classmethod
    def send(
        cls,
        to_email: str,
        subject: str,
        body: str,
        attachments: list[tuple[str, bytes]] | None = None,
        *,
        html_body: str | None = None,
    ) -> None:
        """Send an email via the configured SMTP server.

        Parameters
        ----------
        to_email : str
            Recipient email address.  Multiple recipients are not
            supported; call this method once per recipient.
        subject : str
            Subject line of the email.
        body : str
            Plain text body of the email.  This will be used as the
            fallback plain text part if ``html_body`` is also supplied.
        attachments : list of tuple(str, bytes), optional
            Optional list of attachments.  Each tuple must contain the
            filename and the binary content of the file.
        html_body : str, optional keyword-only
            If provided, an additional HTML version of the message to
            include as a MIME ``text/html`` part.  When ``html_body`` is
            supplied the message will be sent as a multi-part/alternative
            to allow mail clients to choose the best representation.
        """
        host: str = getattr(settings, "EMAIL_HOST", "localhost")
        port: int = int(getattr(settings, "EMAIL_PORT", 25))
        username: str = getattr(settings, "EMAIL_HOST_USER", "")
        password: str = getattr(settings, "EMAIL_HOST_PASSWORD", "")
        use_ssl: bool = bool(getattr(settings, "EMAIL_USE_SSL", False))

        from_email = username or getattr(settings, "DEFAULT_FROM_EMAIL", "")
        if not from_email:
            from_email = "no-reply@example.com"

        # Build the root message container.  If an HTML body is provided
        # create an ``alternative`` subpart so that clients can choose
        # between plain text and HTML representations.
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_email

        if html_body:
            alternative = MIMEMultipart("alternative")
            # Always attach the plain text version first to provide a
            # fallback for clients that do not support HTML.
            alternative.attach(MIMEText(body or "", "plain", "utf-8"))
            alternative.attach(MIMEText(html_body, "html", "utf-8"))
            msg.attach(alternative)
        else:
            # Only plain text
            msg.attach(MIMEText(body or "", "plain", "utf-8"))

        # Attach files if provided
        for fname, content in (attachments or []):
            part = MIMEBase("application", "octet-stream")
            part.set_payload(content)
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename=\"{fname}\"",
            )
            msg.attach(part)

        try:
            if use_ssl:
                server = smtplib.SMTP_SSL(host, port)
            else:
                server = smtplib.SMTP(host, port)
                server.starttls()
            if username and password:
                server.login(username, password)
            server.sendmail(from_email, [to_email], msg.as_string())
            server.quit()
            cls.logger.info(f"E‑mail envoyé avec succès à {to_email}")
        except Exception as exc:
            cls.logger.error(f"Échec de l'envoi de l'e‑mail à {to_email}: {exc}")
