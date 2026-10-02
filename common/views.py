from django.db import connection
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """
    Operational health-check endpoint for deployment and liveness monitoring.
    Verifies database connectivity.
    """

    permission_classes = [AllowAny]
    throttle_classes = []

    @extend_schema(
        summary="Service Health Check",
        description="Verifies database connectivity and service availability.",
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name="HealthCheckSuccessResponse",
                    fields={
                        "status": serializers.CharField(default="ok"),
                        "database": serializers.CharField(default="connected"),
                    },
                ),
                description="Service is healthy",
            ),
            503: OpenApiResponse(
                response=inline_serializer(
                    name="HealthCheckFailureResponse",
                    fields={
                        "status": serializers.CharField(default="unhealthy"),
                        "database": serializers.CharField(default="disconnected"),
                    },
                ),
                description="Service or database is unhealthy",
            ),
        },
    )
    def get(self, request):
        db_healthy = True
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception:
            db_healthy = False

        http_status = status.HTTP_200_OK if db_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(
            {
                "status": "ok" if db_healthy else "unhealthy",
                "database": "connected" if db_healthy else "disconnected",
            },
            status=http_status,
        )
