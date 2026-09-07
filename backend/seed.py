"""
Database seeder — run after migrations.
Creates permissions, roles, the admin user and a sample OCR API client, idempotently.
"""

import asyncio
import os
import sys

# Allow running as `uv run python seed.py` from /app/backend
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.api_client import ApiClient
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User, UserSettings
from app.repositories.permission import get_or_create_permission
from app.services.password import hash_password

PERMISSIONS = [
    # users
    "users.view", "users.create", "users.edit", "users.delete",
    # roles
    "roles.view", "roles.create", "roles.edit", "roles.delete", "roles.manage",
    # permissions
    "permissions.view", "permissions.create", "permissions.delete",
    # dashboard
    "dashboard.view",
    # api clients
    "api_clients.manage", "api_clients.view", "api_clients.create", "api_clients.revoke",
    # ocr
    "ocr.use", "ocr.jobs.view",
    # documents (OCR processing registry)
    "documents.view", "documents.delete",
]

ROLES = {
    "admin": PERMISSIONS,
    "editor": [
        "users.view",
        "roles.view",
        "permissions.view",
        "dashboard.view",
        "ocr.use", "ocr.jobs.view",
        "documents.view",
    ],
    "viewer": [
        "users.view",
        "roles.view",
        "permissions.view",
        "dashboard.view",
        "ocr.jobs.view",
        "documents.view",
    ],
}


async def seed(db: AsyncSession) -> None:
    # ── Permissions & roles ───────────────────────────────────────────────────
    print("Seeding permissions...")
    perm_objects: dict[str, Permission] = {}
    for name in PERMISSIONS:
        perm = await get_or_create_permission(db, name)
        perm_objects[name] = perm
    await db.flush()
    print(f"  {len(PERMISSIONS)} permissions ready.")

    print("Seeding roles...")
    for role_name, perm_names in ROLES.items():
        result = await db.execute(
            select(Role).where(Role.name == role_name).options(selectinload(Role.permissions))
        )
        role = result.scalar_one_or_none()
        if not role:
            role = Role(name=role_name, guard_name="api")
            role.permissions = [perm_objects[p] for p in perm_names]
            db.add(role)
        else:
            role.permissions = [perm_objects[p] for p in perm_names]
        await db.flush()
        print(f"  Role '{role_name}' ready with {len(perm_names)} permissions.")

    # ── Admin user ────────────────────────────────────────────────────────────
    print("Seeding admin user...")
    result = await db.execute(
        select(User).where(User.email == settings.admin_email).options(selectinload(User.roles))
    )
    admin = result.scalar_one_or_none()

    if not admin:
        result = await db.execute(select(Role).where(Role.name == "admin"))
        admin_role = result.scalar_one_or_none()

        admin = User(
            name=settings.admin_name,
            email=settings.admin_email,
            password_hash=hash_password(settings.admin_password),
            status="active",
        )
        if admin_role:
            admin.roles = [admin_role]
        db.add(admin)
        await db.flush()

        admin_settings = UserSettings(user_id=admin.id)
        db.add(admin_settings)
        await db.flush()
        print(f"  Admin user created: {settings.admin_email}")
    else:
        print(f"  Admin user already exists: {settings.admin_email}")

    # ── API client de ejemplo para OCR ───────────────────────────────────────
    print("Seeding OCR API client...")
    result = await db.execute(select(ApiClient).where(ApiClient.name == "ocr-demo"))
    if result.scalar_one_or_none() is None:
        client_id, secret, secret_hash = ApiClient.generate_credentials()
        db.add(
            ApiClient(
                name="ocr-demo",
                client_id=client_id,
                secret_hash=secret_hash,
                scopes=["ocr:write", "ocr:read"],
            )
        )
        await db.flush()
        print("  OCR API client creado — guarda estas credenciales:")
        print(f"    client_id     = {client_id}")
        print(f"    client_secret = {secret}")
    else:
        print("  OCR API client 'ocr-demo' ya existe, skipping.")

    await db.commit()
    print("Seeding complete.")


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await seed(db)


if __name__ == "__main__":
    asyncio.run(main())
