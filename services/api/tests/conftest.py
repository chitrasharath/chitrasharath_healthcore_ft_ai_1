from __future__ import annotations

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "30")
# Force stdout reset-link fallback; dev .env may set EMAIL_API_KEY for Resend sandbox.
os.environ["EMAIL_API_KEY"] = ""
os.environ.setdefault("DATABASE_URL", "")
os.environ["DATABASE_URL"] = ""
