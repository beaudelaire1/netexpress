"""
Diagnostic de bout en bout de la configuration courriel.

Affiche le transport réellement utilisé puis envoie un message de test. C'est
le moyen le plus court de distinguer « le serveur refuse » de « personne ne
lit la boîte » quand les notifications semblent muettes.

    python manage.py send_test_email
    python manage.py send_test_email --to moi@exemple.fr
"""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Affiche la configuration email active et envoie un message de test."

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            dest="to",
            default="",
            help="Destinataire du test. Par défaut : CONTACT_RECEIVER_EMAIL, sinon DEFAULT_FROM_EMAIL.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche la configuration sans envoyer de message.",
        )

    def handle(self, *args, **options):
        backend = getattr(settings, "EMAIL_BACKEND", "")
        is_smtp = backend.endswith("smtp.EmailBackend")

        self.stdout.write("=== CONFIGURATION EMAIL ===")
        self.stdout.write(f"DEBUG                  = {getattr(settings, 'DEBUG', None)}")
        self.stdout.write(f"EMAIL_BACKEND          = {backend}")
        if is_smtp:
            self.stdout.write(f"EMAIL_HOST             = {getattr(settings, 'EMAIL_HOST', '')}")
            self.stdout.write(f"EMAIL_PORT             = {getattr(settings, 'EMAIL_PORT', '')}")
            self.stdout.write(f"EMAIL_USE_TLS          = {getattr(settings, 'EMAIL_USE_TLS', None)}")
            self.stdout.write(f"EMAIL_USE_SSL          = {getattr(settings, 'EMAIL_USE_SSL', None)}")
            self.stdout.write(f"EMAIL_HOST_USER        = {getattr(settings, 'EMAIL_HOST_USER', '')}")
            # Jamais le mot de passe : seulement de quoi voir s'il est renseigné.
            password = getattr(settings, "EMAIL_HOST_PASSWORD", "") or ""
            self.stdout.write(f"EMAIL_HOST_PASSWORD    = {'défini (%d caractères)' % len(password) if password else 'VIDE'}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL     = {getattr(settings, 'DEFAULT_FROM_EMAIL', '')}")
        self.stdout.write(f"CONTACT_RECEIVER_EMAIL = {getattr(settings, 'CONTACT_RECEIVER_EMAIL', '') or 'non défini'}")
        self.stdout.write(f"CONTACT_CC_EMAIL       = {getattr(settings, 'CONTACT_CC_EMAIL', '') or 'non défini'}")
        self.stdout.write(f"TASK_NOTIFICATION_EMAIL= {getattr(settings, 'TASK_NOTIFICATION_EMAIL', '') or 'non défini'}")
        self.stdout.write(f"NOTIFY_EMAILS_ASYNC    = {getattr(settings, 'NOTIFY_EMAILS_ASYNC', False)}")

        recipient = (
            options["to"]
            or getattr(settings, "CONTACT_RECEIVER_EMAIL", "")
            or getattr(settings, "DEFAULT_FROM_EMAIL", "")
        ).strip()

        if not recipient:
            raise CommandError(
                "Aucun destinataire : passe --to, ou renseigne CONTACT_RECEIVER_EMAIL "
                "ou DEFAULT_FROM_EMAIL."
            )

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(f"\n--dry-run : aucun envoi. Cible retenue : {recipient}"))
            return

        self.stdout.write(f"\nEnvoi d'un message de test à {recipient}…")

        message = EmailMultiAlternatives(
            subject="[Nettoyage Express] Test de configuration courriel",
            body=(
                "Ce message confirme que l'envoi de courriel fonctionne.\n\n"
                f"Transport : {backend}\n"
                f"Expéditeur : {getattr(settings, 'DEFAULT_FROM_EMAIL', '')}\n"
            ),
            to=[recipient],
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            # fail_silently=False : on veut l'erreur du relais, pas un silence.
            connection=get_connection(fail_silently=False),
        )
        message.attach_alternative(
            "<p>Ce message confirme que l'envoi de courriel fonctionne.</p>"
            f"<p>Transport&nbsp;: <code>{backend}</code></p>",
            "text/html",
        )

        try:
            sent = message.send(fail_silently=False)
        except Exception as exc:
            raise CommandError(f"Échec de l'envoi : {exc.__class__.__name__}: {exc}") from exc

        if sent:
            self.stdout.write(self.style.SUCCESS(f"OK : {sent} message accepté par le transport."))
            self.stdout.write(
                "Si rien n'arrive malgré ce succès, la piste suivante est le relais lui-même "
                "(expéditeur non vérifié, SPF/DKIM absents, message classé en indésirable)."
            )
        else:
            self.stdout.write(self.style.ERROR("Le transport a refusé le message (0 envoyé)."))
