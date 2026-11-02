import hmac
import os
import time
from collections import defaultdict, deque
from fastapi import HTTPException, Header, Request
from dotenv import load_dotenv

load_dotenv()

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

MAX_FAILED_ATTEMPTS = int(os.getenv("AUTH_MAX_FAILED_ATTEMPTS", "5"))
FAILED_WINDOW_SECONDS = 60

_failed_attempts: dict[str, deque] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    # Behind Render's proxy the rightmost X-Forwarded-For entry is the one it appended.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def reset_rate_limit() -> None:
    _failed_attempts.clear()


def check_rate_limit(request: Request) -> None:
    attempts = _failed_attempts[_client_ip(request)]
    cutoff = time.monotonic() - FAILED_WINDOW_SECONDS
    while attempts and attempts[0] < cutoff:
        attempts.popleft()
    if len(attempts) >= MAX_FAILED_ATTEMPTS:
        raise HTTPException(429, "Muitas tentativas. Tente novamente em instantes.")


def register_failure(request: Request) -> None:
    _failed_attempts[_client_ip(request)].append(time.monotonic())


def password_matches(candidate: str) -> bool:
    return bool(ADMIN_PASSWORD) and hmac.compare_digest(
        candidate.encode(), ADMIN_PASSWORD.encode()
    )


def require_admin(request: Request, x_admin_password: str = Header(default="")):
    if not ADMIN_PASSWORD:
        raise HTTPException(500, "ADMIN_PASSWORD não configurado no servidor.")
    check_rate_limit(request)
    if not x_admin_password or not password_matches(x_admin_password):
        register_failure(request)
        raise HTTPException(401, "Não autorizado.")


def is_admin(request: Request, x_admin_password: str = Header(default="")) -> bool:
    """Non-failing check used to decide whether sensitive fields are returned."""
    if not x_admin_password:
        return False
    check_rate_limit(request)
    if password_matches(x_admin_password):
        return True
    register_failure(request)
    return False
