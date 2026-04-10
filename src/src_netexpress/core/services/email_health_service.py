"""Diagnostic et supervision de la pile email NetExpress."""

from __future__ import annotations

import hashlib
from smtplib import SMTPAuthenticationError, SMTPException

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.validators import validate_email
from django.utils import timezone


def _fingerprint(value: str) -> str:
    if not value:
        return "none"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]


def _mask_value(value: str, prefix: int = 4, suffix: int = 2) -> str:
    if not value:
        return "Non configuré"
    if len(value) <= prefix + suffix:
        return f"{value[:1]}…{value[-1:]}"
    return f"{value[:prefix]}…{value[-suffix:]}"


class EmailHealthService:
    """Expose un rapport exploitable et des probes ciblés pour l'admin."""

    STATUS_LABELS = {
        "healthy": "Opérationnel",
        "warning": "À surveiller",
        "critical": "Action requise",
    }

    @staticmethod
    def _theme(status: str) -> dict:
        mapping = {
            "healthy": {
                "badge_class": "bg-emerald-100 text-emerald-700",
                "panel_bg_class": "bg-emerald-50/80",
                "panel_border_class": "border-emerald-200",
                "accent_class": "text-emerald-700",
            },
            "warning": {
                "badge_class": "bg-amber-100 text-amber-700",
                "panel_bg_class": "bg-amber-50/80",
                "panel_border_class": "border-amber-200",
                "accent_class": "text-amber-700",
            },
            "critical": {
                "badge_class": "bg-red-100 text-red-700",
                "panel_bg_class": "bg-red-50/80",
                "panel_border_class": "border-red-200",
                "accent_class": "text-red-700",
            },
        }
        return mapping.get(status, mapping["warning"])

    @classmethod
    def _decorate(cls, payload: dict, status: str) -> dict:
        payload["status"] = status
        payload["status_label"] = cls.STATUS_LABELS[status]
        payload.update(cls._theme(status))
        return payload

    @staticmethod
    def _transport_mode() -> dict:
        backend = getattr(settings, "EMAIL_BACKEND", "") or ""
        if backend.endswith("BrevoEmailBackend"):
            return {"slug": "brevo_api", "label": "Brevo API"}
        if backend == "django.core.mail.backends.smtp.EmailBackend":
            host = getattr(settings, "EMAIL_HOST", "") or ""
            label = "SMTP Brevo" if "brevo" in host.lower() else "SMTP"
            return {"slug": "smtp", "label": label}
        if backend.endswith("locmem.EmailBackend"):
            return {"slug": "locmem", "label": "Backend local mémoire"}
        if backend.endswith("console.EmailBackend"):
            return {"slug": "console", "label": "Backend console"}
        return {"slug": "custom", "label": backend or "Backend inconnu"}

    @classmethod
    def _build_check(cls, label: str, value: str, state: str = "ok", help_text: str = "") -> dict:
        state_map = {
            "ok": {
                "label": "OK",
                "pill_class": "bg-emerald-100 text-emerald-700",
                "text_class": "text-emerald-700",
            },
            "warning": {
                "label": "À vérifier",
                "pill_class": "bg-amber-100 text-amber-700",
                "text_class": "text-amber-700",
            },
            "critical": {
                "label": "Bloquant",
                "pill_class": "bg-red-100 text-red-700",
                "text_class": "text-red-700",
            },
        }
        tone = state_map[state]
        return {
            "label": label,
            "value": value,
            "help_text": help_text,
            "state": state,
            "state_label": tone["label"],
            "pill_class": tone["pill_class"],
            "text_class": tone["text_class"],
        }

    @classmethod
    def get_configuration_report(cls) -> dict:
        mode = cls._transport_mode()
        issues = []
        warnings = []
        recommendations = []

        backend_path = getattr(settings, "EMAIL_BACKEND", "") or "Non configuré"
        default_from_email = (getattr(settings, "DEFAULT_FROM_EMAIL", "") or "").strip()
        site_url = (getattr(settings, "SITE_URL", "") or "").strip()
        checks = [
            cls._build_check("Backend actif", mode["label"], "ok", backend_path),
            cls._build_check(
                "Expéditeur par défaut",
                default_from_email or "Non configuré",
                "ok" if default_from_email else "warning",
                "Adresse utilisée pour les notifications sortantes.",
            ),
            cls._build_check(
                "URL publique",
                site_url or "Non configurée",
                "ok" if site_url else "warning",
                "Utilisée pour les liens absolus hors contexte de requête.",
            ),
        ]

        if not default_from_email:
            warnings.append("DEFAULT_FROM_EMAIL est vide: certains envois peuvent partir avec une adresse par défaut non souhaitée.")
            recommendations.append("Renseigner DEFAULT_FROM_EMAIL avec une adresse validée par votre fournisseur email.")

        if not site_url:
            warnings.append("SITE_URL n'est pas configurée: certains liens d'invitation hors contexte web peuvent retomber sur localhost.")
            recommendations.append("Définir SITE_URL dans l'environnement pour fiabiliser les liens absolus envoyés par email.")

        if mode["slug"] == "brevo_api":
            api_key = (getattr(settings, "BREVO_API_KEY", "") or "").strip()
            checks.append(
                cls._build_check(
                    "Clé API Brevo",
                    _fingerprint(api_key) if api_key else "Absente",
                    "ok" if api_key else "critical",
                    "Empreinte affichée sans révéler la clé.",
                )
            )
            fallback_enabled = bool(getattr(settings, "BREVO_CONSOLE_FALLBACK", False))
            checks.append(
                cls._build_check(
                    "Fallback console",
                    "Activé" if fallback_enabled else "Désactivé",
                    "warning" if fallback_enabled else "ok",
                    "Un fallback peut masquer un échec réel d'envoi.",
                )
            )
            if not api_key:
                issues.append("BREVO_API_KEY est vide alors que le backend Brevo API est actif.")
                recommendations.append("Définir BREVO_API_KEY ou basculer explicitement sur le mode SMTP.")
            elif not api_key.startswith("xkeysib-"):
                warnings.append("La clé API Brevo semble au format inhabituel: le préfixe xkeysib- est attendu dans la majorité des cas.")
        elif mode["slug"] == "smtp":
            host = (getattr(settings, "EMAIL_HOST", "") or "").strip()
            port = getattr(settings, "EMAIL_PORT", "")
            login = (getattr(settings, "EMAIL_HOST_USER", "") or "").strip()
            password = (getattr(settings, "EMAIL_HOST_PASSWORD", "") or "").strip()
            checks.extend([
                cls._build_check("Serveur SMTP", host or "Non configuré", "ok" if host else "critical", f"Port {port}" if port else ""),
                cls._build_check("Identifiant SMTP", _mask_value(login), "ok" if login else "critical", "Valeur masquée pour éviter toute fuite."),
                cls._build_check("Mot de passe SMTP", _mask_value(password), "ok" if password else "critical", "Présence uniquement, valeur masquée."),
            ])
            if not host:
                issues.append("EMAIL_HOST est vide alors que le backend SMTP est actif.")
            if not login or not password:
                issues.append("Le backend SMTP est actif mais les identifiants EMAIL_HOST_USER / EMAIL_HOST_PASSWORD sont incomplets.")
                recommendations.append("Définir les identifiants SMTP réels ou basculer sur Brevo API.")
            if getattr(settings, "EMAIL_USE_TLS", False) and getattr(settings, "EMAIL_USE_SSL", False):
                warnings.append("EMAIL_USE_TLS et EMAIL_USE_SSL sont activés simultanément: cette combinaison est généralement invalide.")
        elif mode["slug"] in {"console", "locmem"}:
            warnings.append("Le backend email actif est local: il ne réalise pas d'envoi externe réel.")
            recommendations.append("Utiliser SMTP ou Brevo API pour tester la délivrabilité réelle depuis l'admin.")
        else:
            warnings.append("Le backend email actif est personnalisé ou non reconnu: vérifier manuellement sa stratégie d'envoi et ses journaux.")

        if issues:
            summary = issues[0]
            status = "critical"
        elif warnings:
            summary = warnings[0]
            status = "warning"
        else:
            summary = "La configuration email semble prête pour des envois réels."
            status = "healthy"

        return cls._decorate(
            {
                "backend_path": backend_path,
                "mode_label": mode["label"],
                "summary": summary,
                "issues": issues,
                "warnings": warnings,
                "recommendations": recommendations,
                "checks": checks,
                "issue_count": len(issues),
                "warning_count": len(warnings),
            },
            status,
        )

    @classmethod
    def probe_delivery_backend(cls) -> dict:
        mode = cls._transport_mode()

        if mode["slug"] == "brevo_api":
            api_key = (getattr(settings, "BREVO_API_KEY", "") or "").strip()
            if not api_key:
                return cls._decorate(
                    {
                        "title": "Probe Brevo impossible",
                        "details": "BREVO_API_KEY est absente, aucune connexion API ne peut être vérifiée.",
                    },
                    "critical",
                )
            try:
                import sib_api_v3_sdk
                from sib_api_v3_sdk.rest import ApiException

                configuration = sib_api_v3_sdk.Configuration()
                configuration.api_key["api-key"] = api_key
                api_client = sib_api_v3_sdk.ApiClient(configuration)
                account = sib_api_v3_sdk.AccountApi(api_client).get_account()
                details = f"Connexion Brevo validée pour {getattr(account, 'email', 'compte inconnu')}."
                return cls._decorate(
                    {
                        "title": "Probe Brevo réussi",
                        "details": details,
                    },
                    "healthy",
                )
            except ApiException as exc:
                details = f"Brevo a répondu {exc.status} {exc.reason}."
                status = "critical" if exc.status in {401, 403} else "warning"
                return cls._decorate(
                    {
                        "title": "Probe Brevo en échec",
                        "details": details,
                    },
                    status,
                )
            except Exception as exc:
                return cls._decorate(
                    {
                        "title": "Probe Brevo en erreur",
                        "details": str(exc),
                    },
                    "warning",
                )

        if mode["slug"] == "smtp":
            connection = None
            try:
                connection = get_connection(fail_silently=False)
                connection.open()
                return cls._decorate(
                    {
                        "title": "Probe SMTP réussi",
                        "details": "La connexion SMTP et l'authentification se sont ouvertes sans erreur.",
                    },
                    "healthy",
                )
            except SMTPAuthenticationError as exc:
                return cls._decorate(
                    {
                        "title": "Échec d'authentification SMTP",
                        "details": str(exc),
                    },
                    "critical",
                )
            except (SMTPException, OSError) as exc:
                return cls._decorate(
                    {
                        "title": "Connexion SMTP en échec",
                        "details": str(exc),
                    },
                    "warning",
                )
            finally:
                if connection is not None:
                    try:
                        connection.close()
                    except Exception:
                        pass

        if mode["slug"] in {"console", "locmem"}:
            return cls._decorate(
                {
                    "title": "Probe non applicable",
                    "details": "Le backend actuel est local et ne contacte aucun serveur externe.",
                },
                "warning",
            )

        return cls._decorate(
            {
                "title": "Probe non supporté",
                "details": f"Aucun probe automatique n'est prévu pour le backend {mode['label']}.",
            },
            "warning",
        )

    @classmethod
    def send_test_email(cls, recipient_email: str, triggered_by=None) -> dict:
        recipient_email = (recipient_email or "").strip()
        if not recipient_email:
            return cls._decorate(
                {
                    "title": "Adresse de test manquante",
                    "details": "Renseignez une adresse email destinataire avant d'envoyer le test.",
                },
                "critical",
            )

        try:
            validate_email(recipient_email)
        except ValidationError:
            return cls._decorate(
                {
                    "title": "Adresse email invalide",
                    "details": f"{recipient_email} n'est pas une adresse valide.",
                },
                "critical",
            )

        mode = cls._transport_mode()
        sender_name = getattr(settings, "DEFAULT_FROM_NAME", "Nettoyage Express")
        actor = "administrateur"
        if triggered_by is not None:
            actor = getattr(triggered_by, "get_full_name", lambda: "")() or getattr(triggered_by, "username", actor)

        timestamp = timezone.now().strftime("%d/%m/%Y %H:%M")
        subject = f"Test de supervision email NetExpress - {timestamp}"
        text_body = (
            "Ceci est un email de test emis depuis le centre de supervision NetExpress.\n\n"
            f"Backend actif : {mode['label']}\n"
            f"Declenche par : {actor}\n"
            f"Horodatage : {timestamp}\n"
        )
        html_body = (
            "<p>Ceci est un email de test emis depuis le centre de supervision NetExpress.</p>"
            f"<p><strong>Backend actif :</strong> {mode['label']}<br>"
            f"<strong>Déclenché par :</strong> {actor}<br>"
            f"<strong>Horodatage :</strong> {timestamp}</p>"
        )

        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@netexpress.fr"),
            to=[recipient_email],
        )
        message.attach_alternative(html_body, "text/html")

        try:
            message.send(fail_silently=False)
            if mode["slug"] in {"console", "locmem"}:
                status = "warning"
                details = "Le message a bien été remis au backend local, sans délivrabilité externe réelle."
            else:
                status = "healthy"
                details = f"Le test a été remis au backend {mode['label']} pour {recipient_email}."
            return cls._decorate(
                {
                    "title": "Email de test envoyé",
                    "details": details,
                    "sender_name": sender_name,
                },
                status,
            )
        except SMTPAuthenticationError as exc:
            return cls._decorate(
                {
                    "title": "Envoi test refusé par le serveur SMTP",
                    "details": str(exc),
                },
                "critical",
            )
        except Exception as exc:
            return cls._decorate(
                {
                    "title": "Envoi test en échec",
                    "details": str(exc),
                },
                "warning",
            )