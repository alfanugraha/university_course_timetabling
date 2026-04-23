"""
backend/app/core/permissions.py
RBAC helpers: role constants and require_role() FastAPI dependency.
"""

from typing import List

from fastapi import Depends, HTTPException, status

from app.core.auth import get_current_user

# ---------------------------------------------------------------------------
# Role constants
# ---------------------------------------------------------------------------

EDITOR_ROLES_JURUSAN: List[str] = [
    "admin",
    "sekretaris_jurusan",
    "tendik_jurusan",
]

EDITOR_ROLES_PRODI: List[str] = [
    "admin",
    "sekretaris_jurusan",
    "tendik_jurusan",
    "koordinator_prodi",
    "tendik_prodi",
]

VIEWER_ROLES: List[str] = [
    "ketua_jurusan",
]

# All roles that exist in the system (for reference / validation)
ALL_ROLES: List[str] = [
    "admin",
    "ketua_jurusan",
    "sekretaris_jurusan",
    "koordinator_prodi",
    "dosen",
    "tendik_prodi",
    "tendik_jurusan",
]


# ---------------------------------------------------------------------------
# Dependency factory
# ---------------------------------------------------------------------------

def require_role(roles: List[str]):
    """FastAPI dependency factory that enforces role-based access control.

    Usage in a router::

        @router.post("/some-endpoint")
        def my_endpoint(current_user = Depends(require_role(EDITOR_ROLES_JURUSAN))):
            ...

    Args:
        roles: List of role strings that are allowed to access the endpoint.

    Returns:
        A FastAPI dependency callable that returns the current active user if
        their role is in *roles*, or raises HTTP 403 otherwise.
    """

    def _check(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Akses ditolak. Role '{current_user.role}' tidak memiliki "
                    "izin untuk mengakses endpoint ini."
                ),
            )
        return current_user

    return _check
