from fastapi import APIRouter, Request
from ..dependencies import check_rate_limit, password_matches, register_failure
from ..schemas import PasswordVerify, AuthResponse

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/verify",
    response_model=AuthResponse,
    summary="Verificar senha de administrador",
    description="Verifica se a senha fornecida é a senha de administrador. Retorna `valid: true` em caso de sucesso.",
)
def verify_password(data: PasswordVerify, request: Request):
    check_rate_limit(request)
    valid = password_matches(data.password)
    if not valid:
        register_failure(request)
    return AuthResponse(valid=valid)
