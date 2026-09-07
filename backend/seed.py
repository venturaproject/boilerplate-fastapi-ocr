"""
Database seeder — run after migrations.
Creates permissions, roles, admin user, and sample domain data idempotently.
"""

import asyncio
import os
import sys
from datetime import date

# Allow running as `uv run python seed.py` from /app/backend
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.dispositivo import DeviceBrand, DeviceModel, Dispositivo
from app.models.permission import Permission
from app.models.role import Role
from app.models.telefono import EstadoTelefono, Telefono, Tipologia
from app.models.trabajador import Trabajador
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
    # trabajadores
    "trabajadores.view", "trabajadores.create", "trabajadores.edit", "trabajadores.delete",
    # telefonos
    "telefonos.view", "telefonos.create", "telefonos.edit", "telefonos.delete",
    # dispositivos
    "dispositivos.view", "dispositivos.create", "dispositivos.edit", "dispositivos.delete",
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
        "trabajadores.view", "trabajadores.create", "trabajadores.edit",
        "telefonos.view", "telefonos.create", "telefonos.edit",
        "dispositivos.view", "dispositivos.create", "dispositivos.edit",
        "dashboard.view",
        "ocr.use", "ocr.jobs.view",
        "documents.view",
    ],
    "viewer": [
        "users.view",
        "roles.view",
        "permissions.view",
        "trabajadores.view",
        "telefonos.view",
        "dispositivos.view",
        "dashboard.view",
        "documents.view",
    ],
}

TRABAJADORES_DATA = [
    {"nombre": "Carlos",   "apellido": "García",    "dni": "12345678A", "email": "carlos.garcia@empresa.com",   "cargo": "Técnico de campo",      "departamento": "Operaciones",  "ciudad": "Madrid",    "estado": "activo",   "fecha_incorporacion": date(2020, 3, 15)},
    {"nombre": "Laura",    "apellido": "Martínez",  "dni": "23456789B", "email": "laura.martinez@empresa.com",  "cargo": "Responsable de zona",   "departamento": "Operaciones",  "ciudad": "Barcelona", "estado": "activo",   "fecha_incorporacion": date(2019, 6, 1)},
    {"nombre": "Miguel",   "apellido": "López",     "dni": "34567890C", "email": "miguel.lopez@empresa.com",    "cargo": "Instalador",            "departamento": "Técnico",      "ciudad": "Valencia",  "estado": "activo",   "fecha_incorporacion": date(2021, 1, 10)},
    {"nombre": "Ana",      "apellido": "Sánchez",   "dni": "45678901D", "email": "ana.sanchez@empresa.com",     "cargo": "Coordinadora",          "departamento": "Administración","ciudad": "Sevilla",   "estado": "activo",   "fecha_incorporacion": date(2018, 9, 20)},
    {"nombre": "Pedro",    "apellido": "Fernández", "dni": "56789012E", "email": "pedro.fernandez@empresa.com", "cargo": "Técnico de soporte",    "departamento": "Soporte",      "ciudad": "Bilbao",    "estado": "activo",   "fecha_incorporacion": date(2022, 4, 5)},
    {"nombre": "Elena",    "apellido": "Ruiz",      "dni": "67890123F", "email": "elena.ruiz@empresa.com",      "cargo": "Gestora de proyectos",  "departamento": "Proyectos",    "ciudad": "Madrid",    "estado": "activo",   "fecha_incorporacion": date(2020, 11, 3)},
    {"nombre": "Roberto",  "apellido": "Torres",    "dni": "78901234G", "email": "roberto.torres@empresa.com",  "cargo": "Técnico de campo",      "departamento": "Operaciones",  "ciudad": "Zaragoza",  "estado": "inactivo", "fecha_incorporacion": date(2017, 2, 14)},
    {"nombre": "Sofía",    "apellido": "Moreno",    "dni": "89012345H", "email": "sofia.moreno@empresa.com",    "cargo": "Analista",              "departamento": "IT",           "ciudad": "Madrid",    "estado": "activo",   "fecha_incorporacion": date(2023, 7, 18)},
]

