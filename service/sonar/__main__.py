import logging
import os

import uvicorn

from .main import JsonFormatter


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(
    level=os.environ.get("SONAR_LOG_LEVEL", "INFO").upper(), handlers=[handler]
)

port = int(os.environ.get("SONAR_PORT", "8000"))
if not 1 <= port <= 65535:
    raise ValueError("SONAR_PORT must be between 1 and 65535")

uvicorn.run(
    "sonar.main:app",
    host=os.environ.get("SONAR_HOST", "127.0.0.1"),
    port=port,
    log_config=None,
)
