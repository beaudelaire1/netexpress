import hashlib

from django.conf import settings
from django.core.management.base import BaseCommand


def _fingerprint(value: str) -> str:
    """
    Retourne une empreinte courte (non sensible) pour comparer des clés sans les afficher.
    """
    if not value:
        return "none"
    h = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return h[:10]


class Command(BaseCommand):
    help = "Diagnostique la configuration Brevo (clé, backend, appel get_account)."

    def handle(self, *args, **options):
        brevo_key = (getattr(settings, "BREVO_API_KEY", "") or "").strip()

        self.stdout.write("=== CHECK BREVO ===")
        self.stdout.write(f"DEBUG={getattr(settings, 'DEBUG', None)}")
        self.stdout.write(f"EMAIL_BACKEND={getattr(settings, 'EMAIL_BACKEND', None)}")
        self.stdout.write(f"BREVO_API_KEY_set={bool(brevo_key)}")
        self.stdout.write(f"BREVO_API_KEY_fingerprint={_fingerprint(brevo_key)}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL={getattr(settings, 'DEFAULT_FROM_EMAIL', None)}")

        if not brevo_key:
            self.stdout.write(self.style.ERROR("BREVO_API_KEY est vide -> l'API Brevo ne peut pas fonctionner."))
            return

        try:
            import sib_api_v3_sdk
            from sib_api_v3_sdk.rest import ApiException
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Impossible d'importer sib_api_v3_sdk: {e}"))
            return

        cfg = sib_api_v3_sdk.Configuration()
        cfg.api_key["api-key"] = brevo_key
        api_client = sib_api_v3_sdk.ApiClient(cfg)

        try:
            account_api = sib_api_v3_sdk.AccountApi(api_client)
            account = account_api.get_account()
            self.stdout.write(self.style.SUCCESS("API OK: get_account() a réussi"))
            # champs utiles et non sensibles
            self.stdout.write(f"account.email={getattr(account, 'email', None)}")
            self.stdout.write(f"account.company_name={getattr(account, 'company_name', None)}")
        except ApiException as e:
            body = getattr(e, "body", None)
            self.stdout.write(self.style.ERROR(f"API ERROR: {e.status} {e.reason}"))
            if body:
                self.stdout.write(f"body={body}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erreur inattendue: {e}"))


