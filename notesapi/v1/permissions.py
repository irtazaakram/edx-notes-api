import logging

import jwt
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger(__name__)


class TokenWrongIssuer(AuthenticationFailed):
    pass


class HasAccessToken(BasePermission):
    """
    Allows access to requests with a valid JWT access token.

    The token should be structured as:
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
    It should be signed with CLIENT_SECRET.
    """

    def has_permission(self, request, view):
        if getattr(settings, "DISABLE_TOKEN_CHECK", False):
            return True

        token = request.headers.get("x-annotator-auth-token")
        if not token:
            logger.warning("Access token is missing in headers.")
            return False

        try:
            access_token = AccessToken(token)
            self._validate_token_payload(access_token, request)

            return True
        except (AuthenticationFailed, jwt.ExpiredSignatureError) as e:
            logger.warning("Access token validation failed: %s", str(e))
        except Exception as e:
            logger.error("Unexpected error during token validation: %s", str(e))

        return False

    def _validate_token_payload(self, token, request):
        """
        Validates token claims and ensures the token's subject matches the user.
        """
        # Validate the audience
        if token["aud"] != settings.CLIENT_ID:
            logger.error("Token has incorrect audience: %s", token["aud"])
            raise TokenWrongIssuer("Token audience does not match expected client ID")

        # Match token subject with request user
        auth_user = token["sub"]
        if not self._is_request_user_matched(auth_user, request):
            logger.warning("Token user %s did not match any request user", auth_user)
            raise AuthenticationFailed("User in token does not match request user")

    def _is_request_user_matched(self, auth_user, request):
        """
        Check if token subject matches 'user' in GET, POST, or data attributes of the request.
        """
        user_found = False
        for request_field in ("GET", "POST", "data"):
            if "user" in getattr(request, request_field, {}):
                req_user = getattr(request, request_field)["user"]
                if req_user == auth_user:
                    user_found = True
                else:
                    logger.debug(
                        "Token user %s did not match %s user %s", auth_user, request_field, req_user
                    )
                    return False
        if not user_found:
            logger.info("No matching user found in GET, POST, or DATA request fields")
        return user_found
