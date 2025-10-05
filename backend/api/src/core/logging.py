import logging
import os
import sys
import json
from datetime import datetime, UTC
import contextvars

# Standard LogRecord attributes to exclude from structured extras
DEFAULT_LOG_RECORD_ATTRS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "taskName",
}


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        display_logger = "uvicorn" if record.name == "uvicorn.error" else record.name
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": display_logger,
            "message": record.getMessage(),
        }

        # Collect only user-provided extras into a nested context
        context = {}
        for key, value in getattr(record, "__dict__", {}).items():
            if key in DEFAULT_LOG_RECORD_ATTRS or key in payload or key.startswith("_"):
                continue
            if key == "color_message":
                # Uvicorn-specific colorized message, skip for clean JSON
                continue
            # Avoid serializing non-JSON-safe objects
            try:
                json.dumps(value)
                context[key] = value
            except Exception:
                context[key] = str(value)

        if context:
            payload["context"] = context

        return json.dumps(payload, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    LEVEL_COLORS = {
        "DEBUG": "\x1b[36m",  # cyan
        "INFO": "\x1b[32m",   # green
        "WARNING": "\x1b[33m",# yellow
        "ERROR": "\x1b[31m",  # red
        "CRITICAL": "\x1b[35m" # magenta
    }

    RESET = "\x1b[0m"

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, UTC).isoformat().replace("+00:00", "Z")
        level = record.levelname
        color = self.LEVEL_COLORS.get(level, "")
        display_logger = "uvicorn" if record.name == "uvicorn.error" else record.name
        prefix = f"[{ts}] {color}{level}{self.RESET} {display_logger}: "

        message = record.getMessage()

        # Append user extras as key=value tokens
        extras = []
        for key, value in getattr(record, "__dict__", {}).items():
            if key in DEFAULT_LOG_RECORD_ATTRS or key.startswith("_"):
                continue
            if key == "color_message":
                continue
            try:
                json.dumps(value)
                val = value
            except Exception:
                val = str(value)
            extras.append(f"{key}={val}")

        suffix = f" {' '.join(extras)}" if extras else ""
        return f"{prefix}{message}{suffix}"


REQUEST_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        rid = REQUEST_ID.get()
        if rid:
            # Attach request_id to record so formatters include it
            setattr(record, "request_id", rid)
        return True


SENSITIVE_KEYS = {
    "authorization",
    "password",
    "secret",
    "token",
    "api_key",
    "jwt",
    "access_token",
    "refresh_token",
}


def _redact(value):
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if k.lower() in SENSITIVE_KEYS else _redact(v)) for k, v in value.items()}
    if isinstance(value, str) and len(value) > 12:
        # Heuristic: long strings may be tokens/keys
        return "[REDACTED]" if any(key in value.lower() for key in ("secret", "token", "bearer")) else value
    return value


class SecretsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for key in list(getattr(record, "__dict__", {}).keys()):
            if key.lower() in SENSITIVE_KEYS:
                setattr(record, key, "[REDACTED]")
            else:
                val = getattr(record, key)
                try:
                    redacted = _redact(val)
                    setattr(record, key, redacted)
                except Exception:
                    # If redaction fails, fallback to string
                    setattr(record, key, str(val))
        return True


def setup_logging():
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Clear default handlers to avoid duplicate logs
    for h in list(root.handlers):
        root.removeHandler(h)

    # Choose formatter based on LOG_FORMAT env
    log_format = os.getenv("LOG_FORMAT", "json").lower()
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    if log_format == "console":
        handler.setFormatter(ConsoleFormatter())
    else:
        handler.setFormatter(JSONFormatter())
    # Add filters for request_id propagation and secret redaction
    handler.addFilter(RequestIdFilter())
    handler.addFilter(SecretsFilter())
    root.addHandler(handler)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.setLevel(level)
        for h in list(lg.handlers):
            lg.removeHandler(h)
        # Let messages bubble to root to avoid duplicates
        lg.propagate = True

    logging.getLogger("app").info("Logging initialized", extra={"level": level_name})