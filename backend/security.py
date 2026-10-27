"""Fail-closed identity & RBAC for Linko.

local: CLI-issued HS256 tokens for a TRUSTED development/demo team ONLY.
oidc: Validate externally issued RS256 JWTs against a configured issuer/JWKS.
test: No auth only when both ENVIRONMENT=test and ALLOW_TEST_AUTH_BYPASS=true.

There is deliberately no public endpoint that issues user tokens, nor a shared
write secret exposed to the browser. In production, use oidc with an IdP.
"""
from __future__ import annotations

import contextvars
import os
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlparse

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse

current_actor: contextvars.ContextVar[str] = contextvars.ContextVar('linko_actor', default='ANONYMOUS')

@dataclass(frozen=True)
class Principal:
    subject: str
    role: str

class AuthError(Exception):
    def __init__(self, code: str, message: str, status: int = 401):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def auth_mode() -> str:
    mode = os.getenv('AUTH_MODE', 'local').strip().lower()
    if mode not in {'local', 'oidc', 'test'}:
        raise AuthError('AUTH_CONFIG_ERROR', 'AUTH_MODE chỉ được local/oidc/test.', 503)
    if mode == 'test' and not (os.getenv('ENVIRONMENT') == 'test' and
                               os.getenv('ALLOW_TEST_AUTH_BYPASS') == 'true'):
        raise AuthError('AUTH_CONFIG_ERROR', 'Không được tắt xác thực ngoài môi trường test.', 503)
    if mode == 'local' and len(os.getenv('JWT_SECRET', '')) < 32:
        raise AuthError('AUTH_CONFIG_ERROR', 'Cần JWT_SECRET >= 32 ký tự; không cấp quyền khi chưa cấu hình.', 503)
    if mode == 'oidc':
        iss, aud, jwks = (os.getenv('OIDC_ISSUER', ''), os.getenv('OIDC_AUDIENCE', ''), os.getenv('OIDC_JWKS_URL', ''))
        if not (iss and aud and jwks and urlparse(iss).scheme == 'https' and urlparse(jwks).scheme == 'https'):
            raise AuthError('AUTH_CONFIG_ERROR', 'OIDC issuer/audience/JWKS phải được cấu hình HTTPS.', 503)
    return mode

@lru_cache(maxsize=4)
def _jwks_client(url: str):
    return jwt.PyJWKClient(url, cache_jwk_set=True, lifespan=300, timeout=3)


def validate_token(value: str) -> Principal:
    mode = auth_mode()
    if mode == 'test':
        return Principal('offline-test', 'admin')
    if not value.startswith('Bearer ') or len(value) < 12:
        raise AuthError('AUTH_REQUIRED', 'Cần Bearer access token.')
    token = value[7:].strip()
    try:
        if mode == 'local':
            payload = jwt.decode(token, os.environ['JWT_SECRET'], algorithms=['HS256'],
                                 audience='linko-api', issuer='linko-local', options={'require':['exp','iat','sub','iss','aud']})
        else:
            signing = _jwks_client(os.environ['OIDC_JWKS_URL']).get_signing_key_from_jwt(token)
            payload = jwt.decode(token, signing.key, algorithms=['RS256'],
                                 audience=os.environ['OIDC_AUDIENCE'], issuer=os.environ['OIDC_ISSUER'],
                                 options={'require':['exp','iat','sub','iss','aud']})
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise AuthError('INVALID_TOKEN', 'Access token không hợp lệ hoặc hết hạn.') from exc
    subject = payload.get('sub')
    raw_roles = payload.get('roles', [])
    if not isinstance(subject, str) or not subject.strip() or not isinstance(raw_roles, list):
        raise AuthError('INVALID_CLAIMS', 'Token thiếu chủ thể hoặc vai trò.')
    roles = set(raw_roles) & {'employee', 'hr', 'admin'}
    if not roles:
        raise AuthError('ROLE_REQUIRED', 'Token không có vai trò Linko.', 403)
    role = next(r for r in ('admin', 'hr', 'employee') if r in roles)
    return Principal(subject[:64], role)


READ_POST_PATHS = {'/api/graph/shortest-path', '/api/paths/shortest'}

def required_role(request: Request) -> str:
    path, method = request.url.path, request.method
    if ('audit' in path or path.endswith('/delete-impact') or path in {'/api/health','/api/ready'}):
        return 'hr'
    if method == 'DELETE':
        return 'admin'
    if method in {'POST', 'PATCH', 'PUT'} and path not in READ_POST_PATHS:
        return 'hr'
    return 'employee'


def allowed_role(actual: str, required: str) -> bool:
    rank = {'employee': 1, 'hr': 2, 'admin': 3}
    return rank[actual] >= rank[required]


def auth_failure(error: AuthError, request_id: str) -> JSONResponse:
    response = JSONResponse(status_code=error.status, content={'detail': {'code':error.code, 'message':error.message}})
    response.headers['X-Request-ID'] = request_id
    response.headers['Cache-Control'] = 'no-store'
    if error.status == 401:
        response.headers['WWW-Authenticate'] = 'Bearer'
    return response
