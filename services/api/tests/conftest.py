from __future__ import annotations

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "30")
