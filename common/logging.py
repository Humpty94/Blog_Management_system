import logging

from common.middleware import get_current_request_id


class RequestIDFilter(logging.Filter):
    """
    Logging filter that injects the current request_id into each log record.
    """

    def filter(self, record):
        request_id = get_current_request_id()
        record.request_id = request_id if request_id else "-"
        return True
