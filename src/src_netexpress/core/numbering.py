"""Allocate and insert under one database transaction, including deleted documents."""
from django.db import transaction
from .models import DocumentSequence


def save_numbered_document(instance, prefix, save, args, kwargs):
    with transaction.atomic():
        if not instance.pk:
            series = f"{prefix}-{instance.issue_date.year}-"
            sequence, _ = DocumentSequence.objects.get_or_create(series=series)
            sequence = DocumentSequence.objects.select_for_update().get(pk=sequence.pk)
            # Numeric order also handles legacy/imported numbers beyond 999.
            numbers = type(instance).all_objects.filter(number__startswith=series).values_list("number", flat=True)
            maximum = max((int(n[len(series):]) for n in numbers if n[len(series):].isdigit()), default=0)
            sequence.value = max(sequence.value, maximum)
            if not instance.number:
                sequence.value += 1
                instance.number = f"{series}{sequence.value:03d}"
            elif instance.number.startswith(series) and instance.number[len(series):].isdigit():
                sequence.value = max(sequence.value, int(instance.number[len(series):]))
            sequence.save(update_fields=["value"])
        return save(*args, **kwargs)
