import logging

from django.core.management.base import BaseCommand
from django.db import models
from django.db.models import Count

from blog.models import Post

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Reconciles denormalized Post.like_count with the actual count of Like records."

    def handle(self, *args, **options):
        # Annotate posts with true like count and filter those with discrepancies
        discrepant_posts = Post.objects.annotate(
            true_likes=Count("likes")
        ).exclude(like_count=models.F("true_likes"))

        reconciled_count = 0
        for post in discrepant_posts:
            old_count = post.like_count
            post.like_count = post.true_likes
            post.save(update_fields=["like_count"])
            reconciled_count += 1
            self.stdout.write(
                f"Reconciled post {post.id} ('{post.slug}'): {old_count} -> {post.like_count}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Like count reconciliation complete. Reconciled {reconciled_count} post(s)."
            )
        )