ESTADOS_TELEFONO = [
    {"nombre": "Activo",       "color": "#22c55e"},
    {"nombre": "Libre",        "color": "#3b82f6"},
    {"nombre": "Avería",       "color": "#ef4444"},
    {"nombre": "En reparación","color": "#f59e0b"},
    {"nombre": "Baja",         "color": "#6b7280"},
]

TIPOLOGIAS = ["Móvil", "Fijo", "SIM", "Tableta"]

DEVICE_BRANDS = {
    "Apple":   ["iPhone 13", "iPhone 14", "iPhone 15", "iPad Air"],
    "Samsung": ["Galaxy S23", "Galaxy A54", "Galaxy Tab S9"],
    "Xiaomi":  ["Redmi Note 12", "Poco X5", "Mi 13"],
    "Huawei":  ["P40", "Mate 50"],
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

    # ── Trabajadores ──────────────────────────────────────────────────────────
    print("Seeding trabajadores...")
    existing = (await db.execute(select(Trabajador.dni))).scalars().all()
    existing_dnis = set(existing)
    new_trab = 0
    trabajadores_map: dict[str, Trabajador] = {}

    for t in TRABAJADORES_DATA:
        if t["dni"] not in existing_dnis:
            trab = Trabajador(
                nombre=t["nombre"],
                apellido=t["apellido"],
                dni=t["dni"],
                email=t["email"],
                cargo=t["cargo"],
                departamento=t["departamento"],
                ciudad=t["ciudad"],
                estado=t["estado"],
                fecha_incorporacion=t["fecha_incorporacion"],
            )
            db.add(trab)
            await db.flush()
            new_trab += 1
        else:
            result = await db.execute(select(Trabajador).where(Trabajador.dni == t["dni"]))
            trab = result.scalar_one()
        trabajadores_map[t["dni"]] = trab

    print(f"  {new_trab} trabajadores created ({len(TRABAJADORES_DATA) - new_trab} already existed).")

    # ── Estados de teléfono ───────────────────────────────────────────────────
    print("Seeding estados de teléfono...")
    estados_map: dict[str, EstadoTelefono] = {}
    for e in ESTADOS_TELEFONO:
        result = await db.execute(select(EstadoTelefono).where(EstadoTelefono.nombre == e["nombre"]))
        estado = result.scalar_one_or_none()
        if not estado:
            estado = EstadoTelefono(nombre=e["nombre"], color=e["color"])
            db.add(estado)
            await db.flush()
        estados_map[e["nombre"]] = estado
    print(f"  {len(ESTADOS_TELEFONO)} estados ready.")

    # ── Tipologías ────────────────────────────────────────────────────────────
    print("Seeding tipologías...")
    tipologias_map: dict[str, Tipologia] = {}
    for nombre in TIPOLOGIAS:
        result = await db.execute(select(Tipologia).where(Tipologia.nombre == nombre))
        tip = result.scalar_one_or_none()
        if not tip:
            tip = Tipologia(nombre=nombre)
            db.add(tip)
            await db.flush()
        tipologias_map[nombre] = tip
    print(f"  {len(TIPOLOGIAS)} tipologías ready.")

    # ── Teléfonos ─────────────────────────────────────────────────────────────
    print("Seeding teléfonos...")
    tel_count = (await db.execute(select(Telefono))).scalars().first()
    if not tel_count:
        telefonos_data = [
            {"numero": "600111001", "tipo": "corporativo", "operadora": "Movistar", "plan": "Plan Business 5G",  "marca": "Apple",   "modelo": "iPhone 14",       "imei": "351234560000001", "estado": "Activo", "tipologia": "Móvil",   "trabajador_dni": "12345678A"},
            {"numero": "600111002", "tipo": "corporativo", "operadora": "Vodafone", "plan": "Plan Business Pro", "marca": "Samsung", "modelo": "Galaxy S23",      "imei": "351234560000002", "estado": "Activo", "tipologia": "Móvil",   "trabajador_dni": "23456789B"},
            {"numero": "600111003", "tipo": "corporativo", "operadora": "Orange",   "plan": "Plan Empresa M",    "marca": "Xiaomi",  "modelo": "Redmi Note 12",   "imei": "351234560000003", "estado": "Activo", "tipologia": "Móvil",   "trabajador_dni": "34567890C"},
            {"numero": "600111004", "tipo": "corporativo", "operadora": "Movistar", "plan": "Plan Business 5G",  "marca": "Samsung", "modelo": "Galaxy A54",      "imei": "351234560000004", "estado": "Activo", "tipologia": "Móvil",   "trabajador_dni": "45678901D"},
            {"numero": "600111005", "tipo": "corporativo", "operadora": "Vodafone", "plan": "Plan Business Pro", "marca": "Apple",   "modelo": "iPhone 13",       "imei": "351234560000005", "estado": "Activo", "tipologia": "Móvil",   "trabajador_dni": "56789012E"},
            {"numero": "600111006", "tipo": "corporativo", "operadora": "Orange",   "plan": "Plan Empresa M",    "marca": "Apple",   "modelo": "iPhone 15",       "imei": "351234560000006", "estado": "Activo", "tipologia": "Móvil",   "trabajador_dni": "67890123F"},
            {"numero": "600111007", "tipo": "corporativo", "operadora": "Movistar", "plan": "Plan Business 5G",  "marca": "Huawei",  "modelo": "P40",             "imei": "351234560000007", "estado": "Avería", "tipologia": "Móvil",   "trabajador_dni": None},
            {"numero": "600111008", "tipo": "corporativo", "operadora": "Vodafone", "plan": "Plan Business Pro", "marca": "Xiaomi",  "modelo": "Poco X5",         "imei": "351234560000008", "estado": "Libre",  "tipologia": "Móvil",   "trabajador_dni": None},
            {"numero": "912001001", "tipo": "fijo",        "operadora": "Movistar", "plan": "Plan Oficina",      "marca": None,      "modelo": None,              "imei": None,             "estado": "Activo", "tipologia": "Fijo",    "trabajador_dni": "67890123F"},
            {"numero": None,        "tipo": "datos",       "operadora": "Orange",   "plan": "Plan Datos 10GB",   "marca": None,      "modelo": None,              "imei": None,             "estado": "Libre",  "tipologia": "SIM",     "trabajador_dni": None},
        ]
        for td in telefonos_data:
            t = Telefono(
                numero=td["numero"],
                tipo=td["tipo"],
                operadora=td["operadora"],
                plan=td["plan"],
                marca=td["marca"],
                modelo=td["modelo"],
                imei=td["imei"],
                estado_id=estados_map[td["estado"]].id,
                tipologia_id=tipologias_map[td["tipologia"]].id,
                trabajador_id=trabajadores_map[td["trabajador_dni"]].id if td["trabajador_dni"] else None,
                activo=True,
            )
            db.add(t)
        await db.flush()
        print(f"  {len(telefonos_data)} teléfonos created.")
    else:
        print("  Teléfonos already exist, skipping.")

    # ── Device brands & models ────────────────────────────────────────────────
    print("Seeding device brands & models...")
    brands_map: dict[str, DeviceBrand] = {}
    models_map: dict[str, DeviceModel] = {}
    for brand_name, model_names in DEVICE_BRANDS.items():
        result = await db.execute(select(DeviceBrand).where(DeviceBrand.nombre == brand_name))
        brand = result.scalar_one_or_none()
        if not brand:
            brand = DeviceBrand(nombre=brand_name)
            db.add(brand)
            await db.flush()
        brands_map[brand_name] = brand

        for model_name in model_names:
            result = await db.execute(
                select(DeviceModel).where(DeviceModel.nombre == model_name, DeviceModel.marca_id == brand.id)
            )
            model = result.scalar_one_or_none()
            if not model:
                model = DeviceModel(nombre=model_name, marca_id=brand.id)
                db.add(model)
                await db.flush()
            models_map[f"{brand_name}/{model_name}"] = model
    print(f"  {len(brands_map)} marcas, {len(models_map)} modelos ready.")

    # ── Dispositivos ──────────────────────────────────────────────────────────
    print("Seeding dispositivos...")
    disp_count = (await db.execute(select(Dispositivo))).scalars().first()
    if not disp_count:
        dispositivos_data = [
            {"numero": "D-001", "imei": "990001234500001", "serie": "SN001A", "marca": "Apple",   "modelo": "iPhone 14",     "grupo": "Móviles",   "estado": "asignado",   "trabajador_dni": "12345678A"},
            {"numero": "D-002", "imei": "990001234500002", "serie": "SN002A", "marca": "Samsung", "modelo": "Galaxy S23",    "grupo": "Móviles",   "estado": "asignado",   "trabajador_dni": "23456789B"},
            {"numero": "D-003", "imei": "990001234500003", "serie": "SN003A", "marca": "Xiaomi",  "modelo": "Redmi Note 12", "grupo": "Móviles",   "estado": "asignado",   "trabajador_dni": "34567890C"},
            {"numero": "D-004", "imei": "990001234500004", "serie": "SN004A", "marca": "Apple",   "modelo": "iPad Air",      "grupo": "Tabletas",  "estado": "asignado",   "trabajador_dni": "45678901D"},
            {"numero": "D-005", "imei": "990001234500005", "serie": "SN005A", "marca": "Samsung", "modelo": "Galaxy Tab S9", "grupo": "Tabletas",  "estado": "asignado",   "trabajador_dni": "56789012E"},
            {"numero": "D-006", "imei": "990001234500006", "serie": "SN006A", "marca": "Apple",   "modelo": "iPhone 15",     "grupo": "Móviles",   "estado": "asignado",   "trabajador_dni": "67890123F"},
            {"numero": "D-007", "imei": "990001234500007", "serie": "SN007A", "marca": "Huawei",  "modelo": "Mate 50",       "grupo": "Móviles",   "estado": "disponible", "trabajador_dni": None},
            {"numero": "D-008", "imei": "990001234500008", "serie": "SN008A", "marca": "Xiaomi",  "modelo": "Mi 13",         "grupo": "Móviles",   "estado": "disponible", "trabajador_dni": None},
            {"numero": "D-009", "imei": "990001234500009", "serie": "SN009A", "marca": "Samsung", "modelo": "Galaxy A54",    "grupo": "Móviles",   "estado": "baja",       "trabajador_dni": None},
            {"numero": "D-010", "imei": "990001234500010", "serie": "SN010A", "marca": "Apple",   "modelo": "iPhone 13",     "grupo": "Móviles",   "estado": "disponible", "trabajador_dni": None},
        ]
        for dd in dispositivos_data:
            brand = brands_map.get(dd["marca"])
            model = models_map.get(f"{dd['marca']}/{dd['modelo']}")
            d = Dispositivo(
                numero=dd["numero"],
                imei=dd["imei"],
                serie=dd["serie"],
                marca_id=brand.id if brand else None,
                modelo_id=model.id if model else None,
                grupo=dd["grupo"],
                estado=dd["estado"],
                trabajador_id=trabajadores_map[dd["trabajador_dni"]].id if dd["trabajador_dni"] else None,
            )
            db.add(d)
        await db.flush()
        print(f"  {len(dispositivos_data)} dispositivos created.")
    else:
        print("  Dispositivos already exist, skipping.")

    # ── API client de ejemplo para OCR ───────────────────────────────────────
    print("Seeding OCR API client...")
    from app.models.api_client import ApiClient

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
