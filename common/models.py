from django.db import models
from django.utils import timezone


class TimestampedModel(models.Model):
    """
    Abstract base model providing self-updating created_at and updated_at fields
    stored as timestamptz (UTC).
    """

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
