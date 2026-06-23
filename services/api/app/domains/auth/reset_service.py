from __future__ import annotations

import resend

from app.core.config import settings
from app.domains.auth import reset_tokens, token
from app.domains.auth.password import hash_password
from app.domains.auth.schemas import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from app.domains.auth.token import InvalidResetTokenError
from app.domains.users import store

FORGOT_PASSWORD_MESSAGE = "If that address is registered, you will receive a reset link shortly."
RESET_PASSWORD_SUCCESS_MESSAGE = "Password has been reset successfully."
INVALID_RESET_TOKEN_MESSAGE = "Invalid or expired reset token."


def send_reset_email(email: str, reset_token: str) -> None:
    reset_url = f"{settings.frontend_url}/reset-password?token={reset_token}"
    if not settings.email_api_key:
        print(f"Password reset link for {email}: {reset_url}")
        return

    resend.api_key = settings.email_api_key
    resend.Emails.send(
        {
            "from": "onboarding@resend.dev",
            "to": [email],
            "subject": "HealthCore — Password Reset",
            "text": f"Reset your password using this link:\n\n{reset_url}\n\nThis link expires in 30 minutes.",
        }
    )


def forgot_password(body: ForgotPasswordRequest) -> ForgotPasswordResponse:
    user = store.get_by_email(body.email)
    if user is not None:
        reset_token = token.create_reset_token(user["id"])
        send_reset_email(body.email, reset_token)
    return ForgotPasswordResponse(message=FORGOT_PASSWORD_MESSAGE)


def reset_password(body: ResetPasswordRequest) -> ResetPasswordResponse:
    if reset_tokens.is_token_used(body.token):
        raise InvalidResetTokenError(INVALID_RESET_TOKEN_MESSAGE)

    user_id = token.decode_reset_token(body.token)
    user = store.get_by_id(user_id)
    if user is None:
        raise InvalidResetTokenError(INVALID_RESET_TOKEN_MESSAGE)

    store.update_user(user_id, {"hashed_password": hash_password(body.new_password)})
    reset_tokens.mark_token_used(body.token)
    return ResetPasswordResponse(message=RESET_PASSWORD_SUCCESS_MESSAGE)
