"""Lightweight security helpers for InkTrack.

This module provides an opt-in admin authentication dependency. It is
intentionally minimal so that the app keeps working out-of-the-box in a
private network deployment, and only enforces authentication when an
operator explicitly opts in by setting ``ADMIN_API_TOKEN``.

Behavior:

* If ``ADMIN_API_TOKEN`` is unset or empty -> ``require_admin`` is a no-op
  (returns ``None``). Existing deployments keep working unchanged.
* If ``ADMIN_API_TOKEN`` is set -> requests to protected endpoints MUST
  include the header ``X-Admin-Token`` matching the token (compared with
  :func:`hmac.compare_digest` to avoid timing attacks). Otherwise the
  request is rejected with HTTP 401.

The header name and bypass behavior are documented so operators understand
the trade-off: convenient for LAN-only use, strict once a token is set.
"""

from __future__ import annotations

import hmac
import logging
import os
from typing import Optional

from fastapi import Header, HTTPException, status

log = logging.getLogger(__name__)

# These are environment variable / header NAMES, not secrets. Bandit's
# heuristic B105 flags the literal string, so we annotate it explicitly.
_ADMIN_TOKEN_ENV = "ADMIN_API_TOKEN"  # nosec B105
_ADMIN_HEADER = "X-Admin-Token"


def _current_token() -> str:
    """Return the current configured admin token (may be empty)."""
    return (os.environ.get(_ADMIN_TOKEN_ENV) or "").strip()


def admin_auth_enabled() -> bool:
    """Return True when admin authentication is enforced."""
    return bool(_current_token())


async def require_admin(
    x_admin_token: Optional[str] = Header(default=None, alias=_ADMIN_HEADER),
) -> None:
    """FastAPI dependency that enforces admin auth when configured.

    If ``ADMIN_API_TOKEN`` is not set, this is a no-op (backwards compatible
    with the current LAN-only deployment). When the env var is set, the
    request must carry a matching ``X-Admin-Token`` header.
    """
    expected = _current_token()
    if not expected:
        # Auth not configured: opt-in security, allow request.
        return None

    if not x_admin_token or not hmac.compare_digest(x_admin_token, expected):
        log.warning("Rejected request to admin endpoint: invalid or missing token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
            headers={"WWW-Authenticate": _ADMIN_HEADER},
        )
    return None
