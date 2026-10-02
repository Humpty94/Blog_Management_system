import pytest
from django.db import connection, models
from django.utils import timezone

from common.models import TimestampedModel


class ConcreteTimestampedModel(TimestampedModel):
    name = models.CharField(max_length=50)

    class Meta:
        app_label = "common"


@pytest.mark.django_db
def test_timestamped_model_timestamps():
    with connection.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS common_concretetimestampedmodel CASCADE;")

    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(ConcreteTimestampedModel)

    try:
        before_create = timezone.now()
        instance = ConcreteTimestampedModel.objects.create(name="test")
        after_create = timezone.now()

        assert before_create <= instance.created_at <= after_create
        assert before_create <= instance.updated_at <= after_create

        first_updated_at = instance.updated_at
        instance.name = "updated_test"
        instance.save()
        instance.refresh_from_db()

        assert instance.updated_at >= first_updated_at
    finally:
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(ConcreteTimestampedModel)
