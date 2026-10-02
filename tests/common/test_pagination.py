from django.core.paginator import Paginator
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from common.pagination import StandardPageNumberPagination


def test_standard_pagination_response_structure():
    factory = APIRequestFactory()
    wsgi_request = factory.get("/api/v1/posts/?page=1&page_size=2")
    request = Request(wsgi_request)

    items = ["item1", "item2", "item3", "item4", "item5"]
    paginator = Paginator(items, 2)
    page = paginator.page(1)

    pagination = StandardPageNumberPagination()
    pagination.request = request
    pagination.page = page

    response = pagination.get_paginated_response(["item1", "item2"])
    data = response.data

    assert "results" in data
    assert data["results"] == ["item1", "item2"]
    assert "pagination" in data
    meta = data["pagination"]
    assert meta["count"] == 5
    assert meta["page"] == 1
    assert meta["page_size"] == 2
    assert meta["total_pages"] == 3
    assert meta["next"] is not None
    assert meta["previous"] is None
