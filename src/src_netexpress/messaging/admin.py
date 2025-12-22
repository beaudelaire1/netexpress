"""Configuration de l'interface d'administration pour l'application ``messaging``.

Cette configuration permet de visualiser, filtrer et rechercher les
messages envoyés.  Elle offre également une action pour renvoyer un
message en cas d'échec.
"""

from django.contrib import admin

from .models import EmailMessage, Message, MessageThread


@admin.register(MessageThread)
class MessageThreadAdmin(admin.ModelAdmin):
    list_display = ("subject", "get_participants", "last_message_at", "created_at")
    list_filter = ("created_at", "last_message_at")
    search_fields = ("subject",)
    readonly_fields = ("created_at", "last_message_at")
    filter_horizontal = ("participants",)
    
    def get_participants(self, obj):
        return ", ".join([user.username for user in obj.participants.all()])
    get_participants.short_description = "Participants"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "sender", "recipient", "created_at", "is_read")
    list_filter = ("created_at", "read_at")
    search_fields = ("subject", "content", "sender__username", "recipient__username")
    readonly_fields = ("created_at", "read_at")
    raw_id_fields = ("sender", "recipient", "thread")
    
    def is_read(self, obj):
        return obj.is_read
    is_read.boolean = True
    is_read.short_description = "Lu"


@admin.register(EmailMessage)
class EmailMessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "recipient", "status", "created_at", "sent_at")
    list_filter = ("status", "created_at")
    search_fields = ("recipient", "subject", "body")
    readonly_fields = ("created_at", "sent_at", "status", "error_message")
    actions = ["resend_emails"]

    def resend_emails(self, request, queryset):
        """Action pour renvoyer les e‑mails sélectionnés."""
        count = 0
        for msg in queryset:
            # Réessayer uniquement les messages en échec
            if msg.status in (EmailMessage.STATUS_DRAFT, EmailMessage.STATUS_FAILED):
                msg.send()
                count += 1
        self.message_user(request, f"{count} message(s) renvoyé(s)")
    resend_emails.short_description = "Renvoyer les e‑mails sélectionnés"