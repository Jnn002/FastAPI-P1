from fastapi import Depends, Request
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.main import get_session
from src.db.models import User
from src.db.redis import token_in_blocklist
from src.errors import (
    AccessTokenRequired,
    AccountNotVerified,
    InsufficientPermission,
    InvalidCredentials,
    InvalidToken,
    RefreshTokenRequired,
)

from .service import UserService
from .utils import decode_token

user_service = UserService()


class TokenBearer(HTTPBearer):
    def __init__(self, auto_error=True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        """[summary]
        Args:
            request (Request): [description]

        Returns:
            HTTPAuthorizationCredentials | None: [description]

        Raises:
            HTTPException: [description

        We are obtaining the token from the request header and decoding it

        """
        # HTTPBearer busca el header 'Authorization: Bearer <token>'
        creds = await super().__call__(request)

        if creds is None:
            raise InvalidCredentials()

        token = creds.credentials
        token_data = decode_token(token)

        if not token_data:
            raise InvalidToken()

        if await token_in_blocklist(token_data['jti']):
            raise InvalidToken()

        self.verify_token_data(token_data)

        return token_data

    def verify_token_data(self, token_data):
        raise NotImplementedError('Subclasses must implement this method')


class AccessTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict) -> None:
        if token_data and token_data['refresh']:
            raise AccessTokenRequired()


class RefreshTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict) -> None:
        if token_data and not token_data['refresh']:
            raise RefreshTokenRequired()


async def get_current_userd(
    token_details: dict = Depends(AccessTokenBearer()),
    session: AsyncSession = Depends(get_session),
):
    user_email = token_details['user']['email']

    user = await user_service.get_user_by_email(user_email, session)

    return user


class RoleChecker:
    def __init__(self, allow_roles: list[str]):
        self.allow_roles = allow_roles

    def __call__(self, current_user: User = Depends(get_current_userd)):
        if not current_user.is_verified:
            raise AccountNotVerified()

        if current_user.role in self.allow_roles:
            return True

        raise InsufficientPermission()
