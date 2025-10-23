import contextvars
import json
import logging
import os
import sys
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler

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
            "timestamp": datetime.fromtimestamp(record.created, UTC)
            .isoformat()
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": display_logger,
            "message": record.getMessage(),
        }

        context = {}
        for key, value in getattr(record, "__dict__", {}).items():
            if key in DEFAULT_LOG_RECORD_ATTRS or key in payload or key.startswith("_"):
                continue
            if key == "color_message":
                continue
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
        "DEBUG": "\x1b[36m",
        "INFO": "\x1b[32m",
        "WARNING": "\x1b[33m",
        "ERROR": "\x1b[31m",
        "CRITICAL": "\x1b[35m",
    }

    RESET = "\x1b[0m"

    def format(self, record: logging.LogRecord) -> str:
        ts = (
            datetime.fromtimestamp(record.created, UTC)
            .isoformat()
            .replace("+00:00", "Z")
        )
        level = record.levelname
        color = self.LEVEL_COLORS.get(level, "")
        display_logger = "uvicorn" if record.name == "uvicorn.error" else record.name
        prefix = f"[{ts}] {color}{level}{self.RESET} {display_logger}: "

        message = record.getMessage()

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

REQUEST_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)

class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        rid = REQUEST_ID.get()
        if rid:
            # Attach request_id to record so formatters include it
            record.request_id = rid
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
    "aws_access_key_id",
    "aws_secret_access_key",
    "aws_session_token",
    "private_key",
    "client_secret",
    "database_url",
    "db_url",
    "connection_string",
    "redis_url",
    "smtp_password",
    "webhook_secret"
}

SENSITIVE_PATTERNS = {
    "bearer ",
    "basic ",
    "key=",
    "token=",
    "secret=",
    "password=",
    "aws_access_key_id=",
    "aws_secret_access_key=",
    "arn:aws:iam::",
    "-----BEGIN"
}

def _redact(value):
    """
    Recursively redact sensitive information from log data.

    This function identifies and redacts:
    - Dictionary keys that match sensitive patterns
    - String values containing sensitive patterns
    - AWS credentials and tokens
    - Database connection strings
    - API keys and secrets
    """
    if isinstance(value, dict):
        return {
            k: ("[REDACTED]" if k.lower() in SENSITIVE_KEYS else _redact(v))
            for k, v in value.items()
        }
    elif isinstance(value, list):
        return [_redact(item) for item in value]
    elif isinstance(value, str):
        # Check for sensitive patterns in string values
        value_lower = value.lower()

        # Redact if string contains sensitive patterns
        if any(pattern in value_lower for pattern in SENSITIVE_PATTERNS):
            return "[REDACTED]"

        # Redact long strings that might be tokens/keys (but preserve short ones)
        if len(value) > 20 and any(key in value_lower for key in SENSITIVE_KEYS):
            return "[REDACTED]"

        # Redact AWS ARNs and other identifiable patterns
        if value.startswith(("arn:aws:", "AKIA", "ASIA")) or "-----BEGIN" in value:
            return "[REDACTED]"

        return value
    return value

class SecretsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Temporarily disable redaction for debugging
        if os.getenv("DISABLE_LOG_REDACTION", "false").lower() == "true":
            return True
            
        for key in list(getattr(record, "__dict__", {}).keys()):
            if key.lower() in SENSITIVE_KEYS:
                setattr(record, key, "[REDACTED]")
            else:
                val = getattr(record, key)
                try:
                    redacted = _redact(val)
                    setattr(record, key, redacted)
                except Exception:
                    setattr(record, key, str(val))
        return True

def setup_logging():
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    for h in list(root.handlers):
        root.removeHandler(h)

    log_format = os.getenv("LOG_FORMAT", "json").lower()
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    if log_format == "console":
        handler.setFormatter(ConsoleFormatter())
    else:
        handler.setFormatter(JSONFormatter())
    handler.addFilter(RequestIdFilter())
    handler.addFilter(SecretsFilter())
    root.addHandler(handler)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.setLevel(level)
        for h in list(lg.handlers):
            lg.removeHandler(h)
        lg.propagate = True

    # Add a file handler if LOG_FILE is set
    log_file = os.getenv("LOG_FILE")
    if log_file:
        file_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024 * 5, backupCount=5) # 5 MB per file, 5 backups
        file_handler.setLevel(level)
        if log_format == "console":
            file_handler.setFormatter(ConsoleFormatter())
        else:
            file_handler.setFormatter(JSONFormatter())
        file_handler.addFilter(RequestIdFilter())
        file_handler.addFilter(SecretsFilter())
        root.addHandler(file_handler)

    logging.getLogger("app").info("Logging initialized", extra={"level": level_name})
