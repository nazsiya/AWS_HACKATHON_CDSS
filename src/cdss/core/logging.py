"""
Structured logging for CDSS (CloudWatch-friendly, DISHA audit support).
"""

import logging
import os
from typing import Any, Optional

JSON_LOGS = os.environ.get("LOG_FORMAT", "text").lower() == "json"


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """Return logger with optional JSON formatter for Lambda/CloudWatch."""
    log = logging.getLogger(name)
    if level is not None:
        log.setLevel(level)
    if not log.handlers:
        handler = logging.StreamHandler()
        if JSON_LOGS:
            handler.setFormatter(JsonFormatter())
        else:
            handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
            )
        log.addHandler(handler)
    return log


class JsonFormatter(logging.Formatter):
    """Format log records as JSON for CloudWatch Logs Insights."""

    def format(self, record: logging.LogRecord) -> str:
        import json

        d: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            d.update(record.extra)
        return json.dumps(d)
