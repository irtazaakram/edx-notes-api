import logging

from django.conf import settings
from jwt import DecodeError, ExpiredSignatureError, InvalidAudienceError
from rest_framework.permissions import BasePermission
from rest_framework_jwt.utils import jwt_decode_handler

logger = logging.getLogger(__name__)


class TokenWrongIssuer(Exception):
    """Raised when the token has an incorrect issuer."""

    pass


class HasAccessToken(BasePermission):
    """
    Permission check for requests with a valid ID Token.

    Expected Token:
    Header {
        "alg": "HS256",
        "typ": "JWT"
    }
    Claims {
        "sub": "<USER ANONYMOUS ID>",
        "exp": <EXPIRATION TIMESTAMP>,
        "iat": <ISSUED TIMESTAMP>,
        "aud": "<CLIENT ID>"
    }
    Should be signed with CLIENT_SECRET.
    """

    def has_permission(self, request, view):
        if getattr(settings, "DISABLE_TOKEN_CHECK", False):
            return True

        token = request.headers.get("x-annotator-auth-token")
        if not token:
            logger.debug("No token found in headers")
            return False

        try:
            # Use centralized decode handler for JWT
            data = jwt_decode_handler(token)
            self._validate_token_issuer_and_audience(data)

            auth_user = data.get("sub")
            if self._user_in_request_matches(auth_user, request):
                return True

            logger.info("No matching user found in request fields")
        except ExpiredSignatureError:
            logger.debug("Token has expired: %s", token)
        except DecodeError:
            logger.debug("Token decoding failed: %s", token)
        except InvalidAudienceError:
            logger.debug("Token has an invalid audience: %s", token)
        except TokenWrongIssuer as e:
            logger.debug(str(e))
        return False

    def _validate_token_issuer_and_audience(self, data):
        """Validate the issuer and audience in the token."""
        if data.get("aud") != settings.CLIENT_ID:
            raise TokenWrongIssuer("Token has an invalid issuer or audience")

    def _user_in_request_matches(self, auth_user, request):
        """
        Check if the authenticated user from the token matches the user in request fields.
        """
        user_found = False
        for field in ("GET", "POST", "data"):
            if "user" in getattr(request, field, {}):
                req_user = getattr(request, field)["user"]
                if req_user == auth_user:
                    user_found = True
                else:
                    logger.debug(
                        "Authenticated token user %s did not match request %s user %s",
                        auth_user,
                        field,
                        req_user,
                    )
                    return False
        return user_found
