import hmac
import os
from fastapi import HTTPException, Header
from dotenv import load_dotenv

load_dotenv()

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")


def require_admin(x_admin_password: str = Header(default="")):
    if not ADMIN_PASSWORD:
        raise HTTPException(500, "ADMIN_PASSWORD não configurado no servidor.")
    if not x_admin_password or not hmac.compare_digest(
        x_admin_password.encode(), ADMIN_PASSWORD.encode()
    ):
        raise HTTPException(401, "Não autorizado.")
