import logging
import sys
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings




# -----------------------------
# Middleware for HTTP logs
# -----------------------------
class RequestResponseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        logger = logging.getLogger(settings.app_name)
        client_ip = request.client.host
        method = request.method
        url = request.url.path

        logger.info(f"Request: {method} {url} from {client_ip}")
        response = await call_next(request)
        status_code = response.status_code

        if status_code >= 400:
            logger.error(f"Response: {method} {url} from {client_ip} - {status_code}")
        else:
            logger.info(f"Response: {method} {url} from {client_ip} - {status_code}")

        return response


# -----------------------------
# Unified Logging Setup
# -----------------------------
def configure_global_logging(log_level: int = logging.INFO) -> None:
    """Configure root and library loggers with consistent formatting."""
    APP_NAME = settings.app_name
    log_format = f"[{APP_NAME}] %(asctime)s | %(levelname)-8s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_format, datefmt=date_format)

    # Root logger setup
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    # Console output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Unify known third-party loggers
    for lib_logger_name in [
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "fastapi",
        "starlette",
    ]:
        lib_logger = logging.getLogger(lib_logger_name)
        lib_logger.handlers.clear()
        lib_logger.addHandler(console_handler)
        lib_logger.setLevel(log_level)
        lib_logger.propagate = False

    # Silence SQLAlchemy SQL query logs
    for sql_logger_name in [
        "sqlalchemy",
        "sqlalchemy.engine",
        "sqlalchemy.engine.Engine",
        "sqlalchemy.pool",
        "sqlalchemy.dialects",
        "sqlalchemy.orm",
    ]:
        sql_logger = logging.getLogger(sql_logger_name)
        sql_logger.handlers.clear()
        sql_logger.setLevel(logging.WARNING)
        sql_logger.propagate = False

    root_logger.info(
        f"Logging configured for {APP_NAME} (level={logging.getLevelName(log_level)})"
    )

def get_logger(name: str | None = None) -> logging.Logger:
    """Return a named logger after global setup."""
    return logging.getLogger(name or settings.app_name)