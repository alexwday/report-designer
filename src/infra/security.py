"""Optional RBC SSL certificate setup."""

from __future__ import annotations

import importlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def configure_rbc_security_certs() -> Optional[str]:
    """Enable RBC SSL certificates when the optional rbc_security package exists."""
    try:
        rbc_security = importlib.import_module("rbc_security")
    except ImportError:
        logger.debug("rbc_security is not installed; skipping SSL certificate setup")
        return None

    logger.info("Enabling RBC SSL certificates via rbc_security")
    rbc_security.enable_certs()
    return "rbc_security"
