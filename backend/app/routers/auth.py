import hmac
from fastapi import APIRouter
from ..dependencies import ADMIN_PASSWORD
from ..schemas import PasswordVerify, AuthResponse

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/verify",
    response_model=AuthResponse,
    summary="Verificar senha de administrador",
    description="Verifica se a senha fornecida é a senha de administrador. Retorna `valid: true` em caso de sucesso.",
)
def verify_password(data: PasswordVerify):
    if not ADMIN_PASSWORD:
        return AuthResponse(valid=False)
    valid = hmac.compare_digest(data.password.encode(), ADMIN_PASSWORD.encode())
    return AuthResponse(valid=valid)
