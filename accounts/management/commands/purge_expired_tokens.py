import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import RefreshTokenRecord

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Purge expired and revoked refresh token records beyond the retention threshold."

    def add_arguments(self, parser):
        parser.add_argument(
            "--retention-days",
            type=int,
            default=7,
            help="Number of retention days past expires_at before purging (default: 7).",
        )

    def handle(self, *args, **options):
        retention_days = options["retention_days"]
        cutoff = timezone.now() - timedelta(days=retention_days)

        deleted_count, _ = RefreshTokenRecord.objects.filter(
            expires_at__lt=cutoff,
            revoked_at__isnull=False,
        ).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully purged {deleted_count} expired refresh token records "
                f"older than {retention_days} days."
            )
        )
